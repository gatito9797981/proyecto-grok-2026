🚀 A Python library for interacting with the Grok 3 API without requiring login or manual cookie input. Perfect for out-of-the-box use.



## [➡ Ru ReadMe](docs/Ru/RuReadMe.md)

# 🤖 Grok3API: Client for Working with Grok

![Python](https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white)
![Made with ❤️](https://img.shields.io/badge/Made%20with-%F0%9F%92%9C-red)

![Stars](https://img.shields.io/github/stars/boykopovar/Grok3API?style=social)
![Forks](https://img.shields.io/github/forks/boykopovar/Grok3API?style=social)
![Issues](https://img.shields.io/github/issues/boykopovar/Grok3API?style=social)


**Grok3API** is a powerful and user-friendly unofficial tool for interacting with Grok models (including Grok3), allowing you to send requests, receive text responses, and, most excitingly, **generated images** — all with automatic cookie management! 🎨✨ The project is designed with simplicity and automation in mind, so you can focus on creativity rather than technical details.


---

## [📦 Full Changelog](docs/En/ChangeLog.md)

### 🆕 v0.1.0b1

#### ✨ New:

* 🛠 **Improved code block handling**
  Added automatic transformation of nested blocks `<xaiArtifact contentType="text/...">...</xaiArtifact>` into standard Markdown code blocks with language indication.

* ☑️ The feature can be disabled by setting the `auto_transform_code_blocks=False` parameter when creating `GrokClient`.


---



## 🌟 Features

- 🚀 **Automatic cookie retrieval** via browser with Cloudflare bypass — no manual setup required!  
- 🛡️ **Advanced Anti-detection**: Built-in fingerprint spoofing (Canvas noise, WebGL context, AudioContext, Screen resolution, and Timezone emulation).
- 🧬 **Driver Pool**: Support for parallel requests using a thread-safe pool of independent Chrome instances.
- 🎮 **Simplified UI**: Professional terminal chat that automatically connects to your browser's default model.
- 🖼️ **Convenient retrieval of generated images** with the `save_to` method, enabling one-click saving.  
- 🔧 **Flexible request customization**: model selection, image generation control, attachment support, and more.  
- 📦 **Attachment support**: send files and images along with requests.  
- 🛠️ **Error handling**: the client automatically resolves cookie issues and retries requests if something goes wrong.  
- 🤖 **[Example Telegram bot](tests/SimpleTgBot/SimpleTgBot.py) (`grok3api` + `aiogram`)**  
---

## 📦 Installation

To start using GrokClient, install the required dependencies. It’s simple:

```bash
pip install grok3api
```

> ⚠️ **Important**: Ensure **Google Chrome** is installed, as `undetected_chromedriver` relies on it.

After installation, you’re ready to go! 🎉

---

## 🚀 Usage

### Quick Start  

🍀 Minimal working example:
```python
from grok3api.client import GrokClient

client = GrokClient()
answer = client.ask("Hi! How are you?")

print(answer.modelResponse.message)
```


Here’s a complete example of sending a request and saving a generated image:

```python
from grok3api.client import GrokClient

# Create a client (cookies are automatically retrieved if not provided)
client = GrokClient()

# Create a request
message = "Create an image of a ship"

# Send the request
result = client.ask(message=message,
                    images="C:\\Folder\\photo1_to_grok.jpg") # You can send an image to Grok

print("Grok's response:", result.modelResponse.message)

# Save the first image, if available
if result.modelResponse.generatedImages:
    result.modelResponse.generatedImages[0].save_to("ship.jpg")
    print("Image saved as ship.jpg! 🚀")
```

This code:  
1. **Creates a client** — automatically retrieves cookies if none are provided.  
2. **Sends a request** to generate an image.  
3. **Saves the image** to the file `ship.jpg`.  

📌 **What will we see?**  
Grok will generate an image of a **ship**, for example, something like this:  

<img src="assets/ship.jpg" alt="Ship example" width="500">

🐹 Or, for instance, if you request "**A gopher on Elbrus**":

<img src="assets/gopher.jpg" alt="Gopher on Elbrus" width="500">

> 💡 **Cool feature**: You don’t need to manually fetch cookies — the client handles it for you!

---

## 🔧 Request Parameters

The `GrokClient.ask` method accepts various parameters to customize your request. Here’s an example with settings:

```python
from grok3api.client import GrokClient


client = GrokClient(history_msg_count=5, always_new_conversation=False) # to use conversation history from grok.com
client.history.set_main_system_prompt("Respond briefly and with emojis.")

# Send a request with settings
result = client.ask(
    message="Draw a cat like in this picture",
    modelName="grok-3",  # Default is grok-3 anyway
    images=["C:\\Users\\user\\Downloads\\photo1_to_grok.jpg",
            "C:\\Users\\user\\Downloads\\photo2_to_grok.jpg"] # You can send multiple images to Grok!
)
print(f"Grok3 response: {result.modelResponse.message}")

# Save all images
for i, img in enumerate(result.modelResponse.generatedImages):
    img.save_to(f"cat_{i}.jpg")
    print(f"Saved: cat_{i}.jpg 🐾")
```

> 🌟 **The best part? It works with automatically retrieved cookies!** No need to worry about access — the client sets everything up for you.

---

## 🔄 Automatic Cookie Retrieval

If cookies are missing or expired, Grok3API automatically:  
1. Uses the Chrome browser (ensure it’s installed).  
2. Visits `https://grok.com/`.  
3. Bypasses Cloudflare protection.  
4. Continues operation.  

You don’t need to do anything manually — just run the code, and it works!

### [💼️ `GrokClient` Class Description](docs/En/ClientDoc.md)  
### [✈️ `ask` Method Description](docs/En/askDoc.md)  
### [📋 `History` Class Description](docs/En/HistoryDoc.md)  
### [📬 `GrokResponse` Class Description](docs/En/GrokResponse.md)  
### [🐧 Working with `Linux`](docs/En/LinuxDoc.md)  
### [🌐 Running an OpenAI-Compatible Server](docs/En/OpenAI_Server.md)  

---

## 🖼️ Convenient Image Retrieval

One of the standout features of GrokClient is its **super-convenient handling of generated images**. Here’s a complete example:

```python
from grok3api.client import GrokClient

client = GrokClient()
result = client.ask("Draw a sunset over the sea")

for i, image in enumerate(result.modelResponse.generatedImages):
    image.save_to(f"sunset_{i}.jpg")
    print(f"Saved: sunset_{i}.jpg 🌅")
```

---

## 📋 Response Handling

The `ask` method returns a `GrokResponse` object.

Fields of the `GrokResponse` object:  
- **`modelResponse`**: The main model response.  
  - `message` (str): The text response.  
  - `generatedImages` (List[GeneratedImage]): List of images.  
- **`isThinking`**: Whether the model was thinking (bool).  
- **`isSoftStop`**: Soft stop (bool).  
- **`responseId`**: Response ID (str).  
- **`newTitle`**: New chat title, if available (Optional[str]).  

### [📬 Detailed `GrokResponse` Class Description](docs/En/GrokResponse.md)

---

## 🚀 Recent Major Updates (Backup 2 Optimizations)

We have implemented a series of high-level optimizations to make the API even more robust and stealthy:

### 🧬 Architecture: Multi-instance Driver Pool
- **`DriverPool` Support**: Switched from a single browser instance to a thread-safe pool.
- **Concurrent Requests**: Multiple threads can now interact with Grok simultaneously without session collisions.
- **Auto-Recovery**: Failed driver instances are automatically re-initialized before returning to the pool.

### 🎨 UX/UI: Terminal Pro Experience
- **Interactive Selectors**: Integrated `questionary` for smooth model selection using arrow keys (↑↓).
- **One-Click Launch**: Added `RUN_CHAT.bat` for automatic Conda environment activation and chat startup.
- **Rich Formatting**: Full support for `rich` library for aesthetic tables, panels, and live status updates.
- **Python 3.13 Compatibility**: Fixed `imghdr` removal issue with custom byte-level detection.

### 🛡️ Advanced Anti-detection Implementation
- **Enhanced Canvas Noise**: Implemented bit-level XOR noise on image data for a truly unique fingerprint.
- **WebGL 1 & 2 Spoofing**: Dual-context vendor and renderer mask (Intel Iris Engine) to prevent hardware identification.
- **AudioContext Fingerprinting**: Added randomized noise to AudioBuffer channel data.
- **Screen & Timezone Emulation**: Fixed resolution to 1920x1080 and Timezone to 'America/New_York' for consistency.
- **Realistic Plugins**: Emulated real Chrome PDF and Native Client plugins to pass advanced bot detection tests.

---

## 🚀 xAI Updates — February 2026 (Major Fixes)

We have integrated significant architectural improvements and critical bug fixes to ensure 100% compatibility with the latest Grok 4.x/3.x updates:

### 🛠️ Core Client Refactoring
- **Modular `ask()`**: The main request method has been split into 5 atomic sub-methods (`_build_headers`, `_prepare_attachments`, `_build_payload`, `_execute_with_retry`, `_process_response`) for maximum stability and easier debugging.
- **FIX #1: History Logic**: Resolved the critical bug where the assistant would incorrectly save the user's prompt as its own response.
- **FIX #2: Deepsearch Key**: Fixed the typo `deepsearch preset` → `deepsearch_preset` that prevented Deep Search from working.
- **Internal Retries**: Implemented a robust `_execute_with_retry` layer that handles rate limits, Cloudflare "Just a moment" screens, and automatic session restarts.

### 🌐 Dynamic Configuration (.env)
You can now control the infrastructure without touching the code. Add these to your `.env`:
- `DEF_PROXY`: Set your custom SOCKS/HTTP proxy globally.
- `DRIVER_POOL_SIZE`: Adjust the number of parallel Chrome instances.

### 🎭 Terminal Chat Pro
- **Automatic History**: The chat now displays previous turns automatically for better context.
- **Saturation Recovery**: Built-in 3-tier retry logic (5s wait) specifically for "Grok is under heavy usage" errors.
- **SIGTERM Support**: Clean exit handling for server environments.

---

If something’s unclear, feel free to raise an issue — we’ll figure it out together! 🌟

## Disclaimer
Grok3API has no affiliation with xAI or the Grok developers. It is an independent project created by a third party and is not supported, sponsored or endorsed by xAI. Any issues with Grok should be addressed directly to xAI.
You are responsible for ensuring that your use of Grok3API complies with all applicable laws and regulations. The developer does not encourage illegal use.
