@echo off
rem Monitor con actualizacion automatica desde GitHub (ver README, "Actualizacion automatica").
rem Uso: iniciar_monitor_autoactualizable.bat [script]   (por defecto monitor_todas_las_urls.py)
rem Si un commit cambia ESTE .bat, cierralo y abrelo de nuevo a mano: cmd lee el .bat
rem mientras lo ejecuta y no recoge bien los cambios.
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

:inicio
"%PY%" actualizador.py %*
rem 3 = el actualizador se actualizo a si mismo y hay que lanzarlo de nuevo
if "%errorlevel%"=="3" goto inicio
pause
