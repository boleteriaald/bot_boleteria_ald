"""El monitor abre y usa solo Comet, separado del Comet de reserva."""
import io
import json
from unittest import mock

from apoyo import CasoMonitor


class TestNavegadorDelMonitor(CasoMonitor):

    def test_no_queda_ninguna_ruta_de_chrome(self):
        self.assertTrue(self.m.RUTAS_NAVEGADOR)
        for ruta in self.m.RUTAS_NAVEGADOR:
            self.assertTrue(ruta.lower().endswith("comet.exe"), ruta)

    def test_separado_del_navegador_de_reserva(self):
        self.assertNotEqual(self.m.PUERTO_DEPURACION, self.m.RESERVA_PUERTO_DEPURACION)
        self.assertNotIn("CometProfile", self.m.PERFIL_NAVEGADOR)

    def test_lanzar_abre_comet_con_el_puerto_y_el_perfil_del_monitor(self):
        self.m.buscar_chrome = lambda: "comet.exe"
        with mock.patch.object(self.m.subprocess, "run") as correr:
            self.assertTrue(self.m.lanzar_chrome())
        orden = correr.call_args[0][0]
        self.assertIn("comet.exe", orden)
        self.assertIn(f"--remote-debugging-port={self.m.PUERTO_DEPURACION}", orden)
        self.assertIn(f"--user-data-dir={self.m.PERFIL_NAVEGADOR}", orden)


class TestChromedriver(CasoMonitor):

    def _conectar(self, en_cache, descargado=None):
        version = io.BytesIO(json.dumps({"Browser": "Chrome/155.0.1.2"}).encode())
        self.m.puerto_depuracion_activo = lambda puerto=None: True
        self.m._chromedriver_para = lambda v: en_cache
        self.m._descargar_chromedriver = mock.Mock(return_value=descargado)
        with mock.patch.object(self.m.urllib.request, "urlopen", return_value=version), \
                mock.patch.object(self.m, "Service") as servicio, \
                mock.patch.object(self.m.webdriver, "Chrome") as chrome:
            driver = self.m.conectar_chrome()
        return driver, servicio, chrome

    def test_usa_el_driver_de_la_version_de_comet(self):
        driver, servicio, chrome = self._conectar("driver155")
        self.assertIs(driver, chrome.return_value)
        servicio.assert_called_once_with(executable_path="driver155")
        self.m._descargar_chromedriver.assert_not_called()
        opciones = chrome.call_args.kwargs["options"]
        self.assertEqual(opciones.experimental_options["debuggerAddress"],
                         f"127.0.0.1:{self.m.PUERTO_DEPURACION}")

    def test_sin_driver_en_cache_lo_descarga(self):
        _, servicio, _ = self._conectar(None, descargado="nuevo")
        self.m._descargar_chromedriver.assert_called_once_with("155.0.1.2")
        servicio.assert_called_once_with(executable_path="nuevo")

    def test_si_la_descarga_falla_no_lanza(self):
        gestor = mock.Mock()
        gestor.run.side_effect = OSError("sin red")
        with mock.patch.object(self.m, "SeleniumManager", return_value=gestor):
            self.assertIsNone(self.m._descargar_chromedriver("155.0.1.2"))
