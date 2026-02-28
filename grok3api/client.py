import contextvars
import functools
import os
from asyncio import events
from typing import Optional, List, Union, Dict, Any, Tuple
import base64
import json
from io import BytesIO

from grok3api.history import History, SenderType, get_image_type
from grok3api import driver
from grok3api.logger import logger
from grok3api.types.GrokResponse import GrokResponse


class GrokClient:
    """
    Client for working with Grok.

    :param use_xvfb: Flag to use Xvfb. Defaults to True. Applicable only on Linux.
    :param proxy: (str) Proxy server URL, used only in cases of regional blocking.
    :param history_msg_count: Number of messages to keep in history (default is `0` — history saving is disabled).
    :param history_path: Path to the history file in JSON format. Default is "chat_histories.json".
    :param history_as_json: Whether to send history to Grok in JSON format (for history_msg_count > 0). Defaults to True.
    :param history_auto_save: Automatically overwrite history file after each message. Defaults to True.
    :param always_new_conversation: (bool) Whether to use the new chat creation URL when sending a request to Grok.
    :param conversation_id: (str) Grok chat ID.
    :param response_id: (str) Grok response ID. Must be used together with conversation_id.
    :param timeout: Maximum time for client initialization. Default is 120 seconds.
    """

    NEW_CHAT_URL = "https://grok.com/rest/app-chat/conversations/new"
    CONVERSATION_URL = "https://grok.com/rest/app-chat/conversations/"
    max_tries: int = 5

    def __init__(self,
                 cookies: Union[Union[str, List[str]], Union[dict, List[dict]]] = None,
                 use_xvfb: bool = True,
                 proxy: Optional[str] = None,
                 history_msg_count: int = 0,
                 history_path: str = "chat_histories.json",
                 history_as_json: bool = True,
                 history_auto_save: bool = True,
                 always_new_conversation: bool = True,
                 conversation_id: Optional[str] = None,
                 response_id: Optional[str] = None,
                 enable_artifact_files: bool = False,
                 main_system_prompt: Optional[str] = None,
                 timeout: int = driver.web_driver.TIMEOUT):
        try:
            if (conversation_id is None) != (response_id is None):
                raise ValueError(
                    "If you want to use server history, you must provide both conversation_id and response_id.")

            self.cookies = cookies
            self.proxy = proxy
            self.use_xvfb: bool = use_xvfb
            self.history = History(history_msg_count=history_msg_count,
                                   history_path=history_path,
                                   history_as_json=history_as_json,
                                   main_system_prompt=main_system_prompt)
            self.history_auto_save: bool = history_auto_save
            self.proxy_index = 0
            self.enable_artifact_files = enable_artifact_files
            self.timeout: int = timeout

            self.always_new_conversation: bool = always_new_conversation
            self.conversationId: Optional[str] = conversation_id
            self.parentResponseId: Optional[str] = response_id
            self._statsig_id: Optional[str] = None

            driver.web_driver.init_driver(use_xvfb=self.use_xvfb, timeout=timeout, proxy=self.proxy)
            self._statsig_id = driver.web_driver.get_statsig()

        except Exception as e:
            logger.error(f"In GrokClient.__init__: {e}")
            raise e

    # ─────────────────────────────────────────────
    # FIX #4: Headers centralizados — un solo lugar, consistente con driver.py
    # ─────────────────────────────────────────────

    def _build_headers(self) -> dict:
        """Build request headers using the centralized BASE_HEADERS from driver."""
        from grok3api.driver import WebDriverSingleton
        headers = WebDriverSingleton.BASE_HEADERS.copy()
        # Ensure a consistent modern User-Agent
        headers["User-Agent"] = WebDriverSingleton.USER_AGENTS[0]
        if self._statsig_id:
            headers["x-statsig-id"] = self._statsig_id
        return headers

    # ─────────────────────────────────────────────
    # FIX #3: Lógica de reintentos extraída a método dedicado
    # ─────────────────────────────────────────────

    def _execute_with_retry(self, payload: dict, headers: dict,
                            history_id: Optional[str], message: str,
                            images, timeout: int) -> dict:
        """
        Maneja toda la lógica de reintentos de forma clara y lineal.
        Retorna el dict de respuesta crudo o un dict de error.
        """
        last_error_data = {}
        statsig_try_index = 0
        statsig_try_max = 2
        try_index = 0
        use_cookies: bool = self.cookies is not None
        is_list_cookies = isinstance(self.cookies, list)

        def _upload_images_to_payload():
            if not images:
                return
            attachments = []
            imgs = images if isinstance(images, list) else [images]
            for img in imgs:
                attachments.append(self._upload_image(img))
            payload["fileAttachments"] = attachments

        while try_index < self.max_tries:
            logger.debug(f"Attempt {try_index + 1}/{self.max_tries}"
                         + (" (no cookies)" if not use_cookies else ""))

            # — Ciclo de rotación de cookies —
            cookies_used = 0
            max_cookie_tries = len(self.cookies) if is_list_cookies else 1

            while True:
                # Aplicar cookies si corresponde
                if use_cookies:
                    current_cookies = self.cookies[0] if is_list_cookies else self.cookies
                    driver.web_driver.set_cookies(current_cookies)
                    _upload_images_to_payload()

                response = self._send_request(payload, headers, timeout)
                logger.debug(f"Raw response: {response}")

                # Respuesta vacía → reiniciar driver
                if response == {} and try_index != 0:
                    driver.web_driver.close_driver()
                    driver.web_driver.init_driver()
                    self._clean_conversation(payload, history_id, message)
                    break

                if not isinstance(response, dict) or not response:
                    break

                last_error_data = response
                str_response = str(response)

                # — Manejo de errores específicos —

                if 'Too many requests' in str_response or 'credentials' in str_response:
                    cookies_used += 1
                    self._clean_conversation(payload, history_id, message)

                    if is_list_cookies and cookies_used < len(self.cookies):
                        self.cookies.append(self.cookies.pop(0))
                        continue

                    # Sin más cookies → sesión anónima
                    driver.web_driver.restart_session()
                    use_cookies = False
                    _upload_images_to_payload()
                    continue

                if 'This service is not available in your region' in str_response:
                    return last_error_data

                if ('a padding to disable MSIE' in str_response
                        or 'Request rejected by anti-bot rules.' in str_response):
                    if not self.always_new_conversation:
                        last_error_data["error"] = (
                            "Cannot bypass x-statsig-id protection. "
                            "Try always_new_conversation=True"
                        )
                        return last_error_data

                    if statsig_try_index < statsig_try_max:
                        statsig_try_index += 1
                        self._statsig_id = driver.web_driver.get_statsig(restart_session=True)
                        headers["x-statsig-id"] = self._statsig_id or ""
                        continue

                    last_error_data["error"] = "Cannot bypass x-statsig-id protection"
                    return last_error_data

                if 'Just a moment' in str_response or '403' in str_response:
                    driver.web_driver.restart_session()
                    self._clean_conversation(payload, history_id, message)
                    break

                # — Respuesta válida —
                return response

            # Fin del ciclo de cookies
            if is_list_cookies and cookies_used >= len(self.cookies):
                break

            try_index += 1

            if try_index == self.max_tries - 1:
                self._clean_conversation(payload, history_id, message)
                driver.web_driver.close_driver()
                driver.web_driver.init_driver()

            self._clean_conversation(payload, history_id, message)
            driver.web_driver.restart_session()

        logger.debug(f"All retries exhausted. Last error: {last_error_data}")
        return last_error_data

    # ─────────────────────────────────────────────
    # Request sender
    # ─────────────────────────────────────────────

    def _send_request(self, payload: dict, headers: dict, timeout: int = driver.web_driver.TIMEOUT) -> dict:
        """Send request via browser fetch with timeout."""
        try:
            if not self._statsig_id:
                self._statsig_id = driver.web_driver.get_statsig()

            # FIX #4: statsig_id siempre actualizado desde _build_headers
            headers["x-statsig-id"] = self._statsig_id or ""

            target_url = (
                self.CONVERSATION_URL + self.conversationId + "/responses"
                if self.conversationId
                else self.NEW_CHAT_URL
            )

            fetch_script = f"""
            const controller = new AbortController();
            const signal = controller.signal;
            setTimeout(() => controller.abort(), {timeout * 1000});

            const payload = {json.dumps(payload)};
            return fetch('{target_url}', {{
                method: 'POST',
                headers: {json.dumps(headers)},
                body: JSON.stringify(payload),
                credentials: 'include',
                signal: signal
            }})
            .then(response => {{
                if (!response.ok) {{
                    return response.text().then(text => 'Error: HTTP ' + response.status + ' - ' + text);
                }}
                return response.text();
            }})
            .catch(error => {{
                if (error.name === 'AbortError') return 'TimeoutError';
                return 'Error: ' + error;
            }});
            """

            response = driver.web_driver.execute_script(fetch_script)

            if isinstance(response, str) and response.startswith('Error:'):
                return self.handle_str_error(response)

            if response and 'This service is not available in your region' in response:
                return {'error': 'This service is not available in your region'}

            # — Parse NDJSON response —
            final_dict = {}
            conversation_info = {}
            new_title = None

            for line in response.splitlines():
                try:
                    parsed = json.loads(line)

                    if "modelResponse" in parsed.get("result", {}):
                        parsed["result"]["response"] = {
                            "modelResponse": parsed["result"].pop("modelResponse")
                        }

                    if "conversation" in parsed.get("result", {}):
                        conversation_info = parsed["result"]["conversation"]

                    if "title" in parsed.get("result", {}):
                        new_title = parsed["result"]["title"].get("newTitle")

                    if "modelResponse" in parsed.get("result", {}).get("response", {}):
                        final_dict = parsed

                except (json.JSONDecodeError, KeyError):
                    continue

            if final_dict:
                model_response = final_dict["result"]["response"]["modelResponse"]
                final_dict["result"]["response"] = {"modelResponse": model_response}
                final_dict["result"]["response"].update({
                    "conversationId": conversation_info.get("conversationId"),
                    "title":          conversation_info.get("title"),
                    "createTime":     conversation_info.get("createTime"),
                    "modifyTime":     conversation_info.get("modifyTime"),
                    "temporary":      conversation_info.get("temporary"),
                    "newTitle":       new_title,
                })

                if not self.always_new_conversation and model_response.get("responseId"):
                    self.conversationId = self.conversationId or conversation_info.get("conversationId")
                    self.parentResponseId = (
                        model_response.get("responseId") if self.conversationId else None
                    )

            logger.debug(f"Parsed response: {final_dict}")
            return final_dict

        except Exception as e:
            logger.error(f"In _send_request: {e}")
            return {}

    # ─────────────────────────────────────────────
    # Image handling — FIX #6: extraído de ask()
    # ─────────────────────────────────────────────

    def _is_base64_image(self, s: str) -> bool:
        try:
            decoded = base64.b64decode(s, validate=True)
            return get_image_type(decoded) is not None
        except Exception:
            return False

    def _upload_image(self, file_input: Union[str, BytesIO],
                      file_extension: str = "jpg",
                      file_mime_type: str = None) -> str:
        if isinstance(file_input, str):
            if os.path.exists(file_input):
                with open(file_input, "rb") as f:
                    file_content = f.read()
            elif self._is_base64_image(file_input):
                file_content = base64.b64decode(file_input)
            else:
                raise ValueError("String is neither a valid file path nor a valid base64 image")
        elif isinstance(file_input, BytesIO):
            file_content = file_input.getvalue()
        else:
            raise ValueError("file_input must be a file path, base64 string, or BytesIO object")

        # FIX: Usar get_image_type para detección automática
        detected_ext = get_image_type(file_content)
        if detected_ext:
            file_extension = detected_ext
            file_mime_type = f"image/{detected_ext}"
        else:
            file_extension = file_extension or "jpg"
            file_mime_type = file_mime_type or "image/jpeg"

        file_content_b64 = base64.b64encode(file_content).decode("utf-8")
        file_name_base = file_content_b64[:10].replace("/", "_").replace("+", "_")
        file_name = f"{file_name_base}.{file_extension}"

        fetch_script = f"""
        return fetch('https://grok.com/rest/app-chat/upload-file', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'User-Agent': '{driver.WebDriverSingleton.USER_AGENTS[0]}',
                'Origin': 'https://grok.com',
                'Referer': 'https://grok.com/'
            }},
            body: JSON.stringify({{
                fileName: {json.dumps(file_name)},
                fileMimeType: {json.dumps(file_mime_type)},
                content: {json.dumps(file_content_b64)}
            }}),
            credentials: 'include'
        }})
        .then(response => {{
            if (!response.ok) {{
                return response.text().then(text => 'Error: HTTP ' + response.status + ' - ' + text);
            }}
            return response.json();
        }})
        .catch(error => 'Error: ' + error);
        """

        response = driver.web_driver.execute_script(fetch_script)

        captcha = isinstance(response, str) and "Just a moment" in response
        if (isinstance(response, str) and response.startswith('Error:')) or captcha:
            if 'Too many requests' in response or 'Bad credentials' in response or captcha:
                driver.web_driver.restart_session()
                response = driver.web_driver.execute_script(fetch_script)
                if isinstance(response, str) and response.startswith('Error:'):
                    raise ValueError(response)
            else:
                raise ValueError(response)

        if not isinstance(response, dict) or "fileMetadataId" not in response:
            raise ValueError("Server response does not contain fileMetadataId")

        return response["fileMetadataId"]

    # FIX #6: preparación de imágenes extraída de ask()
    def _prepare_file_attachments(self, images, existing_attachments: Optional[List]) -> List:
        """Upload images and return list of fileMetadataIds."""
        if images is None:
            return existing_attachments or []
        attachments = []
        imgs = images if isinstance(images, list) else [images]
        for img in imgs:
            attachments.append(self._upload_image(img))
        return attachments

    # ─────────────────────────────────────────────
    # Conversation helpers
    # ─────────────────────────────────────────────

    def _clean_conversation(self, payload: dict, history_id: str, message: str):
        payload.pop("parentResponseId", None)
        payload["message"] = self._messages_with_possible_history(history_id, message)
        self.conversationId = None
        self.parentResponseId = None

    def _messages_with_possible_history(self, history_id: str, message: str) -> str:
        if (self.history.history_msg_count < 1
                and self.history.main_system_prompt is None
                and history_id not in self.history._system_prompts):
            return message
        if self.parentResponseId and self.conversationId:
            return message
        return self.history.get_history(history_id) + '\n' + message

    # ─────────────────────────────────────────────
    # FIX #6: Payload preparado en su propio método
    # ─────────────────────────────────────────────

    def _build_payload(self,
                       message: str,
                       history_id: Optional[str],
                       file_attachments: List,
                       image_attachments: Optional[List],
                       temporary: bool,
                       model_name: Optional[str],
                       custom_instructions: str,
                       deepsearch_preset: str,
                       disable_search: bool,
                       enable_image_generation: bool,
                       return_image_bytes: bool,
                       return_raw_grok: bool,
                       enable_image_streaming: bool,
                       image_generation_count: int,
                       force_concise: bool,
                       tool_overrides: Optional[Dict],
                       enable_side_by_side: bool,
                       send_final_metadata: bool,
                       is_preset: bool,
                       is_reasoning: bool,
                       disable_text_follow_ups: bool,
                       webpage_urls: Optional[List[str]],
                       disable_artifact: bool,
                       response_model_id: Optional[str]) -> dict:
        """Build the full request payload."""
        message_payload = self._messages_with_possible_history(history_id, message)
        payload = {
            "temporary": temporary,
            "message": message_payload,
            "fileAttachments": file_attachments,
            "imageAttachments": image_attachments or [],
            "disableSearch": disable_search,
            "enableImageGeneration": enable_image_generation,
            "returnImageBytes": return_image_bytes,
            "returnRawGrokInXaiRequest": return_raw_grok,
            "enableImageStreaming": enable_image_streaming,
            "imageGenerationCount": image_generation_count,
            "forceConcise": force_concise,
            "toolOverrides": tool_overrides or {},
            "enableSideBySide": enable_side_by_side,
            "sendFinalMetadata": send_final_metadata,
            "isPreset": is_preset,
            "isReasoning": is_reasoning,
            "disableTextFollowUps": disable_text_follow_ups,
            "customInstructions": custom_instructions,
            # FIX #2: typo corregido (espacio -> guión bajo)
            "deepsearch_preset": deepsearch_preset,
            "webpageUrls": webpage_urls or [],
            "disableArtifact": disable_artifact or not self.enable_artifact_files,
        }
        
        if model_name:
            payload["modelName"] = model_name
        
        if response_model_id:
            payload["responseMetadata"] = {
                "requestModelDetails": {
                    "modelId": response_model_id
                }
            }

        if self.parentResponseId:
            payload["parentResponseId"] = self.parentResponseId
        return payload

    # ─────────────────────────────────────────────
    # FIX #6: Procesamiento de respuesta extraído de ask()
    # ─────────────────────────────────────────────

    def _process_response(self, raw: dict, history_id: Optional[str], message: str) -> GrokResponse:
        """Convierte el dict crudo en GrokResponse y actualiza historial."""
        response = GrokResponse(raw, self.enable_artifact_files)
        assistant_message = response.modelResponse.message

        if self.history.history_msg_count > 0:
            # FIX #1: guardar mensaje del USUARIO (no del asistente)
            self.history.add_message(history_id, SenderType.USER, message)
            self.history.add_message(history_id, SenderType.ASSISTANT, assistant_message)
            if self.history_auto_save:
                self.history.to_file()

        return response

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    def send_message(self, message: str, history_id: Optional[str] = None,
                     **kwargs: Any) -> GrokResponse:
        """Deprecated — use ask() instead."""
        logger.warning("send_message is deprecated. Please use GrokClient.ask instead.")
        return self.ask(message=message, history_id=history_id, **kwargs)

    async def async_ask(self, message: str, history_id: Optional[str] = None,
                        new_conversation: Optional[bool] = None,
                        timeout: Optional[int] = None,
                        temporary: bool = False,
                        modelName: Optional[str] = None,
                        images: Union[Optional[List[Union[str, BytesIO]]], str, BytesIO] = None,
                        fileAttachments: Optional[List[str]] = None,
                        imageAttachments: Optional[List] = None,
                        customInstructions: str = "",
                        deepsearch_preset: str = "",
                        disableSearch: bool = False,
                        enableImageGeneration: bool = True,
                        enableImageStreaming: bool = True,
                        enableSideBySide: bool = True,
                        imageGenerationCount: int = 2,
                        isPreset: bool = False,
                        isReasoning: bool = False,
                        returnImageBytes: bool = False,
                        returnRawGrokInXaiRequest: bool = False,
                        sendFinalMetadata: bool = True,
                        toolOverrides: Optional[Dict[str, Any]] = None,
                        forceConcise: bool = True,
                        disableTextFollowUps: bool = True,
                        webpageUrls: Optional[List[str]] = None,
                        disableArtifact: bool = False,
                        responseModelId: Optional[str] = None) -> GrokResponse:
        """Asynchronous wrapper for ask()."""
        try:
            return await _to_thread(
                self.ask,
                message=message, history_id=history_id, new_conversation=new_conversation,
                timeout=timeout, temporary=temporary, modelName=modelName, images=images,
                fileAttachments=fileAttachments, imageAttachments=imageAttachments,
                customInstructions=customInstructions, deepsearch_preset=deepsearch_preset,
                disableSearch=disableSearch, enableImageGeneration=enableImageGeneration,
                enableImageStreaming=enableImageStreaming, enableSideBySide=enableSideBySide,
                imageGenerationCount=imageGenerationCount, isPreset=isPreset,
                isReasoning=isReasoning, returnImageBytes=returnImageBytes,
                returnRawGrokInXaiRequest=returnRawGrokInXaiRequest,
                sendFinalMetadata=sendFinalMetadata, toolOverrides=toolOverrides,
                forceConcise=forceConcise, disableTextFollowUps=disableTextFollowUps,
                webpageUrls=webpageUrls, disableArtifact=disableArtifact,
                responseModelId=responseModelId,
            )
        except Exception as e:
            logger.error(f"In async_ask: {e}")
            return GrokResponse({}, self.enable_artifact_files)

    def ask(self,
            message: str,
            history_id: Optional[str] = None,
            new_conversation: Optional[bool] = None,
            timeout: Optional[int] = None,
            temporary: bool = False,
            modelName: Optional[str] = None,
            images: Union[Optional[List[Union[str, BytesIO]]], str, BytesIO] = None,
            fileAttachments: Optional[List[str]] = None,
            imageAttachments: Optional[List] = None,
            customInstructions: str = "",
            deepsearch_preset: str = "",
            disableSearch: bool = False,
            enableImageGeneration: bool = True,
            enableImageStreaming: bool = True,
            enableSideBySide: bool = True,
            imageGenerationCount: int = 2,
            isPreset: bool = False,
            isReasoning: bool = False,
            returnImageBytes: bool = False,
            returnRawGrokInXaiRequest: bool = False,
            sendFinalMetadata: bool = True,
            toolOverrides: Optional[Dict[str, Any]] = None,
            forceConcise: bool = True,
            disableTextFollowUps: bool = True,
            webpageUrls: Optional[List[str]] = None,
            disableArtifact: bool = False,
            responseModelId: Optional[str] = None) -> GrokResponse:
        """
        Send a message to Grok and return the response.
        """
        if timeout is None:
            timeout = self.timeout

        if images is not None and fileAttachments is not None:
            raise ValueError("'images' and 'fileAttachments' cannot be used together.")

        last_error_data = {}
        try:
            # FIX #4: headers unificados desde método centralizado
            headers = self._build_headers()

            # FIX #6: preparación de imágenes en método dedicado
            file_attachments = self._prepare_file_attachments(images, fileAttachments)

            # FIX #6: construcción de payload en método dedicado
            payload = self._build_payload(
                message=message,
                history_id=history_id,
                file_attachments=file_attachments,
                image_attachments=imageAttachments,
                temporary=temporary,
                model_name=modelName,
                custom_instructions=customInstructions,
                deepsearch_preset=deepsearch_preset,
                disable_search=disableSearch,
                enable_image_generation=enableImageGeneration,
                return_image_bytes=returnImageBytes,
                return_raw_grok=returnRawGrokInXaiRequest,
                enable_image_streaming=enableImageStreaming,
                image_generation_count=imageGenerationCount,
                force_concise=forceConcise,
                tool_overrides=toolOverrides,
                enable_side_by_side=enableSideBySide,
                send_final_metadata=sendFinalMetadata,
                is_preset=isPreset,
                is_reasoning=isReasoning,
                disable_text_follow_ups=disableTextFollowUps,
                webpage_urls=webpageUrls,
                disable_artifact=disableArtifact,
                response_model_id=responseModelId,
            )

            if new_conversation:
                self._clean_conversation(payload, history_id, message)

            # FIX #3: reintentos en método dedicado
            raw = self._execute_with_retry(
                payload=payload,
                headers=headers,
                history_id=history_id,
                message=message,
                images=images,
                timeout=timeout,
            )

            if raw:
                last_error_data = raw
                # FIX #1 + FIX #6: procesamiento y guardado de historial correcto
                return self._process_response(raw, history_id, message)

        except Exception as e:
            logger.error(f"In ask: {e}")
            if not last_error_data:
                last_error_data = self.handle_str_error(str(e))

        return GrokResponse(last_error_data, self.enable_artifact_files)

    # ─────────────────────────────────────────────
    # Error handling
    # ─────────────────────────────────────────────

    def handle_str_error(self, response_str: str) -> dict:
        try:
            json_str = response_str.split(" - ", 1)[1]
            response = json.loads(json_str)

            if isinstance(response, dict):
                if 'error' in response:
                    error = response['error']
                    return {
                        "error_code": error.get('code', 'Unknown'),
                        "error": error.get('message') or response_str,
                        "details": error.get('details') if isinstance(error.get('details'), list) else [],
                    }
                if 'message' in response:
                    return {
                        "error_code": response.get('code', 'Unknown'),
                        "error": response.get('message') or response_str,
                        "details": response.get('details') if isinstance(response.get('details'), list) else [],
                    }
        except Exception:
            pass

        return {"error_code": "Unknown", "error": response_str, "details": []}


# ─────────────────────────────────────────────
# Async helper
# ─────────────────────────────────────────────

async def _to_thread(func, /, *args, **kwargs):
    loop = events.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)