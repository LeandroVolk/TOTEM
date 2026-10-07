import subprocess

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from camera import FfmpegCamera
from config import (
    CAMERA_DEVICE,
    FPS,
    HEIGHT,
    LIMITE_SAIDA_FRAMES,
    POSE_MIN_DETECTION_CONFIDENCE,
    POSE_MODEL_PATH,
    WELCOME_VIDEO_PATH,
    WIDTH,
)


class PessoaDetector:
    def __init__(
        self,
        model_path=POSE_MODEL_PATH,
        min_detection_confidence=POSE_MIN_DETECTION_CONFIDENCE,
        limite_saida_frames=LIMITE_SAIDA_FRAMES,
    ):
        base_options = python.BaseOptions(model_asset_path=str(model_path))
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            min_pose_detection_confidence=min_detection_confidence,
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)
        self.pessoa_presente = False
        self.frames_sem_pessoa = 0
        self.limite_saida_frames = limite_saida_frames

    def detectar(self, frame):
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=frame,
        )
        resultado = self.detector.detect(mp_image)
        return bool(resultado.pose_landmarks)

    def atualizar(self, frame, peso_frames=1):
        pessoa_detectada = self.detectar(frame)
        entrou = False
        saiu = False

        if pessoa_detectada:
            self.frames_sem_pessoa = 0
            if not self.pessoa_presente:
                self.pessoa_presente = True
                entrou = True
        elif self.pessoa_presente:
            self.frames_sem_pessoa += peso_frames

        if self.frames_sem_pessoa >= self.limite_saida_frames:
            self.pessoa_presente = False
            self.frames_sem_pessoa = 0
            saiu = True

        return {
            "presente": self.pessoa_presente,
            "detectada_agora": pessoa_detectada,
            "entrou": entrou,
            "saiu": saiu,
            "frames_sem_pessoa": self.frames_sem_pessoa,
        }

    def close(self):
        self.detector.close()


def main():
    camera = FfmpegCamera(CAMERA_DEVICE, WIDTH, HEIGHT, FPS).start()
    detector = PessoaDetector()

    print("Deteccao de pessoa iniciada.")
    print("Ctrl+C para sair.")

    try:
        while True:
            frame = camera.read()
            if frame is None:
                print("Falha ao receber frame.")
                break

            estado = detector.atualizar(frame)
            if estado["entrou"]:
                print("PESSOA ENTROU")
                subprocess.run([
                    "mpv",
                    "--fs",
                    "--really-quiet",
                    str(WELCOME_VIDEO_PATH),
                ])
                camera.discard(10)
            if estado["saiu"]:
                print("PESSOA SAIU")

    except KeyboardInterrupt:
        print("\nEncerrado.")

    finally:
        camera.close()
        detector.close()


if __name__ == "__main__":
    main()
