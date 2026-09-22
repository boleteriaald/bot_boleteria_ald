"""
Base comun de las pruebas del monitor.

Cada prueba carga una copia NUEVA del script, aislada del mundo real:

- config.py se sustituye por un doble sin credenciales: nunca se leen el token
  ni el chat de Telegram reales.
- enviar_notificacion() no envia nada; guarda los mensajes en self.enviados.
- El estado de avisos y el registro van a una carpeta temporal, no a los
  archivos reales del proyecto.
- El reloj es simulado (self.reloj): sleep() no espera, solo adelanta la hora.
  Se sustituye el modulo time *del script*, no el time global de Python, para
  que ninguna prueba contamine a las demas.
"""
import importlib.util
import logging
import os
import sys
import tempfile
import time
import types
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(RAIZ, "main13_filters_all_urls lina.py")


class RelojSimulado:
    """Sustituto del modulo time del script: sleep() adelanta la hora al instante."""

    def __init__(self):
        self.ahora = 1_000_000.0
        self.esperas = []

    def time(self):
        return self.ahora

    def sleep(self, segundos):
        self.esperas.append(segundos)
        self.ahora += segundos

    def strftime(self, formato):
        return time.strftime(formato, time.localtime(self.ahora))


def cargar_monitor(carpeta):
    """Carga una copia nueva del monitor apuntando estado y registro a `carpeta`."""
    config = types.ModuleType("config")
    config.TELEGRAM_BOT_TOKEN = "token-de-prueba"
    config.TELEGRAM_CHAT_ID = "0"
    anterior = sys.modules.get("config")
    sys.modules["config"] = config
    try:
        spec = importlib.util.spec_from_file_location("monitor_bajo_prueba", SCRIPT)
        monitor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(monitor)
    finally:
        if anterior is None:
            sys.modules.pop("config", None)
        else:
            sys.modules["config"] = anterior

    # Igual que al lanzar el monitor: sin esto, los emojis de sus print() revientan
    # en consolas cp1252 como cmd.exe o PowerShell.
    monitor.preparar_consola()

    monitor.ARCHIVO_ESTADO = os.path.join(carpeta, "estado_notificaciones.json")
    monitor.CARPETA_LOGS = os.path.join(carpeta, "logs")
    monitor.ARCHIVO_LOG = os.path.join(monitor.CARPETA_LOGS, "monitor.log")
    return monitor


class CasoMonitor(unittest.TestCase):
    """Caso base: self.m es el monitor aislado, self.enviados los mensajes."""

    def setUp(self):
        self._carpeta = tempfile.TemporaryDirectory()
        self.m = cargar_monitor(self._carpeta.name)
        self.reloj = RelojSimulado()
        self.m.time = self.reloj
        self.enviados = []
        self.telegram_funciona = True

        def enviar(mensaje):
            self.enviados.append(mensaje)
            return self.telegram_funciona

        self.m.enviar_notificacion = enviar

    def tearDown(self):
        # Cerrar el archivo de registro antes de borrar la carpeta (Windows no
        # deja borrar un archivo abierto).
        for manejador in list(self.m.log.handlers):
            if not isinstance(manejador, logging.NullHandler):
                manejador.close()
                self.m.log.removeHandler(manejador)
        self._carpeta.cleanup()

    def leer_registro(self):
        for manejador in self.m.log.handlers:
            manejador.flush()
        with open(self.m.ARCHIVO_LOG, encoding="utf-8") as archivo:
            return archivo.read()
