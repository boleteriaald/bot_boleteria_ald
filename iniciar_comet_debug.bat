@echo off
REM Abre Comet en modo depuracion (puerto 9223) con un perfil propio para la
REM RESERVA automatica de boletas. Es un Comet aparte del de uso diario: no toca
REM tus pestanas ni tu sesion normales.
REM
REM La primera vez, inicia sesion en Ticketmaster.co en la ventana que se abre.
REM La sesion queda guardada en el perfil y no hay que repetirla.
REM
REM Debe estar abierto mientras corre el monitor (el puerto debe coincidir con
REM RESERVA_PUERTO_DEPURACION en el script).

set COMET=%LOCALAPPDATA%\Perplexity\Comet\Application\comet.exe

if not exist "%COMET%" (
    echo ERROR: no se encontro Comet en "%COMET%"
    pause
    exit /b 1
)

start "Comet Reserva" "%COMET%" --remote-debugging-port=9223 --user-data-dir="C:\selenium\CometProfile" https://www.ticketmaster.co/

echo Comet de reserva iniciado en el puerto 9223.
echo Si es la primera vez, inicia sesion en Ticketmaster.co en esa ventana.
pause
