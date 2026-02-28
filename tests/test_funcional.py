from grok3api.client import GrokClient
import sys

def main():
    print("Iniciando prueba de funcionamiento de Grok3API...")
    try:
        # Inicializamos el cliente
        # Nota: Esto abrirá una instancia de Chrome automáticamente para manejar las cookies si es necesario
        client = GrokClient()
        
        pregunta = "¡Hola! ¿Podrías confirmar que estás funcionando correctamente a través de la API?"
        print(f"Enviando pregunta: {pregunta}")
        
        result = client.ask(pregunta)
        
        print("\n--- Respuesta de Grok ---")
        print(result.modelResponse.message)
        print("--------------------------")
        
        if result.modelResponse.message:
            print("\n✅ Prueba superada con éxito.")
        else:
            print("\n❌ Se recibió una respuesta vacía.")
            
    except Exception as e:
        print(f"\n❌ Ocurrió un error durante la prueba: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
