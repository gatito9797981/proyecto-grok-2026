"""
Grok Terminal Chat — Versión Corregida
"""
import signal
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
load_dotenv(root_dir / ".env")

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.prompt import Prompt

from grok3api.client import GrokClient

console = Console()

# ─────────────────────────────────────────────
# UI helpers
# ─────────────────────────────────────────────

def render_header() -> Panel:
    text = Text()
    text.append("  GROK TERMINAL CHAT  ", style="bold white")
    text.append("│  Modo: ", style="dim white")
    text.append("Predeterminado (Navegador)", style="bold green")
    return Panel(text, box=box.ROUNDED, border_style="cyan", padding=(0, 1))


# FIX: truncado ampliado a 100/120 caracteres para más contexto útil
def render_history(history: list[tuple[str, str]]) -> Panel:
    text = Text()
    if not history:
        text.append("  Sin mensajes aún...\n", style="dim white")
    else:
        for user_msg, grok_msg in history[-6:]:
            text.append("  Tú: ", style="bold green")
            text.append(
                f"{user_msg[:100]}{'...' if len(user_msg) > 100 else ''}\n",
                style="white",
            )
            text.append("  Grok: ", style="bold magenta")
            text.append(
                f"{grok_msg[:120]}{'...' if len(grok_msg) > 120 else ''}\n\n",
                style="white",
            )
    return Panel(
        text,
        title="[bold cyan]Conversación reciente[/bold cyan]",
        box=box.ROUNDED,
        border_style="blue",
        padding=(0, 1),
    )


def render_help() -> Panel:
    text = Text()
    text.append("  nuevo     ", style="bold yellow")
    text.append("→ Nueva conversación\n", style="white")
    text.append("  limpiar   ", style="bold yellow")
    text.append("→ Limpiar pantalla\n", style="white")
    text.append("  historial ", style="bold yellow")
    text.append("→ Ver conversación reciente\n", style="white")
    text.append("  salir     ", style="bold yellow")
    text.append("→ Cerrar el chat", style="white")
    return Panel(
        text,
        title="[bold cyan]Comandos[/bold cyan]",
        box=box.ROUNDED,
        border_style="dim blue",
        padding=(0, 1),
    )


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    session_history: list[tuple[str, str]] = []

    # FIX: manejo de SIGTERM para cierre limpio en contenedores/systemd
    def _shutdown(sig, frame):
        console.print("\n[bold yellow]  Cerrando...[/bold yellow]")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)

    console.clear()
    console.print(render_header())
    console.print(render_help())
    console.print("\n[bold blue][INFO][/bold blue] Conectando con Grok...\n")

    try:
        client = GrokClient(history_msg_count=10, always_new_conversation=True)
        # FIX: reducir max_tries para no solapar con el reintento de saturación de la UI
        client.max_tries = 3
        console.print("[bold green][OK][/bold green] ¡Conexión establecida!\n")
    except Exception as e:
        console.print(f"[bold red][ERROR][/bold red] No se pudo conectar: {e}")
        input("\nPresiona Enter para cerrar...")
        return

    while True:
        try:
            user_input = Prompt.ask("[bold green]Tú[/bold green]", console=console).strip()

            if not user_input:
                continue

            cmd = user_input.lower()

            if cmd in ("salir", "exit", "quit"):
                console.print("\n[bold yellow]  Hasta luego.[/bold yellow]\n")
                break

            if cmd == "nuevo":
                client.conversationId = None
                client.parentResponseId = None
                session_history.clear()
                # FIX: no limpiar pantalla en "nuevo" — los errores previos siguen visibles
                console.print("\n[bold yellow]  Nueva conversación iniciada.[/bold yellow]\n")
                continue

            if cmd == "limpiar":
                console.clear()
                console.print(render_header())
                continue

            # FIX: comando "historial" ahora realmente muestra el historial
            if cmd == "historial":
                console.print(render_history(session_history))
                continue

            # ─────────────────────────────────────────────
            # FIX: un solo nivel de reintento específico para saturación (código 8)
            # GrokClient.max_tries ya maneja los reintentos de red internamente
            # ─────────────────────────────────────────────
            MAX_SATURATION_RETRIES = 3
            SATURATION_WAIT_SECS = 5

            result = None
            for attempt in range(MAX_SATURATION_RETRIES):
                suffix = (
                    f" (Reintento por saturación {attempt}/{MAX_SATURATION_RETRIES - 1})"
                    if attempt > 0
                    else ""
                )
                with console.status(f"[bold yellow]Grok está pensando...[/bold yellow]{suffix}"):
                    result = client.ask(user_input)

                if not result.error:
                    break

                is_saturation = (
                    result.error_code == 8
                    or "heavy usage" in str(result.error).lower()
                )
                if is_saturation and attempt < MAX_SATURATION_RETRIES - 1:
                    console.print(
                        f"[bold yellow][AVISO][/bold yellow] Grok saturado. "
                        f"Esperando {SATURATION_WAIT_SECS}s..."
                    )
                    time.sleep(SATURATION_WAIT_SECS)
                    continue

                # Otro tipo de error → no reintentar más
                break

            if result is None or result.error:
                error_code = getattr(result, "error_code", "?") if result else "?"
                error_msg = getattr(result, "error", "Sin respuesta") if result else "Sin respuesta"
                console.print(f"\n[bold red]  [ERROR {error_code}][/bold red] {error_msg}\n")
                continue

            message = result.modelResponse.message
            session_history.append((user_input, message))

            # FIX: mostrar historial actualizado después de cada respuesta
            console.print(render_history(session_history))
            console.print(Panel(
                Text(message, style="white"),
                title="[bold magenta]Grok[/bold magenta]",
                border_style="magenta",
                box=box.ROUNDED,
                padding=(1, 2),
            ))

        except KeyboardInterrupt:
            console.print("\n[bold yellow]  Interrumpido.[/bold yellow]\n")
            break
        except Exception as e:
            console.print(f"\n[bold red]  [ERROR][/bold red] {e}\n")


if __name__ == "__main__":
    main()