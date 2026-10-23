import os
from pathlib import Path

from totem_app.settings import load_settings

BASE_DIR = Path(__file__).resolve().parent
_SETTINGS = load_settings()

CAMERA_DEVICE = _SETTINGS.camera_device
WIDTH = _SETTINGS.camera_width
HEIGHT = _SETTINGS.camera_height
FPS = _SETTINGS.camera_fps
# A pose e suficiente para presenca; roda em metade dos frames para deixar CPU
# disponivel para o rastreamento da mao durante a interacao.
POSE_INTERVALO_FRAMES = _SETTINGS.pose_interval_frames

POSE_MODEL_PATH = BASE_DIR / "pose_landmarker_lite.task"
HAND_MODEL_PATH = BASE_DIR / "hand_landmarker.task"
WELCOME_VIDEO_PATH = BASE_DIR / "bemvindo.mp4"

POSE_MIN_DETECTION_CONFIDENCE = _SETTINGS.pose_min_confidence
HAND_MIN_DETECTION_CONFIDENCE = _SETTINGS.hand_min_detection_confidence
HAND_MIN_PRESENCE_CONFIDENCE = _SETTINGS.hand_min_presence_confidence
HAND_MIN_TRACKING_CONFIDENCE = _SETTINGS.hand_min_tracking_confidence

ABANDONO_SEGUNDOS = _SETTINGS.absence_seconds
LIMITE_SAIDA_FRAMES = FPS * ABANDONO_SEGUNDOS
JOINHA_FRAMES_CONFIRMAR = 4
JOINHA_FRAMES_LIBERAR = 3
MAO_FRAMES_CONFIRMAR = 2
MAO_FRAMES_PERDER = 5
RESPOSTA_FRAMES_CONFIRMAR = 3
RESPOSTA_FRAMES_LIBERAR = 3
RESPOSTA_INTERVALO_SEGUNDOS = _SETTINGS.answer_release_seconds
RESPOSTA_DESTAQUE_SEGUNDOS = _SETTINGS.answer_highlight_seconds
JOINHA_RECONHECIDO_SEGUNDOS = _SETTINGS.thumbs_up_feedback_seconds
DURACAO_FEEDBACK_SEGUNDOS = _SETTINGS.feedback_seconds
DEBUG_GESTOS = os.environ.get("DEBUG_GESTOS") == "1"
DEBUG_CAMERA = os.environ.get("DEBUG_CAMERA") == "1"
DEBUG_GESTOS_INTERVALO_SEGUNDOS = 1.0

DIALOGO_TITULO = "LABECO"
DIALOGO_TTY_PATH = os.environ.get("DIALOGO_TTY", "/dev/tty1")
DIALOGO_SDL_DRIVER = os.environ.get("DIALOGO_SDL_DRIVER", "")
DIALOGO_TEMPO_PAGINA_SEGUNDOS = 4.0
ATRACAO_FPS = _SETTINGS.attraction_fps
EMBRAPA_LOGO_PATH = BASE_DIR / "embrap_logo.png"
