"""
Pruebas contra el Chrome real del monitor. Desactivadas por defecto.

- MONITOR_PRUEBAS_CHROME=1   conecta, comprueba la sesion y la suelta sin
                             cerrar Chrome. Necesita Chrome en modo debug y el
                             monitor DETENIDO (compartirian la pestana).
- MONITOR_PRUEBAS_RELANZAR=1 ademas CIERRA el Chrome del monitor y comprueba
                             que se relanza solo. Solo toca el Chrome que usa el
                             perfil del monitor, nunca tu navegador normal.

Nada de esto visita boleteras ni envia nada por Telegram.
"""
import os
import subprocess
import time
import unittest

from apoyo import CasoMonitor

CHROME = os.environ.get("MONITOR_PRUEBAS_CHROME") == "1"
RELANZAR = os.environ.get("MONITOR_PRUEBAS_RELANZAR") == "1"


@unittest.skipUnless(CHROME or RELANZAR, "activar con MONITOR_PRUEBAS_CHROME=1")
class TestChromeReal(CasoMonitor):

    def setUp(self):
        super().setUp()
        self.m.time = time          # esperas reales: aqui hay procesos de verdad

    def test_conectar_y_soltar_no_cierra_chrome(self):
        if not self.m.puerto_depuracion_activo():
            self.m.lanzar_chrome()
        driver = self.m.conectar_chrome()
        self.assertIsNotNone(driver)
        self.assertTrue(self.m.sesion_viva(driver))
        self.m.soltar_sesion(driver)
        self.assertTrue(self.m.puerto_depuracion_activo())
        self.assertFalse(self.m.sesion_viva(driver))

    @unittest.skipUnless(RELANZAR, "activar con MONITOR_PRUEBAS_RELANZAR=1 (cierra Chrome)")
    def test_chrome_caido_se_relanza_solo(self):
        if not self.m.puerto_depuracion_activo():
            self.m.lanzar_chrome()
        driver = self.m.conectar_chrome()
        self.assertIsNotNone(driver)

        perfil = "selenium" + chr(92) + "ChromeProfile"
        consulta = ("Get-CimInstance Win32_Process -Filter \"name='chrome.exe'\" | Where-Object { "
                    f"$_.CommandLine -like '*{perfil}*' -and $_.CommandLine -notlike '*--type=*' }} | "
                    "ForEach-Object { $_.ProcessId }")
        pids = subprocess.run(["powershell", "-NoProfile", "-Command", consulta],
                              capture_output=True, text=True).stdout.split()
        self.assertEqual(len(pids), 1, "debe haber exactamente un Chrome del monitor")
        subprocess.run(["taskkill", "/PID", pids[0], "/T", "/F"], capture_output=True)
        time.sleep(1)
        self.assertFalse(self.m.sesion_viva(driver))

        inicio = time.time()
        nuevo = self.m.recuperar_sesion(driver)
        self.assertTrue(self.m.sesion_viva(nuevo))
        self.assertLess(time.time() - inicio, 45)
        self.assertEqual(len(self.enviados), 1)
        self.assertIn("relancé", self.enviados[0])
        self.m.soltar_sesion(nuevo)
