import time
import json
import os
from grok3api.client import GrokClient
from colorama import init, Fore, Style

# Inicializar colorama
init(autoreset=True)

PROMPTS = [
    "¿Cuál es el sentido de la vida según la ciencia?",
    "Escribe un poema corto sobre la inteligencia artificial.",
    "Resume la historia de la caída del Imperio Romano en 3 frases.",
    "¿Cómo funciona una red neuronal?",
    "Dame una receta rápida de pasta carbonara.",
    "Explica la teoría de la relatividad para un niño de 5 años.",
    "¿Cuáles son los 3 países más grandes del mundo?",
    "Dime un chiste sobre programadores.",
    "¿Qué es el interés compuesto?",
    "Describe el color azul a una persona ciega."
]

REPORT_PATH = "test_results.md"

def generate_md_report(results, total_time, avg_speed):
    md_content = f"""# 🚀 Reporte de Estrés Profesional - Grok3API
Generado automáticamente tras validación de 10 prompts consecutivos.

## 📊 Resumen Ejecutivo
- **Total de Prompts:** {len(results)}
- **Tiempo Total de Prueba:** {total_time:.2f}s
- **Velocidad Promedio:** {avg_speed:.2f} chars/sec
- **Estado Global:** {"✅ EXITOSO" if all(r['success'] for r in results) else "⚠️ CON INCIDENCIAS"}

---

## 📈 Detalle de Pruebas
| # | Prompt | Tiempo | Longitud | Estado |
|---|---|---|---|---|
"""
    for i, r in enumerate(results, 1):
        status = "✅" if r['success'] else "❌"
        md_content += f"| {i} | {r['prompt'][:50]}... | {r['duration']:.2f}s | {r['length']} | {status} |\n"

    md_content += "\n--- \n\n## 📝 Registros Detallados (Logs)\n"
    
    for i, r in enumerate(results, 1):
        md_content += f"### Prueba {i}: {r['prompt']}\n"
        md_content += f"**Respuesta:**\n> {r['response'][:500]}...\n\n"
        md_content += f"- **Latencia:** {r['duration']:.2f}s\n"
        md_content += f"- **Caracteres:** {r['length']}\n"
        md_content += "---\n"

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"\n{Fore.GREEN}✨ Reporte generado exitosamente en: {REPORT_PATH}")

def run_stress_test():
    print(f"{Fore.CYAN}{Style.BRIGHT}INICIANDO TEST DE ESTRÉS DE 10 PROMPTS CONSECUTIVOS...")
    
    results = []
    client = Gro_client = None
    
    try:
        print(f"{Fore.YELLOW}Inicializando cliente y gestionando Cloudflare...")
        start_global = time.time()
        client = GrokClient()
        
        for i, prompt in enumerate(PROMPTS, 1):
            print(f"{Fore.WHITE}Ejecutando prompt {i}/10: {Fore.MAGENTA}{prompt[:40]}...")
            
            start_req = time.time()
            try:
                result = client.ask(prompt)
                duration = time.time() - start_req
                
                response_text = result.modelResponse.message
                results.append({
                    "prompt": prompt,
                    "response": response_text,
                    "duration": duration,
                    "length": len(response_text),
                    "success": True
                })
                print(f"{Fore.GREEN}   ✅ Completado en {duration:.2f}s ({len(response_text)} chars)")
                
            except Exception as req_e:
                print(f"{Fore.RED}   ❌ Fallo en prompt {i}: {req_e}")
                results.append({
                    "prompt": prompt,
                    "response": str(req_e),
                    "duration": time.time() - start_req,
                    "length": 0,
                    "success": False
                })

        total_time = time.time() - start_global
        total_chars = sum(r['length'] for r in results)
        avg_speed = total_chars / total_time if total_time > 0 else 0
        
        generate_md_report(results, total_time, avg_speed)
        
    except Exception as e:
        print(f"{Fore.RED}Error fatal en el ciclo de estrés: {e}")

if __name__ == "__main__":
    run_stress_test()
