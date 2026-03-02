import random
import json
from typing import Optional


class FingerprintGenerator:
    """
    Genera scripts JavaScript anti-detección para spoofing de fingerprints.
    El fingerprint es consistente durante una sesión pero varía entre reinicios.
    """

    def __init__(self,
                 canvas_seed: Optional[int] = None,
                 anti_detection_level: str = "full",
                 hardware_concurrency: int = 8,
                 device_memory: int = 8,
                 platform: str = "Win32",
                 vendor: str = "Google Inc.",
                 max_touch_points: int = 0,
                 max_texture_size: int = 16384):
        """
        Inicializa el generador de fingerprints.

        Args:
            canvas_seed: Semilla aleatoria para ruido de Canvas (auto-generada si es None)
            anti_detection_level: Nivel de anti-detección (basic, standard, full)
            hardware_concurrency: Número de núcleos de CPU simulados
            device_memory: Memoria del dispositivo en GB
            platform: Plataforma del navegador
            vendor: Fabricante del navegador
            max_touch_points: Número máximo de puntos táctiles
            max_texture_size: Tamaño máximo de textura WebGL
        """
        self.canvas_seed = canvas_seed if canvas_seed is not None else random.randint(100000, 999999)
        self.anti_detection_level = anti_detection_level
        self.hardware_concurrency = hardware_concurrency
        self.device_memory = device_memory
        self.platform = platform
        self.vendor = vendor
        self.max_touch_points = max_touch_points
        self.max_texture_size = max_texture_size

    def generate_anti_detection_script(self) -> str:
        """
        Genera el script completo de anti-detección JavaScript.

        Returns:
            str: Código JavaScript para inyectar en el navegador
        """
        script = ""

        script += self._hide_webdriver()
        script += "\n\n"
        script += self._spoof_canvas_fingerprint()
        script += "\n\n"
        script += self._spoof_webgl()
        script += "\n\n" if self.anti_detection_level == "full" else ""
        script += self._spoof_navigator_properties()
        script += "\n\n" if self.anti_detection_level == "full" else ""
        script += self._spoof_audio_context()
        script += "\n\n"
        script += self._spoof_screen_resolution()
        script += "\n\n"
        script += self._spoof_timezone()
        script += "\n\n"
        script += self._spoof_plugins()
        script += "\n\n"
        script += self._spoof_languages()
        script += "\n\n"
        script += self._prevent_webrtc_leak() if self.anti_detection_level == "full" else ""
        script += "\n\n" if self.anti_detection_level == "full" else ""
        script += self._protect_font_fingerprint() if self.anti_detection_level == "full" else ""

        return script

    def _hide_webdriver(self) -> str:
        return """
// Hide webdriver flag
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
"""

    def _spoof_canvas_fingerprint(self) -> str:
        if self.anti_detection_level == "basic":
            return """
// Canvas fingerprint noise (basic)
const _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function() {
    const ctx = this.getContext('2d');
    if (ctx) {
        const img = ctx.getImageData(0, 0, this.width, this.height);
        img.data[0] = img.data[0] ^ 1;
        ctx.putImageData(img, 0, 0);
    }
    return _origToDataURL.apply(this, arguments);
};
"""

        return f"""
// Canvas fingerprint noise (enhanced with distributed noise)
const _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function() {{
    const ctx = this.getContext('2d');
    if (ctx) {{
        const img = ctx.getImageData(0, 0, this.width, this.height);
        const data = img.data;

        // Distributed noise with consistent seed
        const seed = {self.canvas_seed};
        const noise = [];
        for (let i = 0; i < 256; i++) {{{
            noise[i] = ((seed * (i + 1) * 1103515245 + 12345) & 0x7fff) % 3 - 1;
        }}}

        for (let i = 0; i < data.length; i += 4) {{{
            const idx = (i / 4) % 256;
            data[i] = Math.max(0, Math.min(255, data[i] + noise[idx]));
            data[i+1] = Math.max(0, Math.min(255, data[i+1] + noise[(idx + 85) % 256]));
            data[i+2] = Math.max(0, Math.min(255, data[i+2] + noise[(idx + 170) % 256]));
        }}}

        ctx.putImageData(img, 0, 0);
    }}
    return _origToDataURL.apply(this, arguments);
}};

// Also spoof getImageData
const _origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
CanvasRenderingContext2D.prototype.getImageData = function() {{
    const result = _origGetImageData.apply(this, arguments);
    const data = result.data;

    const seed = {self.canvas_seed};
    const noise = [];
    for (let i = 0; i < 256; i++) {{{
        noise[i] = ((seed * (i + 1) * 1103515245 + 12345) & 0x7fff) % 3 - 1;
    }}}

    for (let i = 0; i < data.length; i += 4) {{{
        const idx = (i / 4) % 256;
        data[i] = Math.max(0, Math.min(255, data[i] + noise[idx]));
        data[i+1] = Math.max(0, Math.min(255, data[i+1] + noise[(idx + 85) % 256]));
        data[i+2] = Math.max(0, Math.min(255, data[i+2] + noise[(idx + 170) % 256]));
    }}}

    return result;
}};
"""

    def _spoof_webgl(self) -> str:
        webgl_params = {
            "MAX_TEXTURE_SIZE": self.max_texture_size,
            "MAX_RENDERBUFFER_SIZE": self.max_texture_size,
            "MAX_VERTEX_ATTRIBS": 16,
            "MAX_VERTEX_UNIFORM_VECTORS": 4096,
            "MAX_FRAGMENT_UNIFORM_VECTORS": 1024,
            "MAX_VARYING_VECTORS": 30,
            "MAX_VERTEX_TEXTURE_IMAGE_UNITS": 16,
            "MAX_COMBINED_TEXTURE_IMAGE_UNITS": 32,
            "MAX_TEXTURE_IMAGE_UNITS": 16,
            "MAX_CUBE_MAP_TEXTURE_SIZE": 16384,
            "ALIASED_LINE_WIDTH_RANGE": "[1,1]",
            "ALIASED_POINT_SIZE_RANGE": "[1,1024]",
            "MAX_VIEWPORT_DIMS": f"[{self.max_texture_size},{self.max_texture_size}]",
        }

        params_js = json.dumps(webgl_params)

        spoofed_extensions = [
            "ANGLE_instanced_arrays",
            "EXT_blend_minmax",
            "EXT_color_buffer_half_float",
            "EXT_disjoint_timer_query",
            "EXT_float_blend",
            "EXT_frag_depth",
            "EXT_shader_texture_lod",
            "EXT_texture_compression_bptc",
            "EXT_texture_compression_rgtc",
            "EXT_texture_filter_anisotropic",
            "WEBKIT_EXT_texture_filter_anisotropic",
            "EXT_sRGB",
            "OES_element_index_uint",
            "OES_fbo_render_mipmap",
            "OES_standard_derivatives",
            "OES_texture_float",
            "OES_texture_float_linear",
            "OES_texture_half_float",
            "OES_texture_half_float_linear",
            "OES_vertex_array_object",
            "WEBGL_color_buffer_float",
            "WEBGL_compressed_texture_s3tc",
            "WEBKIT_WEBGL_compressed_texture_s3tc",
            "WEBGL_debug_renderer_info",
            "WEBGL_debug_shaders",
            "WEBGL_depth_texture",
            "WEBKIT_WEBGL_depth_texture",
            "WEBGL_draw_buffers",
            "WEBGL_lose_context",
            "WEBGL_multi_draw",
            "WEBGL_shared_resources",
        ]

        extensions_js = json.dumps(spoofed_extensions)

        if self.anti_detection_level == "basic":
            return f"""
// WebGL vendor / renderer spoofing (basic)
function spoofWebGL(ctx) {{
    const _orig = ctx.prototype.getParameter;
    ctx.prototype.getParameter = function(parameter) {{
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return _orig.apply(this, arguments);
    }};
}}
spoofWebGL(WebGLRenderingContext);
if (typeof WebGL2RenderingContext !== 'undefined') spoofWebGL(WebGL2RenderingContext);
"""

        return f"""
// WebGL spoofing (full)
const WEBGL_SPOOF = {params_js};

const SPOOFED_EXTENSIONS = {extensions_js};

function spoofWebGL(ctx) {{
    const _origGetParameter = ctx.prototype.getParameter;
    ctx.prototype.getParameter = function(parameter) {{
        // Vendor and renderer
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        if (parameter === 7937) return 'Intel Iris OpenGL Engine';  // UNMASKED_RENDERER_WEBGL

        // Spoofed parameters
        const paramNames = [
            'MAX_TEXTURE_SIZE', 'MAX_RENDERBUFFER_SIZE', 'MAX_VERTEX_ATTRIBS',
            'MAX_VERTEX_UNIFORM_VECTORS', 'MAX_FRAGMENT_UNIFORM_VECTORS',
            'MAX_VARYING_VECTORS', 'MAX_VERTEX_TEXTURE_IMAGE_UNITS',
            'MAX_COMBINED_TEXTURE_IMAGE_UNITS', 'MAX_TEXTURE_IMAGE_UNITS',
            'MAX_CUBE_MAP_TEXTURE_SIZE', 'ALIASED_LINE_WIDTH_RANGE',
            'ALIASED_POINT_SIZE_RANGE', 'MAX_VIEWPORT_DIMS'
        ];

        for (let i = 0; i < paramNames.length; i++) {{
            const name = paramNames[i];
            const value = WEBGL_SPOOF[name];
            if (value !== undefined) {{
                const key = 0x84CF + i;
                if (parameter === key) return value;
            }}
        }}

        return _origGetParameter.apply(this, arguments);
    }};

    // Spoof getSupportedExtensions
    const _origGetSupportedExtensions = ctx.prototype.getSupportedExtensions;
    ctx.prototype.getSupportedExtensions = function() {{
        return _origGetSupportedExtensions.apply(this, arguments).concat(SPOOFED_EXTENSIONS);
    }};

    // Spoof getExtension
    const _origGetExtension = ctx.prototype.getExtension;
    ctx.prototype.getExtension = function(name) {{
        if (SPOOFED_EXTENSIONS.includes(name)) return {{
            // Return minimal mock object
        }};
        return _origGetExtension.apply(this, arguments);
    }};
}}

spoofWebGL(WebGLRenderingContext);
if (typeof WebGL2RenderingContext !== 'undefined') spoofWebGL(WebGL2RenderingContext);
"""

    def _spoof_navigator_properties(self) -> str:
        return f"""
// Navigator properties spoofing
Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {self.hardware_concurrency}}});
Object.defineProperty(navigator, 'deviceMemory', {{get: () => {self.device_memory}}});
Object.defineProperty(navigator, 'platform', {{get: () => '{self.platform}'}});
Object.defineProperty(navigator, 'vendor', {{get: () => '{self.vendor}'}});
Object.defineProperty(navigator, 'maxTouchPoints', {{get: () => {self.max_touch_points}}});
Object.defineProperty(navigator, 'pdfViewerEnabled', {{get: () => true}});
"""

    def _spoof_audio_context(self) -> str:
        if self.anti_detection_level == "basic":
            return """
// AudioContext fingerprint noise (basic)
const _origGetChannelData = AudioBuffer.prototype.getChannelData;
AudioBuffer.prototype.getChannelData = function() {
    const data = _origGetChannelData.apply(this, arguments);
    for (let i = 0; i < data.length; i += 100) {
        data[i] += Math.random() * 0.0001;
    }
    return data;
};
"""

        return f"""
// AudioContext fingerprint noise (enhanced)
const audio_seed = {self.canvas_seed + 12345};

const _origGetChannelData = AudioBuffer.prototype.getChannelData;
AudioBuffer.prototype.getChannelData = function() {{
    const data = _origGetChannelData.apply(this, arguments);

    // Generate consistent noise based on buffer index
    for (let i = 0; i < data.length; i++) {{
        const noise = ((audio_seed * (i + 1) * 1103515245 + 54321) & 0x7fff) / 0x7fff - 0.5;
        data[i] += noise * 0.0002;
    }}

    return data;
}};

// Also spoof createBuffer
const _origCreateBuffer = AudioContext.prototype.createBuffer;
AudioContext.prototype.createBuffer = function(channels, length, sampleRate) {{
    const buffer = _origCreateBuffer.apply(this, arguments);

    // Add consistent noise to all channels
    for (let channel = 0; channel < channels; channel++) {{
        const data = buffer.getChannelData(channel);
        for (let i = 0; i < data.length; i++) {{
            const noise = ((audio_seed * (i + channel * 100 + 1) * 1103515245 + 54321) & 0x7fff) / 0x7fff - 0.5;
            data[i] += noise * 0.0001;
        }}
    }}

    return buffer;
}};
"""

    def _spoof_screen_resolution(self) -> str:
        return f"""
// Screen resolution spoofing
Object.defineProperty(screen, 'width', {{get: () => 1920}});
Object.defineProperty(screen, 'height', {{get: () => 1080}});
Object.defineProperty(screen, 'availWidth', {{get: () => 1920}});
Object.defineProperty(screen, 'availHeight', {{get: () => 1040}});
Object.defineProperty(screen, 'colorDepth', {{get: () => 24}});
Object.defineProperty(screen, 'pixelDepth', {{get: () => 24}});
Object.defineProperty(window, 'innerWidth', {{get: () => 1920}});
Object.defineProperty(window, 'innerHeight', {{get: () => 1080}});
Object.defineProperty(window, 'outerWidth', {{get: () => 1920}});
Object.defineProperty(window, 'outerHeight', {{get: () => 1080}});
"""

    def _spoof_timezone(self) -> str:
        return """
// Timezone spoofing
const _origResolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
Intl.DateTimeFormat.prototype.resolvedOptions = function() {
    return {
        ..._origResolvedOptions.apply(this, arguments),
        timeZone: 'America/New_York',
        timeZoneName: 'short'
    };
};

// Spoof getTimezoneOffset
const _origGetTimezoneOffset = Date.prototype.getTimezoneOffset;
Date.prototype.getTimezoneOffset = function() {
    // America/New_York is UTC-5 or UTC-4 depending on DST
    const _origToISOString = Date.prototype.toISOString;
    const this_year = new Date().getFullYear();
    const dst_start = new Date(_origToISOString.call(new Date(this_year, 2, 14)));
    const dst_end = new Date(_origToISOString.call(new Date(this_year, 10, 7)));
    const now = new Date(_origToISOString.call(this));

    if (now >= dst_start && now < dst_end) {
        return 240; // EDT: UTC-4, offset in minutes
    }
    return 300; // EST: UTC-5, offset in minutes
};
"""

    def _spoof_plugins(self) -> str:
        return """
// Plugins spoofing
Object.defineProperty(navigator, 'plugins', {get: () => {
    const arr = [
        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
        {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
        {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''},
    ];
    arr.item = i => arr[i];
    arr.namedItem = n => arr.find(p => p.name === n);
    arr.refresh = () => {};
    return arr;
}});
"""

    def _spoof_languages(self) -> str:
        return """
// Languages spoofing
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'language', {get: () => 'en-US'});
"""

    def _prevent_webrtc_leak(self) -> str:
        return """
// WebRTC leak prevention
(function() {
    const originalRTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection;

    if (originalRTCPeerConnection) {
        window.RTCPeerConnection = function(...args) {
            const config = args[0] || {};

            // Clear ICE servers to prevent IP leak
            config.iceServers = [];

            return new originalRTCPeerConnection(...args);
        };

        window.RTCPeerConnection.prototype = originalRTCPeerConnection.prototype;
        window.webkitRTCPeerConnection = window.RTCPeerConnection;
        window.mozRTCPeerConnection = window.RTCPeerConnection;
    }
})();
"""

    def _protect_font_fingerprint(self) -> str:
        return """
// Font fingerprint protection
(function() {
    const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth');
    const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');

    function normalizeMeasurement(original, seed_mod) {
        const originalVal = original.get.call(this);
        if (typeof originalVal !== 'number') return originalVal;

        // Add small, consistent variation
        const variation = (originalVal * (seed_mod % 10)) / 10000;
        return originalVal + variation;
    }

    if (originalOffsetWidth) {
        Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
            get: function() {
                return normalizeMeasurement.call(this, originalOffsetWidth, 7);
            },
            configurable: true
        });
    }

    if (originalOffsetHeight) {
        Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
            get: function() {
                return normalizeMeasurement.call(this, originalOffsetHeight, 13);
            },
            configurable: true
        });
    }

    // Protect clientWidth and clientHeight as well
    const originalClientWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientWidth');
    const originalClientHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientHeight');

    if (originalClientWidth) {
        Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
            get: function() {
                return normalizeMeasurement.call(this, originalClientWidth, 17);
            },
            configurable: true
        });
    }

    if (originalClientHeight) {
        Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
            get: function() {
                return normalizeMeasurement.call(this, originalClientHeight, 19);
            },
            configurable: true
        });
    }
})();
"""

    def get_seed(self) -> int:
        """Returns the canvas seed for this session."""
        return self.canvas_seed
