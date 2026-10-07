import time
from math import hypot
from pathlib import Path

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from config import (
    HAND_MIN_DETECTION_CONFIDENCE,
    HAND_MIN_PRESENCE_CONFIDENCE,
    HAND_MIN_TRACKING_CONFIDENCE,
    HAND_MODEL_PATH,
)


class GestosDetector:
    def __init__(
        self,
        model_path=HAND_MODEL_PATH,
    ):
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Modelo de mao nao encontrado: {model_path}. "
                "Baixe o hand_landmarker.task antes de executar o totem."
            )

        base_options = python.BaseOptions(model_asset_path=str(model_path))
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=HAND_MIN_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=HAND_MIN_PRESENCE_CONFIDENCE,
            min_tracking_confidence=HAND_MIN_TRACKING_CONFIDENCE,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.ultimo_timestamp_ms = 0

    def atualizar(self, frame):
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=frame,
        )
        timestamp_ms = max(int(time.monotonic() * 1000), self.ultimo_timestamp_ms + 1)
        self.ultimo_timestamp_ms = timestamp_ms
        resultado = self.detector.detect_for_video(mp_image, timestamp_ms)

        diagnostico = None
        diagnostico_numero = None
        joinha_agora = False
        numero = None
        pontos_mao = []
        for landmarks in resultado.hand_landmarks:
            diagnostico = self._diagnosticar_joinha(landmarks)
            diagnostico_numero = self._diagnosticar_numero(landmarks)
            pontos_mao = [(ponto.x, ponto.y) for ponto in landmarks]
            if diagnostico["joinha"]:
                joinha_agora = True
            numero = diagnostico_numero["numero"]
            break

        return {
            "joinha": joinha_agora,
            "mao_detectada": bool(resultado.hand_landmarks),
            "diagnostico": diagnostico,
            "numero": numero,
            "dedos_estendidos": (
                [] if diagnostico_numero is None else diagnostico_numero["dedos_estendidos"]
            ),
            "gesto_candidato": str(numero) if numero is not None else "indefinido",
            "landmarks": pontos_mao,
        }

    def close(self):
        self.detector.close()

    def _parece_joinha(self, landmarks):
        return self._diagnosticar_joinha(landmarks)["joinha"]

    def _diagnosticar_joinha(self, landmarks):
        wrist = landmarks[0]
        thumb_mcp = landmarks[2]
        thumb_ip = landmarks[3]
        thumb_tip = landmarks[4]
        pontas_dedos = [landmarks[idx] for idx in (8, 12, 16, 20)]

        polegar_mais_alto = thumb_tip.y < min(p.y for p in pontas_dedos) - 0.02
        polegar_acima_do_punho = thumb_tip.y < wrist.y - 0.05
        polegar_estendido = (
            thumb_tip.y < thumb_ip.y + 0.02
            and self._distancia(thumb_tip, thumb_mcp) > 0.08
        )
        dedos_dobrados = sum(
            self._dedo_dobrado(landmarks, mcp, pip, tip)
            for mcp, pip, tip in (
                (5, 6, 8),
                (9, 10, 12),
                (13, 14, 16),
                (17, 18, 20),
            )
        )
        dedos_abaixo_do_polegar = sum(
            ponta.y > thumb_tip.y + 0.06
            for ponta in pontas_dedos
        )

        pontuacao = sum(
            (
                polegar_mais_alto,
                polegar_acima_do_punho,
                polegar_estendido,
                dedos_dobrados >= 2,
                dedos_abaixo_do_polegar >= 3,
            )
        )

        joinha = (
            polegar_mais_alto
            and polegar_acima_do_punho
            and dedos_dobrados >= 2
            and (polegar_estendido or dedos_abaixo_do_polegar >= 3)
        )

        return {
            "joinha": joinha,
            "pontuacao": pontuacao,
            "polegar_mais_alto": polegar_mais_alto,
            "polegar_acima_do_punho": polegar_acima_do_punho,
            "polegar_estendido": polegar_estendido,
            "dedos_dobrados": dedos_dobrados,
            "dedos_abaixo_do_polegar": dedos_abaixo_do_polegar,
        }

    def _diagnosticar_numero(self, landmarks):
        indicador_estendido = self._dedo_estendido(landmarks, 5, 6, 8)
        medio_estendido = self._dedo_estendido(landmarks, 9, 10, 12)
        anelar_dobrado = self._dedo_dobrado(landmarks, 13, 14, 16)
        minimo_dobrado = self._dedo_dobrado(landmarks, 17, 18, 20)
        medio_dobrado = self._dedo_dobrado(landmarks, 9, 10, 12)

        numero = None
        if indicador_estendido and medio_dobrado and anelar_dobrado and minimo_dobrado:
            numero = 1
        elif indicador_estendido and medio_estendido and anelar_dobrado and minimo_dobrado:
            numero = 2

        dedos_estendidos = []
        for nome, estendido in (
            ("indicador", indicador_estendido),
            ("medio", medio_estendido),
            ("anelar", self._dedo_estendido(landmarks, 13, 14, 16)),
            ("minimo", self._dedo_estendido(landmarks, 17, 18, 20)),
        ):
            if estendido:
                dedos_estendidos.append(nome)

        return {"numero": numero, "dedos_estendidos": dedos_estendidos}

    @staticmethod
    def _dedo_dobrado(landmarks, mcp_idx, pip_idx, tip_idx):
        mcp = landmarks[mcp_idx]
        pip = landmarks[pip_idx]
        tip = landmarks[tip_idx]
        return tip.y >= pip.y - 0.02 or tip.y >= mcp.y

    @staticmethod
    def _dedo_estendido(landmarks, mcp_idx, pip_idx, tip_idx):
        mcp = landmarks[mcp_idx]
        pip = landmarks[pip_idx]
        tip = landmarks[tip_idx]
        return tip.y < pip.y - 0.025 and tip.y < mcp.y - 0.04

    @staticmethod
    def _distancia(a, b):
        return hypot(a.x - b.x, a.y - b.y)
