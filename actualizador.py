"""
Mantiene el monitor al dia con GitHub en el PC donde corre 24/7.

Lanza el monitor y, cada INTERVALO_REVISION segundos, hace `git fetch`. Si `origin/main`
trae commits nuevos:

1. Comprueba que se pueden aplicar sin pisar nada: rama `main`, sin cambios sin commitear en
   archivos del repo, avance directo (fast-forward) y que todos los .py que cambian compilan.
   Si algo falla, avisa por Telegram (una vez por commit) y sigue con la version que ya corre.
2. Pide al monitor que se detenga (ARCHIVO_REINICIO). El monitor lo mira antes de cada URL,
   asi que nunca se corta una lectura ni una reserva a medias.
3. `git merge --ff-only`, relanza el monitor y avisa por Telegram de la version nueva.

Si el monitor se cae solo, lo relanza tras PAUSA_TRAS_CAIDA y avisa con las ultimas lineas
que escribio. Si sale porque no hay URLs activas, espera a un commit nuevo.

El fetch es a GitHub, no a las boleteras: el ritmo de peticiones a ellas no cambia.

Se arranca con iniciar_monitor_autoactualizable.bat. Si un commit cambia este mismo archivo,
sale con SALIDA_REINICIARME y el .bat lo vuelve a lanzar con la version nueva.

Uso: python actualizador.py [script_del_monitor]
"""
import collections
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from logging.handlers import RotatingFileHandler

RAIZ = os.path.dirname(os.path.abspath(__file__))
SCRIPT_POR_DEFECTO = "monitor_todas_las_urls.py"
REMOTO = "origin"
RAMA = "main"

INTERVALO_REVISION = 60           # s entre cada git fetch
ESPERA_MAXIMA_SALIDA = 20 * 60    # s que se espera a que el monitor acabe la URL (o reserva) en curso
PAUSA_TRAS_CAIDA = 60             # s antes de relanzar un monitor que se cayo solo
INTERVALO_AVISO_CAIDA = 30 * 60   # como mucho un Telegram de caida cada 30 min
LINEAS_GUARDADAS = 40             # ultimas lineas del monitor que se guardan para el aviso de caida
LINEAS_EN_AVISO = 15

NOMBRE_ARCHIVO_REINICIO = "reiniciar_monitor.flag"   # el mismo que mira el monitor
SALIDA_SIN_URLS = 4               # el monitor sale con esto si no hay URLs activas
SALIDA_REINICIARME = 3            # el .bat relanza el actualizador si sale con esto

log = logging.getLogger("actualizador")


