@echo off
REM Script para iniciar Chrome en modo debugging
REM Esto permite que el script de Python se conecte a Chrome

echo ============================================================
echo INICIANDO CHROME EN MODO DEBUGGING
echo ============================================================

REM Intenta Chrome en Program Files primero
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    echo.
    echo ✓ Chrome encontrado en Program Files
    echo ✓ Iniciando en puerto 9222...
    echo.
    start "Chrome Debug Mode" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\selenium\ChromeProfile"
    goto success
)

REM Si no está, intenta Program Files (x86)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    echo.
    echo ✓ Chrome encontrado en Program Files (x86)
    echo ✓ Iniciando en puerto 9222...
    echo.
    start "Chrome Debug Mode" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\selenium\ChromeProfile"
    goto success
)

echo.
echo ✗ ERROR: Chrome no se encontró en las ubicaciones estándar
echo ✗ Por favor instala Chrome o verifica la ruta
echo.
pause
exit /b 1

:success
echo.
echo ✓ Chrome iniciado correctamente
echo ✓ Se abrirá una ventana de Chrome en modo debugging (puerto 9222)
echo ✓ Ahora puedes ejecutar: python main.py
echo.
pause
