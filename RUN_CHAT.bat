@echo off
setlocal
echo ============================================================
echo   INICIANDO GROK TERMINAL CHAT (AUTOMATICO)
echo ============================================================

:: Intentar activar conda usando la ruta comun en la maquina del usuario
if exist "C:\Users\Admin\anaconda3\Scripts\activate.bat" (
    call "C:\Users\Admin\anaconda3\Scripts\activate.bat" grok3api
) else (
    echo [!] No se encontro el activador de Conda en la ruta estandar.
    echo Intentando comando directo...
    call conda activate grok3api
)

echo [OK] Entorno activado.
echo [INFO] Lanzando chat interactivo...
python scripts/interactive_chat.py

if errorlevel 1 (
    echo.
    echo [ERROR] El chat se cerro con un problema.
    pause
)
