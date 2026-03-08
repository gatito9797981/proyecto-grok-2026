# 🤖 Proyecto Grok 2026 - Guía de Funcionamiento

Esta guía explica detalladamente qué es este proyecto, qué requisitos necesita para funcionar y cómo ponerlo en marcha.

## 🌟 ¿Qué es este proyecto?

Este proyecto es una herramienta para interactuar con la **API de Grok 3** de forma automatizada, sin necesidad de configurar cookies manualmente. Incluye un sistema avanzado de **anti-detección** para navegar de forma segura y un **Driver Pool** para manejar múltiples instancias de navegación simultáneamente.

## 📋 Requisitos del Sistema

Para que el proyecto funcione correctamente, necesitas tener instalado:

1.  **Python 3.8 o superior**: El lenguaje base del proyecto.
2.  **Google Chrome**: Es indispensable, ya que el sistema utiliza `undetected_chromedriver` para interactuar con la web de Grok.
3.  **Git**: Necesario para clonar y actualizar el repositorio.

## 🚀 Pasos para la Instalación

1.  **Instalar dependencias**:
    Abre una terminal en la carpeta del proyecto y ejecuta:
    ```bash
    pip install -e .
    ```
    *(Esto instalará todas las librerías necesarias listadas en `pyproject.toml`)*.

2.  **Configurar el entorno**:
    *   Localiza el archivo `.env.example`.
    *   Renómbralo a `.env`.
    *   Abre el archivo `.env` y configura el proxy si deseas usar uno (`DEF_PROXY`).

## 🛠️ Cómo Funciona el Proyecto

### 🧬 Anti-detección Avanzada
El sistema modifica el comportamiento del navegador para evitar ser detectado como un bot:
*   **Ruido en Canvas y WebGL**: Cambia sutilmente los gráficos para que la huella digital (fingerprint) sea única.
*   **Emulación de Pantalla**: Simula resoluciones estándar (1920x1080).
*   **AudioContext**: Añade ruido aleatorio a los datos de audio.

### 🏊 Driver Pool (Piscina de Navegadores)
En lugar de abrir un solo navegador, el proyecto puede manejar un grupo de instancias independientes. Esto permite hacer varias preguntas al mismo tiempo sin que se mezclen las sesiones.

### 💬 Chat Terminal Pro
Puedes iniciar un chat interactivo directamente desde tu consola usando el archivo batch incluido.

## 🏃 Cómo iniciar el Chat

Simplemente ejecuta el archivo:
```bash
./RUN_CHAT.bat
```
Este comando activará automáticamente el entorno y lanzará la interfaz de chat interactiva donde podrás elegir modelos y enviar mensajes.

## 📂 Estructura del Proyecto

*   `grok3api/`: El núcleo de la lógica y cliente API.
*   `docs/`: Documentación técnica detallada (en inglés y ruso).
*   `tests/`: Ejemplos de uso y bots de prueba (como un bot de Telegram).
*   `RUN_CHAT.bat`: Script de inicio rápido para Windows.

---
> **Nota**: Este es un proyecto independiente y no está afiliado oficialmente con xAI. Úsalo con responsabilidad.
