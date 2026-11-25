@echo off
REM Abre el Comet del MONITOR en modo depuracion (puerto 9224) con su propio perfil.
REM El monitor lo abre solo si no esta abierto; este .bat es para abrirlo a mano.
REM
REM La primera vez, inicia sesion en Ticketmaster.co en la ventana que se abre.
REM La sesion queda guardada en el perfil y no hay que repetirla.
REM
REM Debe estar abierto mientras corre el monitor (el puerto debe coincidir con
REM RESERVA_PUERTO_DEPURACION en el script).

REM Comet instalado por usuario (LOCALAPPDATA) o para todo el equipo (Program Files)
set "COMET=%LOCALAPPDATA%\Perplexity\Comet\Application\comet.exe"
if not exist "%COMET%" set "COMET=%ProgramFiles%\Perplexity\Comet\Application\comet.exe"

if not exist "%COMET%" (
    echo ERROR: no se encontro Comet en "%COMET%"
    pause
    exit /b 1
)

REM start "Comet Reserva" "%COMET%" --remote-debugging-port=9224 --user-data-dir="C:\selenium\CometProfile" https://www.ticketmaster.co/
start "Comet Monitor" "%COMET%" --remote-debugging-port=9224 --user-data-dir="C:\selenium\CometMonitorProfile"

echo Comet del monitor iniciado en el puerto 9224.
echo Si es la primera vez, inicia sesion en Ticketmaster.co en esa ventana.
pause
