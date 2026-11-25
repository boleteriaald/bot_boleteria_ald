"""
actualizador.py contra repositorios git reales en una carpeta temporal.

"github" es un repositorio desnudo; "casa" es el clon donde corre el monitor y "otro_pc" el
clon desde el que se suben los cambios. El monitor es un script falso que apunta cada
arranque en arranques.txt (sin seguimiento en git) y sale al ver reiniciar_monitor.flag.
"""
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import actualizador  # noqa: E402

ENTORNO_GIT = dict(os.environ, GIT_AUTHOR_NAME="prueba", GIT_AUTHOR_EMAIL="prueba@ejemplo.invalid",
                   GIT_COMMITTER_NAME="prueba", GIT_COMMITTER_EMAIL="prueba@ejemplo.invalid")

MONITOR = '''import os, sys, time
VERSION = {version}
raiz = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(raiz, "arranques.txt"), "a") as f:
    f.write(str(VERSION) + "\\n")
print("monitor version", VERSION, flush=True)
{extra}
while not os.path.exists(os.path.join(raiz, "reiniciar_monitor.flag")):
    time.sleep(0.05)
'''


def git(carpeta, *args):
    return subprocess.run(["git", *args], cwd=carpeta, env=ENTORNO_GIT, check=True,
                          capture_output=True, text=True).stdout.strip()


class TestActualizador(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        base = self._tmp.name
        self.github = os.path.join(base, "github")
        self.otro = os.path.join(base, "otro_pc")
        self.casa = os.path.join(base, "casa")
        git(base, "init", "--quiet", "--bare", "-b", "main", self.github)
        git(base, "clone", "--quiet", self.github, self.otro)
        git(self.otro, "checkout", "--quiet", "-b", "main")
        self.subir(version=1)
        git(base, "clone", "--quiet", self.github, self.casa)
        self.avisos = []
        self.act = actualizador.Actualizador(raiz=self.casa, script="monitor.py",
                                             avisar=self.avisos.append, intervalo=0.2,
                                             pausa_tras_caida=0.3, espera_maxima_salida=10)
        self.resultado = []
        self.hilo = None

    def tearDown(self):
        if self.hilo:
            self.act.parar.set()
            self.hilo.join(timeout=15)
        if self.act.proceso and self.act.proceso.poll() is None:
            self.act.proceso.kill()
            self.act.proceso.wait()
        self._tmp.cleanup()

    def subir(self, version, extra="", archivos=None):
        with open(os.path.join(self.otro, "monitor.py"), "w") as f:
            f.write(MONITOR.format(version=version, extra=extra))
        for nombre, contenido in (archivos or {}).items():
            with open(os.path.join(self.otro, nombre), "w") as f:
                f.write(contenido)
        git(self.otro, "add", "-A")
        git(self.otro, "commit", "--quiet", "-m", f"version {version}")
        git(self.otro, "push", "--quiet", "origin", "main")
        return git(self.otro, "rev-parse", "HEAD")

    def arrancar(self):
        self.hilo = threading.Thread(target=lambda: self.resultado.append(self.act.ejecutar()))
        self.hilo.start()
        self.esperar(lambda: self.arranques() == [1])

    def arranques(self):
        ruta = os.path.join(self.casa, "arranques.txt")
        if not os.path.exists(ruta):
            return []
        with open(ruta) as f:
            return [int(x) for x in f.read().split()]

    def esperar(self, condicion, segundos=15):
        limite = time.time() + segundos
        while time.time() < limite:
            if condicion():
                return
            time.sleep(0.05)
        self.fail(f"no se cumplio a tiempo; arranques={self.arranques()} avisos={self.avisos}")

    def head_casa(self):
        return git(self.casa, "rev-parse", "HEAD")

    def test_aplica_un_commit_nuevo_y_relanza_el_monitor(self):
        self.arrancar()
        nuevo = self.subir(version=2)
        self.esperar(lambda: self.arranques() == [1, 2])
        self.assertEqual(self.head_casa(), nuevo)
        self.assertTrue(any("actualizado" in a and "version 2" in a for a in self.avisos), self.avisos)
        self.assertFalse(os.path.exists(os.path.join(self.casa, "reiniciar_monitor.flag")))

    def test_al_arrancar_aplica_lo_que_haya_pendiente(self):
        nuevo = self.subir(version=2)
        self.hilo = threading.Thread(target=lambda: self.resultado.append(self.act.ejecutar()))
        self.hilo.start()
        self.esperar(lambda: self.arranques() == [2])
        self.assertEqual(self.head_casa(), nuevo)

    def test_un_commit_con_error_de_sintaxis_no_se_aplica(self):
        self.arrancar()
        anterior = self.head_casa()
        self.subir(version=2, extra="def roto(:")
        self.esperar(lambda: self.avisos)
        time.sleep(1)                                    # varias revisiones mas: un solo aviso
        self.assertEqual(len(self.avisos), 1)
        self.assertIn("error de sintaxis en monitor.py", self.avisos[0])
        self.assertEqual(self.head_casa(), anterior)
        self.assertEqual(self.arranques(), [1])          # el monitor viejo sigue corriendo
        self.assertTrue(self.act.corriendo())

    def test_cambios_locales_sin_commitear_bloquean_la_actualizacion(self):
        self.arrancar()
        with open(os.path.join(self.casa, "monitor.py"), "a") as f:
            f.write("# editado a mano en casa\n")
        anterior = self.head_casa()
        self.subir(version=2)
        self.esperar(lambda: self.avisos)
        self.assertIn("cambios sin commitear", self.avisos[0])
        self.assertIn("monitor.py", self.avisos[0])
        self.assertEqual(self.head_casa(), anterior)
        self.assertEqual(self.arranques(), [1])

    def test_un_monitor_que_se_cae_se_relanza_y_avisa_una_vez(self):
        self.arrancar()
        self.subir(version=2, extra='raise RuntimeError("boom")')
        self.esperar(lambda: self.arranques().count(2) >= 3)
        caidas = [a for a in self.avisos if "se detuvo solo" in a]
        self.assertEqual(len(caidas), 1)
        self.assertIn("RuntimeError: boom", caidas[0])

    def test_sin_urls_no_se_relanza_hasta_el_siguiente_commit(self):
        self.arrancar()
        self.subir(version=2, extra="sys.exit(4)")
        self.esperar(lambda: any("ninguna URL activa" in a for a in self.avisos))
        time.sleep(1)
        self.assertEqual(self.arranques(), [1, 2])
        self.subir(version=3)
        self.esperar(lambda: self.arranques() == [1, 2, 3])

    def test_si_cambia_el_actualizador_sale_para_que_el_bat_lo_relance(self):
        self.arrancar()
        nuevo = self.subir(version=2, archivos={"actualizador.py": "# version nueva\n"})
        self.hilo.join(timeout=15)
        self.assertEqual(self.resultado, [actualizador.SALIDA_REINICIARME])
        self.assertEqual(self.head_casa(), nuevo)
        self.assertFalse(self.act.corriendo())
        self.hilo = None


if __name__ == "__main__":
    unittest.main()