def configurar_registro():
    carpeta = os.path.join(RAIZ, "logs")
    os.makedirs(carpeta, exist_ok=True)
    manejador = RotatingFileHandler(os.path.join(carpeta, "actualizador.log"),
                                    maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(manejador)
    log.setLevel(logging.INFO)


def enviar_telegram(mensaje):
    """Envia un mensaje con el bot del monitor. Nunca lanza: si falla, queda en el registro."""
    try:
        sys.path.insert(0, RAIZ)
        from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        datos = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": mensaje[:4000]}).encode()
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        with urllib.request.urlopen(url, data=datos, timeout=20):
            pass
        return True
    except Exception:
        log.exception("No se pudo enviar el Telegram del actualizador")
        return False


class Actualizador:

    def __init__(self, raiz=RAIZ, script=SCRIPT_POR_DEFECTO, avisar=enviar_telegram,
                 intervalo=INTERVALO_REVISION, pausa_tras_caida=PAUSA_TRAS_CAIDA,
                 espera_maxima_salida=ESPERA_MAXIMA_SALIDA, python=sys.executable):
        self.raiz = raiz
        self.script = script
        self.avisar = avisar
        self.intervalo = intervalo
        self.pausa_tras_caida = pausa_tras_caida
        self.espera_maxima_salida = espera_maxima_salida
        self.python = python
        self.archivo_reinicio = os.path.join(raiz, NOMBRE_ARCHIVO_REINICIO)
        self.parar = threading.Event()        # para detenerlo desde las pruebas
        self.proceso = None
        self.lanzado_en = 0.0
        self.lineas = collections.deque(maxlen=LINEAS_GUARDADAS)
        self.relanzar_en = None               # hora a la que relanzar un monitor caido
        self.esperando_commit = False         # salio sin URLs: no relanzar hasta un commit nuevo
        self.ultimo_aviso_caida = 0.0
        self.avisados = set()                 # (commit, motivo) ya avisados

    # ------------------------------------------------------------------ git

    def git(self, *args, texto=True):
        r = subprocess.run(["git", *args], cwd=self.raiz, capture_output=True,
                           text=texto, encoding="utf-8" if texto else None, timeout=120)
        return r.returncode, (r.stdout.strip() if texto else r.stdout), (r.stderr.strip() if texto else r.stderr)

    def commit_local(self):
        return self.git("rev-parse", "HEAD")[1]

    def describir(self, commit):
        return self.git("log", "-1", "--format=%h %s", commit)[1]

    def buscar_version_nueva(self):
        """
        Devuelve (commit, problema). commit es el de origin/main si hay algo nuevo que aplicar;
        problema, el motivo por el que no se puede aplicar (o None).
        """
        codigo, _, error = self.git("fetch", "--quiet", REMOTO, RAMA)
        if codigo != 0:
            log.warning(f"git fetch fallo: {error}")          # sin internet, GitHub caido...
            return None, None
        remoto = self.git("rev-parse", f"{REMOTO}/{RAMA}")[1]
        local = self.commit_local()
        if remoto == local or self.git("merge-base", "--is-ancestor", remoto, local)[0] == 0:
            return None, None                                  # nada nuevo (o la copia va por delante)

        rama = self.git("rev-parse", "--abbrev-ref", "HEAD")[1]
        if rama != RAMA:
            return remoto, f"la copia de este PC esta en la rama '{rama}', no en '{RAMA}'"
        if self.git("merge-base", "--is-ancestor", local, remoto)[0] != 0:
            return remoto, ("la copia de este PC tiene commits que no estan en GitHub "
                            "(o la historia de GitHub se reescribio)")
        cambios = self.git("diff", "--name-only", "HEAD")[1]      # tracked, staged o no
        if cambios:
            archivos = ", ".join(cambios.splitlines())
            return remoto, f"hay cambios sin commitear en este PC: {archivos}"

        nombres = self.git("diff", "--name-only", "-z", local, remoto, "--", "*.py")[1]
        for nombre in filter(None, nombres.split("\0")):
            codigo, fuente, _ = self.git("show", f"{remoto}:{nombre}", texto=False)
            if codigo != 0:
                continue                                       # el commit lo borra
            try:
                compile(fuente, nombre, "exec")
            except SyntaxError as e:
                return remoto, f"error de sintaxis en {nombre}, linea {e.lineno}: {e.msg}"
        return remoto, None

    # -------------------------------------------------------------- monitor

    def lanzar(self):
        if os.path.exists(self.archivo_reinicio):
            os.remove(self.archivo_reinicio)
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        self.lineas.clear()
        self.proceso = subprocess.Popen([self.python, self.script], cwd=self.raiz, env=entorno,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.lanzado_en = time.time()
        self.relanzar_en = None
        self.esperando_commit = False
        threading.Thread(target=self._repetir_salida, args=(self.proceso,), daemon=True).start()
        log.info(f"Monitor lanzado: {self.script} ({self.describir('HEAD')})")
        print(f"[actualizador] Monitor lanzado: {self.script} ({self.describir('HEAD')})", flush=True)

    def _repetir_salida(self, proceso):
        """Pasa a la consola lo que escribe el monitor y guarda las ultimas lineas."""
        for linea in proceso.stdout:
            texto = linea.decode("utf-8", errors="replace").rstrip("\r\n")
            self.lineas.append(texto)
            try:
                print(texto, flush=True)
            except Exception:
                pass

    def corriendo(self):
        return self.proceso is not None and self.proceso.poll() is None

    def detener_monitor(self):
        """Pide al monitor que pare entre URLs y espera; si no para a tiempo, lo mata."""
        if not self.corriendo():
            return
        with open(self.archivo_reinicio, "w") as archivo:
            archivo.write("reiniciar\n")
        try:
            self.proceso.wait(timeout=self.espera_maxima_salida)
        except subprocess.TimeoutExpired:
            log.error(f"El monitor no se detuvo en {self.espera_maxima_salida} s: se mata")
            self.proceso.kill()
            self.proceso.wait()
        finally:
            if os.path.exists(self.archivo_reinicio):
                os.remove(self.archivo_reinicio)

    def revisar_caida(self):
        """Si el monitor salio sin que se le pidiera, programa el relanzamiento y avisa."""
        if self.proceso is None or self.corriendo() or self.relanzar_en or self.esperando_commit:
            return
        codigo = self.proceso.returncode
        if codigo == SALIDA_SIN_URLS:
            self.esperando_commit = True
            log.info("El monitor salio: no hay URLs activas. Se espera a un commit nuevo")
            self.avisar("⏸ El monitor no tiene ninguna URL activa y se detuvo. "
                        "Arrancará solo cuando subas un commit con URLs.")
            return
        duro = time.time() - self.lanzado_en
        log.error(f"El monitor se detuvo solo (codigo {codigo}, tras {duro:.0f} s); "
                  f"se relanza en {self.pausa_tras_caida} s")
        self.relanzar_en = time.time() + self.pausa_tras_caida
        if time.time() - self.ultimo_aviso_caida >= INTERVALO_AVISO_CAIDA:
            self.ultimo_aviso_caida = time.time()
            ultimas = "\n".join(list(self.lineas)[-LINEAS_EN_AVISO:])
            self.avisar(f"⚠ El monitor se detuvo solo (versión {self.describir('HEAD')}). "
                        f"Lo relanzo en {self.pausa_tras_caida} s.\n\nÚltimas líneas:\n{ultimas}")

    # ---------------------------------------------------------------- ciclo

    def actualizar_si_hay(self):
        """Aplica la version nueva si la hay. Devuelve True si este mismo archivo cambio."""
        remoto, problema = self.buscar_version_nueva()
        if not remoto:
            return False
        if problema:
            if (remoto, problema) not in self.avisados:
                self.avisados.add((remoto, problema))
                log.error(f"No se aplica {remoto[:7]}: {problema}")
                self.avisar(f"❌ No apliqué el commit {self.describir(remoto)}: {problema}.\n"
                            f"Sigo con la versión {self.describir('HEAD')}.")
            return False

        anterior = self.commit_local()
        cambiados = self.git("diff", "--name-only", anterior, remoto)[1].splitlines()
        self.detener_monitor()
        codigo, _, error = self.git("merge", "--ff-only", "--quiet", remoto)
        if codigo != 0:
            log.error(f"git merge fallo: {error}")
            self.avisar(f"❌ No pude aplicar {self.describir(remoto)} (git merge: {error}). "
                        f"Sigo con la versión {self.describir('HEAD')}.")
            self.avisados.add((remoto, "merge"))
            self.lanzar()
            return False

        log.info(f"Actualizado {anterior[:7]} -> {self.describir('HEAD')}")
        self.avisar(f"🔄 Monitor actualizado a {self.describir('HEAD')}")
        if os.path.basename(__file__) in cambiados:
            return True
        self.lanzar()
        return False

    def ejecutar(self):
        """Bucle principal. Devuelve el codigo de salida del proceso."""
        try:
            if self.actualizar_si_hay():
                return SALIDA_REINICIARME
            if not self.corriendo():
                self.lanzar()
            proxima_revision = time.time() + self.intervalo
            while not self.parar.is_set():
                self.revisar_caida()
                if self.relanzar_en and time.time() >= self.relanzar_en:
                    self.lanzar()
                if time.time() >= proxima_revision:
                    proxima_revision = time.time() + self.intervalo
                    try:
                        if self.actualizar_si_hay():
                            return SALIDA_REINICIARME
                    except Exception:
                        log.exception("Error revisando GitHub")
                self.parar.wait(min(1.0, self.intervalo))
            self.detener_monitor()
            return 0
        except KeyboardInterrupt:
            # Ctrl+C tambien le llega al monitor, que se detiene solo
            if self.proceso:
                try:
                    self.proceso.wait(timeout=30)
                except (subprocess.TimeoutExpired, KeyboardInterrupt):
                    self.proceso.kill()
            log.info("Actualizador detenido por el usuario")
            return 0


if __name__ == "__main__":
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    configurar_registro()
    script = sys.argv[1] if len(sys.argv) > 1 else SCRIPT_POR_DEFECTO
    if not os.path.isfile(os.path.join(RAIZ, script)):
        print(f"No existe {script} en {RAIZ}")
        sys.exit(1)
    log.info(f"Actualizador iniciado para {script}")
    sys.exit(Actualizador(script=script).ejecutar())
