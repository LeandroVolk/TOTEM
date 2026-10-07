import subprocess
from threading import Condition, Thread
from time import monotonic

import numpy as np


class FfmpegCamera:
    def __init__(self, device, width, height, fps, pix_fmt="rgb24"):
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.pix_fmt = pix_fmt
        self.channels = 3 if pix_fmt == "rgb24" else 1
        self.frame_size = width * height * self.channels
        self.processo = None
        self._condicao = Condition()
        self._thread = None
        self._ultimo_frame = None
        self._sequencia = 0
        self._ultima_sequencia_lida = 0
        self._encerrada = False

    def start(self):
        cmd = [
            "ffmpeg",
            "-loglevel", "quiet",
            "-f", "v4l2",
            "-video_size", f"{self.width}x{self.height}",
            "-framerate", str(self.fps),
            "-i", self.device,
            "-f", "rawvideo",
            "-pix_fmt", self.pix_fmt,
            "-",
        ]
        self.processo = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            bufsize=self.frame_size * 2,
        )
        self._encerrada = False
        self._thread = Thread(target=self._capturar_frames, daemon=True)
        self._thread.start()
        return self

    def read(self):
        return self.read_com_timeout(None)

    def read_com_timeout(self, timeout):
        if self.processo is None:
            raise RuntimeError("Camera nao iniciada.")

        with self._condicao:
            limite = None if timeout is None else monotonic() + timeout
            while self._sequencia <= self._ultima_sequencia_lida and not self._encerrada:
                restante = None if limite is None else limite - monotonic()
                if restante is not None and restante <= 0:
                    return None
                self._condicao.wait(restante)

            if self._sequencia > self._ultima_sequencia_lida:
                self._ultima_sequencia_lida = self._sequencia
                return self._ultimo_frame
            return None

    @property
    def encerrada(self):
        return self._encerrada

    def _capturar_frames(self):
        processo = self.processo
        if processo is None or processo.stdout is None:
            return

        while True:
            dados = processo.stdout.read(self.frame_size)
            if len(dados) != self.frame_size:
                with self._condicao:
                    self._encerrada = True
                    self._condicao.notify_all()
                return

            frame = np.frombuffer(dados, dtype=np.uint8)
            if self.channels == 1:
                frame = frame.reshape((self.height, self.width))
            else:
                frame = frame.reshape((self.height, self.width, self.channels))

            with self._condicao:
                self._ultimo_frame = frame
                self._sequencia += 1
                self._condicao.notify_all()

    def discard(self, count):
        if self.processo is None:
            return

        with self._condicao:
            self._ultima_sequencia_lida = self._sequencia

    def close(self):
        if self.processo is None:
            return

        processo = self.processo
        with self._condicao:
            self._encerrada = True
            self._condicao.notify_all()
        processo.terminate()
        try:
            processo.wait(timeout=2)
        except subprocess.TimeoutExpired:
            processo.kill()
        if self._thread is not None:
            self._thread.join(timeout=1)
        self.processo = None
        self._thread = None
