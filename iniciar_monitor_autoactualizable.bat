@echo off
rem Monitor con actualizacion automatica desde GitHub (ver README, "Actualizacion automatica").
rem Uso: iniciar_monitor_autoactualizable.bat [script]   (por defecto monitor_todas_las_urls.py)
rem Si un commit cambia ESTE .bat, cierralo y abrelo de nuevo a mano: cmd lee el .bat
rem mientras lo ejecuta y no recoge bien los cambios.
cd /d "%~dp0"

rem Primer Python que tenga las dependencias del monitor: el de .venv, el del PATH o el
rem lanzador "py". Un .venv cuyo Python base ya no existe ("No Python at ...") se salta.
set "PY="
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import selenium, telegram" >nul 2>&1 && set "PY=.venv\Scripts\python.exe"
)
if not defined PY (
    python -c "import selenium, telegram" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    py -c "import selenium, telegram" >nul 2>&1 && set "PY=py"
)
if not defined PY (
    echo No encontre un Python con selenium y python-telegram-bot instalados.
    echo Instalalos con:  python -m pip install -r requirements.txt
    pause
    exit /b 1
)
echo Usando Python: %PY%

:inicio
"%PY%" actualizador.py %*
rem 3 = el actualizador se actualizo a si mismo y hay que lanzarlo de nuevo
if "%errorlevel%"=="3" goto inicio
pause
