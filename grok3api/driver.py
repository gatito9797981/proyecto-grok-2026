import logging
import random
import re
import string
import time
from typing import Optional
import os
import shutil
import subprocess
import atexit
import signal
import sys

from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import SessionNotCreatedException, TimeoutException

from grok3api.logger import logger
from grok3api.fingerprint import FingerprintGenerator


class WebDriverSingleton:
    """Singleton for managing ChromeDriver."""

    _instance = None
    _driver: Optional[ChromeWebDriver] = None
    _fingerprint: Optional[FingerprintGenerator] = None
    TIMEOUT = 360

    USE_XVFB = True
    xvfb_display: Optional[int] = None

    BASE_URL = "https://grok.com/"
    CHROME_VERSION = None
    WAS_FATAL = False

    # Proxy desde variable de entorno (DEF_PROXY ya configurado en .env)
    def_proxy = os.getenv("DEF_PROXY", "socks4://98.178.72.21:10919")

    # Anti-detection config desde .env
    ANTI_DETECTION_LEVEL = os.getenv("ANTI_DETECTION_LEVEL", "full")
    FINGERPRINT_SEED = os.getenv("FINGERPRINT_SEED")

    # Hardware spoofing config
    HARDWARE_CONCURRENCY = 8
    DEVICE_MEMORY = 8
    PLATFORM = "Win32"
    VENDOR = "Google Inc."
    MAX_TOUCH_POINTS = 0
    MAX_TEXTURE_SIZE = 16384

    execute_script = None
    add_cookie = None
    get_cookies = None
    get = None

    need_proxy: bool = False
    max_proxy_tries = 1
    proxy_try = 0
    proxy: Optional[str] = None

    # Headers base centralizados para evitar deteccion anti-bot
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    ]

    BASE_HEADERS = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://grok.com",
        "Referer": "https://grok.com/",
        "Sec-Ch-Ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=1, i",
    }

    def __new__(cls, *args, **kwargs):
        if kwargs.get("bypass_singleton"):
            return super(WebDriverSingleton, cls).__new__(cls)
        if cls._instance is None:
            cls._instance = super(WebDriverSingleton, cls).__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        self._hide_unnecessary_logs()
        self._patch_chrome_del()
        atexit.register(self.close_driver)
        signal.signal(signal.SIGINT, self._signal_handler)

    # ─────────────────────────────────────────────
    # Internal setup helpers
    # ─────────────────────────────────────────────

    def _hide_unnecessary_logs(self):
        """Suppress noisy third-party logs."""
        try:
            for name in (
                "undetected_chromedriver",
                "selenium",
                "urllib3.connectionpool",
                "selenium.webdriver",
                "selenium.webdriver.remote.remote_connection",
            ):
                lg = logging.getLogger(name)
                for h in lg.handlers[:]:
                    lg.removeHandler(h)
                lg.setLevel(logging.CRITICAL)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logging.debug(f"Error suppressing logs: {e}")

    def _patch_chrome_del(self):
        """Patch uc.Chrome.__del__ to avoid noisy errors on shutdown."""

        def safe_del(self):
            try:
                if hasattr(self, "service") and self.service.process:
                    self.service.process.kill()
            except Exception as e:
                logger.debug(f"Error killing chromedriver service: {e}")
            try:
                self.quit()
            except Exception as e:
                logger.debug(f"uc.Chrome.__del__ quit(): {e}")

        try:
            uc.Chrome.__del__ = safe_del
        except Exception:
            pass

    def _bind_driver_methods(self):
        """Bind frequently used driver methods to instance attributes."""
        self.execute_script = self._driver.execute_script
        self.add_cookie = self._driver.add_cookie
        self.get_cookies = self._driver.get_cookies
        self.get = self._driver.get

    def _is_driver_alive(self, driver) -> bool:
        """Check if the driver session is still alive."""
        try:
            driver.title
            return True
        except Exception:
            return False

    def _minimize(self):
        """Minimize the browser window."""
        try:
            self._driver.minimize_window()
        except Exception:
            pass

    def _human_delay(self, min_s: float = 0.5, max_s: float = 2.5):
        """Random pause simulating human behaviour."""
        base = random.uniform(min_s, max_s)
        if random.random() < 0.1:
            base += random.uniform(1.0, 3.0)
        time.sleep(base)

    def _wait_for_page_stable(self, timeout: float = 5.0):
        """Wait until the DOM stops changing, up to `timeout` seconds."""
        prev_source = ""
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.3)
            current = self._driver.page_source
            if current == prev_source:
                return
            prev_source = current

    # ─────────────────────────────────────────────
    # Anti-detection
    # ─────────────────────────────────────────────

    def _inject_fingerprint_spoofing(self):
        """
        Inject JS via CDP with comprehensive anti-detection.
        Uses FingerprintGenerator for configurable, consistent fingerprint spoofing.
        """
        if self._fingerprint is None:
            canvas_seed = None
            if self.FINGERPRINT_SEED:
                try:
                    canvas_seed = int(self.FINGERPRINT_SEED)
                except ValueError:
                    pass

            self._fingerprint = FingerprintGenerator(
                canvas_seed=canvas_seed,
                anti_detection_level=self.ANTI_DETECTION_LEVEL,
                hardware_concurrency=self.HARDWARE_CONCURRENCY,
                device_memory=self.DEVICE_MEMORY,
                platform=self.PLATFORM,
                vendor=self.VENDOR,
                max_touch_points=self.MAX_TOUCH_POINTS,
                max_texture_size=self.MAX_TEXTURE_SIZE,
            )

        script = self._fingerprint.generate_anti_detection_script()

        self._driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": script}
        )

        logger.debug(
            f"Fingerprint injected. Anti-detection level: {self.ANTI_DETECTION_LEVEL}, Seed: {self._fingerprint.get_seed()}"
        )

    # ─────────────────────────────────────────────
    # Human-like interactions
    # ─────────────────────────────────────────────

    def human_move_to(self, element):
        """Move the mouse toward an element in a human-like curved path."""
        action = ActionChains(self._driver)
        action.move_to_element(self._driver.find_element(By.TAG_NAME, "body"))
        action.pause(random.uniform(0.05, 0.15))
        for _ in range(random.randint(5, 10)):
            action.move_by_offset(random.randint(-10, 10), random.randint(-5, 5))
            action.pause(random.uniform(0.01, 0.05))
        action.move_to_element(element)
        action.pause(random.uniform(0.1, 0.3))
        action.perform()

    def human_type(self, element, text: str):
        """Type text character by character with randomised inter-key delays."""
        for char in text:
            element.send_keys(char)
            delay = random.gauss(0.08, 0.03)
            delay = max(0.02, min(delay, 0.3))
            time.sleep(delay)
            if random.random() < 0.05:
                time.sleep(random.uniform(0.3, 0.8))

    # ─────────────────────────────────────────────
    # Driver lifecycle
    # ─────────────────────────────────────────────

    def _setup_driver(self, driver, wait_loading: bool, timeout: int):
        """Minimise, inject fingerprint, load base URL and wait for input field."""
        self._minimize()
        self._inject_fingerprint_spoofing()  # must run before driver.get()

        driver.get(self.BASE_URL)
        patch_fetch_for_statsig(driver)

        page = driver.page_source
        if (
            page
            and isinstance(page, str)
            and "This service is not available in your region" in page
        ):
            if self.proxy_try > self.max_proxy_tries:
                raise ValueError("Cannot bypass region block")
            self.need_proxy = True
            self.close_driver()
            self.init_driver(wait_loading=wait_loading, proxy=self.def_proxy)
            self.proxy_try += 1
            return

        if wait_loading:
            logger.debug("Waiting for input field...")
            try:
                WebDriverWait(driver, timeout).until(
                    ec.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.relative.z-10 textarea")
                    )
                )
                self._wait_for_page_stable()
                self.proxy_try = 0
                logger.debug("Input field found.")
            except Exception:
                logger.debug("Input field not found.")

    def init_driver(
        self,
        wait_loading: bool = True,
        use_xvfb: bool = True,
        timeout: Optional[int] = None,
        proxy: Optional[str] = None,
    ):
        """Start ChromeDriver and navigate to the base URL (up to 3 attempts)."""
        driver_timeout = timeout if timeout is not None else self.TIMEOUT
        self.TIMEOUT = driver_timeout

        if proxy is None:
            if self.need_proxy:
                proxy = self.def_proxy
        else:
            self.proxy = proxy

        self.USE_XVFB = use_xvfb
        attempts = 0
        max_attempts = 3

        def _create_driver():
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument(
                f"--user-agent={random.choice(WebDriverSingleton.USER_AGENTS)}"
            )

            caps = DesiredCapabilities.CHROME
            caps["goog:loggingPrefs"] = {"browser": "ALL"}

            if proxy:
                logger.debug(f"Using proxy: {proxy}")
                chrome_options.add_argument(f"--proxy-server={proxy}")

            new_driver = uc.Chrome(
                options=chrome_options,
                headless=False,
                use_subprocess=True,
                version_main=self.CHROME_VERSION,
                desired_capabilities=caps,
            )
            new_driver.set_script_timeout(driver_timeout)
            return new_driver

        while attempts < max_attempts:
            try:
                if self.USE_XVFB:
                    self._safe_start_xvfb()

                if self._driver and self._is_driver_alive(self._driver):
                    self._minimize()
                    current_url = self._driver.current_url
                    if current_url != self.BASE_URL:
                        logger.debug(
                            f"Current URL {current_url} differs from base, navigating..."
                        )
                        self._driver.get(self.BASE_URL)
                        if wait_loading:
                            try:
                                WebDriverWait(self._driver, driver_timeout).until(
                                    ec.presence_of_element_located(
                                        (By.CSS_SELECTOR, "div.relative.z-10 textarea")
                                    )
                                )
                                self._wait_for_page_stable()
                                logger.debug("Input field found.")
                            except Exception:
                                logger.error("Input field not found.")
                    self.WAS_FATAL = False
                    logger.debug("Driver alive, all good.")
                    self._bind_driver_methods()
                    return

                logger.debug(f"Attempt {attempts + 1}: creating new driver...")
                self.close_driver()
                self._driver = _create_driver()
                self._setup_driver(self._driver, wait_loading, driver_timeout)
                self.WAS_FATAL = False
                logger.debug("Browser started.")
                self._bind_driver_methods()
                return

            except SessionNotCreatedException as e:
                self.close_driver()
                error_message = str(e)
                match = re.search(r"Current browser version is (\d+)", error_message)
                self.CHROME_VERSION = (
                    int(match.group(1)) if match else self._get_chrome_version()
                )
                logger.debug(
                    f"Browser/driver mismatch, retrying with Chrome {self.CHROME_VERSION}..."
                )
                self._driver = _create_driver()
                self._setup_driver(self._driver, wait_loading, driver_timeout)
                logger.debug(f"Driver version set to {self.CHROME_VERSION}.")
                self.WAS_FATAL = False
                self._bind_driver_methods()
                return

            except Exception as e:
                logger.error(f"Attempt {attempts + 1} failed: {e}")
                attempts += 1
                self.close_driver()
                if attempts == max_attempts:
                    logger.fatal(f"All {max_attempts} attempts failed: {e}")
                    self.WAS_FATAL = True
                    raise
                sleep_time = 2**attempts  # exponential backoff: 2s, 4s
                logger.debug(f"Waiting {sleep_time}s before next attempt...")
                time.sleep(sleep_time)

    def restart_session(self):
        """Clear all storage, re-inject fingerprint and reload the base URL."""
        try:
            self._driver.delete_all_cookies()
            self._driver.execute_script("localStorage.clear(); sessionStorage.clear();")
            self._inject_fingerprint_spoofing()  # re-inject after session reset
            self._driver.get(self.BASE_URL)
            patch_fetch_for_statsig(self._driver)
            WebDriverWait(self._driver, self.TIMEOUT).until(
                ec.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.relative.z-10 textarea")
                )
            )
            self._wait_for_page_stable()
            logger.debug("Session restarted, page loaded.")
        except Exception as e:
            logger.debug(f"Error in restart_session: {e}")

    def close_driver(self):
        """Quit the driver and clear the reference."""
        if self._driver:
            self._driver.quit()
            logger.debug("Browser closed.")
        self._driver = None

    def set_proxy(self, proxy: str):
        """Switch to a different proxy by restarting the driver."""
        self.close_driver()
        self.init_driver(use_xvfb=self.USE_XVFB, timeout=self.TIMEOUT, proxy=proxy)

    # ─────────────────────────────────────────────
    # Cookie management
    # ─────────────────────────────────────────────

    def set_cookies(self, cookies_input):
        """Set cookies from a string, dict or list of dicts."""
        if cookies_input is None:
            return
        if not self._driver.current_url.startswith("http"):
            raise Exception("A page must be loaded before setting cookies.")

        if isinstance(cookies_input, str):
            for cookie in cookies_input.strip().rstrip(";").split("; "):
                if "=" not in cookie:
                    continue
                name, value = cookie.split("=", 1)
                self._driver.add_cookie({"name": name, "value": value, "path": "/"})

        elif isinstance(cookies_input, dict):
            if "name" in cookies_input and "value" in cookies_input:
                c = cookies_input.copy()
                c.setdefault("path", "/")
                self._driver.add_cookie(c)
            else:
                for name, value in cookies_input.items():
                    self._driver.add_cookie({"name": name, "value": value, "path": "/"})

        elif isinstance(cookies_input, list):
            for cookie in cookies_input:
                if isinstance(cookie, dict) and "name" in cookie and "value" in cookie:
                    c = cookie.copy()
                    c.setdefault("path", "/")
                    self._driver.add_cookie(c)
                else:
                    raise ValueError(
                        "Each cookie dict must contain 'name' and 'value'."
                    )
        else:
            raise TypeError("cookies_input must be a str, dict or list of dicts.")

    # ─────────────────────────────────────────────
    # Statsig helpers
    # ─────────────────────────────────────────────

    def get_statsig(
        self, restart_session: bool = False, try_index: int = 0
    ) -> Optional[str]:
        if try_index > 3:
            return None
        try:
            statsig_id = self._update_statsig(restart_session)
            if statsig_id:
                return statsig_id
            # First attempt returned nothing — retry once with a fresh session
            return self._update_statsig(True)
        except Exception as e:
            logger.error(f"In get_statsig: {e}")
            return None

    def _initiate_answer(self):
        """Type a random character and submit to trigger a network response."""
        try:
            textarea = WebDriverWait(self._driver, self.TIMEOUT).until(
                ec.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@class, 'relative')]//textarea")
                )
            )
            self.human_move_to(textarea)
            textarea.click()
            self._human_delay(0.2, 0.5)
            self.human_type(textarea, random.choice(string.ascii_lowercase))
            textarea.send_keys(Keys.ENTER)
        except Exception as e:
            logger.error(f"In _initiate_answer: {e}")

    def _update_statsig(self, restart_session: bool = False) -> Optional[str]:
        if restart_session:
            self.restart_session()

        if self._driver.current_url != self.BASE_URL:
            logger.debug("Not on base URL, navigating back...")
            self._driver.get(self.BASE_URL)
            patch_fetch_for_statsig(self._driver)

        self._initiate_answer()

        try:
            is_overlay_active = self._driver.execute_script("""
                for (const el of document.querySelectorAll("p")) {
                    if (el.textContent.includes("Making sure you're human")) {
                        const s = window.getComputedStyle(el);
                        if (s.visibility !== 'hidden' && s.display !== 'none') return true;
                    }
                }
                return false;
            """)
            if is_overlay_active:
                logger.debug("Captcha overlay detected.")
                return None

            WebDriverWait(self._driver, min(self.TIMEOUT, 20)).until(
                ec.any_of(
                    ec.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.message-bubble p[dir='auto']")
                    ),
                    ec.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.w-full.max-w-\\48rem\\]")
                    ),
                    ec.presence_of_element_located(
                        (
                            By.XPATH,
                            '//p[contains(text(), "Making sure you\'re human...")]',
                        )
                    ),
                )
            )

            if self._driver.find_elements(
                By.CSS_SELECTOR, "div.w-full.max-w-\\48rem\\]"
            ):
                logger.debug("Authenticity error.")
                return None

            if self._driver.find_elements(
                By.XPATH, '//p[contains(text(), "Making sure you\'re human...")]'
            ):
                logger.debug("Captcha appeared.")
                return None

            statsig_id = self._driver.execute_script("return window.__xStatsigId;")
            logger.debug(f"Got x-statsig-id: {statsig_id}")
            return statsig_id

        except TimeoutException:
            logger.debug("Timeout waiting for response.")
            return None
        except Exception as e:
            logger.debug(f"In _update_statsig: {e}")
            return None

    def del_captcha(self, timeout: int = 5) -> bool:
        try:
            captcha_wrapper = WebDriverWait(self._driver, timeout).until(
                ec.presence_of_element_located((By.CSS_SELECTOR, "div.main-wrapper"))
            )
            self._driver.execute_script("arguments[0].remove();", captcha_wrapper)
            return True
        except TimeoutException:
            return True
        except Exception as e:
            logger.debug(f"In del_captcha: {e}")
            return False

    # ─────────────────────────────────────────────
    # System helpers
    # ─────────────────────────────────────────────

    def _safe_start_xvfb(self):
        """Start Xvfb on a unique DISPLAY number (Linux only)."""
        if not sys.platform.startswith("linux"):
            return

        if shutil.which("Xvfb") is None:
            raise RuntimeError("Xvfb not found. Install with: sudo apt install xvfb")

        if self.xvfb_display is None:
            display_number = 99
            while True:
                result = subprocess.run(
                    ["pgrep", "-f", f"Xvfb :{display_number}"],
                    capture_output=True,
                    text=True,
                )
                if not result.stdout.strip():
                    break
                display_number += 1
            self.xvfb_display = display_number

        display_var = f":{self.xvfb_display}"
        os.environ["DISPLAY"] = display_var

        result = subprocess.run(
            ["pgrep", "-f", f"Xvfb {display_var}"], capture_output=True, text=True
        )
        if result.stdout.strip():
            logger.debug(f"Xvfb already running on {display_var}.")
            return

        # 1920x1080 avoids detection of the old 1024x768 Xvfb default
        logger.debug(f"Starting Xvfb on {display_var}...")
        subprocess.Popen(
            ["Xvfb", display_var, "-screen", "0", "1920x1080x24"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(10):
            time.sleep(1)
            result = subprocess.run(
                ["pgrep", "-f", f"Xvfb {display_var}"], capture_output=True, text=True
            )
            if result.stdout.strip():
                logger.debug(f"Xvfb started on {display_var}.")
                return
        raise RuntimeError(f"Xvfb did not start on {display_var} within 10 seconds.")

    def _get_chrome_version(self) -> Optional[int]:
        """Detect the installed Chrome major version."""
        if "win" in sys.platform.lower():
            try:
                import winreg

                reg_path = (
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
                )
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                    chrome_path, _ = winreg.QueryValueEx(key, "")
                output = subprocess.check_output(
                    [chrome_path, "--version"], shell=True, text=True
                )
                return int(re.search(r"(\d+)\.", output).group(1))
            except Exception as e:
                logger.debug(f"Registry lookup failed: {e}")

            for path in (
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ):
                if os.path.exists(path):
                    try:
                        output = subprocess.check_output(
                            [path, "--version"], shell=True, text=True
                        )
                        return int(re.search(r"(\d+)\.", output).group(1))
                    except Exception as e:
                        logger.debug(f"Failed at {path}: {e}")

            logger.error("Could not determine Chrome version on Windows.")
            return None
        else:
            try:
                output = subprocess.check_output(
                    "google-chrome --version", shell=True, text=True
                )
                return int(re.search(r"(\d+)\.", output).group(1))
            except Exception as e:
                logger.error(f"Error getting Chrome version: {e}")
                return None

    def _signal_handler(self, sig, frame):
        """Handle SIGINT for clean shutdown."""
        logger.debug("Shutting down...")
        self.close_driver()
        sys.exit(0)


# ─────────────────────────────────────────────
# Fetch patch (module-level helper, public API unchanged)
# ─────────────────────────────────────────────


def patch_fetch_for_statsig(driver):
    """Intercept fetch calls to capture the x-statsig-id header."""
    driver.execute_script("""
        if (window.__fetchPatched) return "already patched";

        window.__fetchPatched = false;
        const _origFetch = window.fetch;
        window.__xStatsigId = null;

        window.fetch = async function(...args) {
            const response = await _origFetch.apply(this, args);
            try {
                const req  = args[0];
                const opts = args[1] || {};
                const url  = typeof req === 'string' ? req : req.url;
                const hdrs = opts.headers || {};
                if (url === "https://grok.com/rest/app-chat/conversations/new") {
                    const id = hdrs["x-statsig-id"] ||
                               (typeof hdrs.get === "function" && hdrs.get("x-statsig-id"));
                    if (id) window.__xStatsigId = id;
                }
            } catch (e) {}
            return response;
        };

        window.__fetchPatched = true;
        return "patched";
    """)


from grok3api.driver_pool import DriverPool

web_driver = DriverPool(size=int(os.getenv("DRIVER_POOL_SIZE", "3")))
