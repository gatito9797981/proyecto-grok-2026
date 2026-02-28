import time
import sys
from grok3api.client import GrokClient
from colorama import init, Fore, Style

# Inicializar colorama para una salida profesional
init(autoreset=True)

def print_banner():
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}")
    print(f"{Fore.WHITE}{Style.BRIGHT}   Grok3API PROFESSIONAL DIAGNOSTIC & PERFORMANCE TEST")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}\n")

def run_professional_test():
    print_banner()
    
    metrics = {
        "start_time": 0,
        "end_time": 0,
        "init_duration": 0,
        "request_duration": 0,
        "success": False
    }

    try:
        # 1. Validación de Inicialización
        print(f"{Fore.YELLOW}[1/4] Inicializando Cliente Grok3API...")
        start_init = time.time()
        client = GrokClient()
        metrics["init_duration"] = time.time() - start_init
        print(f"{Fore.GREEN}✅ Cliente inicializado en {metrics['init_duration']:.2f}s\n")

        # 2. Prueba de Prompt y Rendimiento
        prompt = "Explica brevemente qué es la entropía y dame un ejemplo cotidiano."
        print(f"{Fore.YELLOW}[2/4] Enviando Prompt de Validación...")
        print(f"{Fore.WHITE}Prompt: {Style.DIM}'{prompt}'")
        
        start_req = time.time()
        result = client.ask(prompt)
        metrics["request_duration"] = time.time() - start_req
        
        # 3. Análisis de Respuesta
        print(f"\n{Fore.YELLOW}[3/4] Analizando Integridad de la Respuesta...")
        
        if not result or not result.modelResponse:
            raise ValueError("La respuesta del modelo es nula o inválida.")

        response_text = result.modelResponse.message
        char_count = len(response_text)
        
        print(f"{Fore.GREEN}✅ Respuesta recibida exitosamente.")
        print(f"{Fore.CYAN}--- Metadatos de Respuesta ---")
        print(f"ID de Respuesta: {result.responseId}")
        print(f"¿Estuvo pensando?: {result.isThinking}")
        print(f"Longitud: {char_count} caracteres")
        print(f"Tiempo de respuesta (TTB): {metrics['request_duration']:.2f}s")
        print(f"Velocidad aprox: {char_count / metrics['request_duration']:.2f} chars/sec")
        print(f"{Fore.CYAN}----------------------------\n")

        print(f"{Fore.WHITE}{Style.BRIGHT}Contenido:")
        print(f"{Fore.WHITE}{response_text[:500]}..." if char_count > 500 else f"{Fore.WHITE}{response_text}")
        print("\n")

        # 4. Verificación de Funcionalidades Adicionales
        print(f"{Fore.YELLOW}[4/4] Verificando Objetos de Imagen...")
        img_count = len(result.modelResponse.generatedImages)
        print(f"Imágenes generadas en esta sesión: {img_count}")
        
        metrics["success"] = True

    except Exception as e:
        print(f"\n{Fore.RED}{Style.BRIGHT}❌ ERROR CRÍTICO EN EL TEST: {str(e)}")
        metrics["success"] = False

    finally:
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*60}")
        status_color = Fore.GREEN if metrics["success"] else Fore.RED
        status_text = "PASSED" if metrics["success"] else "FAILED"
        print(f"RESULTADO FINAL: {status_color}{Style.BRIGHT}{status_text}")
        print(f"Tiempo Total de Ejecución: {time.time() - start_init if 'start_init' in locals() else 0:.2f}s")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}")

if __name__ == "__main__":
    run_professional_test()
