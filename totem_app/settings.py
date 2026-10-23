"""Configuracao central, portavel e sobreponivel por ambiente/TOML."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
import os
from pathlib import Path
import platform
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.toml"


def detected_platform() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    os_id = "linux"
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if line.startswith("ID="):
                os_id = line.partition("=")[2].strip('"')
                break
    except OSError:
        os_id = system
    return f"{os_id}-{machine}"


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    mode: str = "hardware"
    platform: str = ""
    fullscreen: bool = True
    headless: bool = False
    screen_width: int = 0
    screen_height: int = 0
    camera_device: str = "/dev/video0"
    camera_width: int = 320
    camera_height: int = 240
    camera_fps: int = 5
    pose_interval_frames: int = 2
    pose_min_confidence: float = 0.5
    hand_min_detection_confidence: float = 0.4
    hand_min_presence_confidence: float = 0.4
    hand_min_tracking_confidence: float = 0.4
    absence_seconds: float = 15.0
    inactivity_seconds: float = 90.0
    thumbs_up_confirm_seconds: float = 0.8
    answer_confirm_seconds: float = 0.6
    answer_release_seconds: float = 0.5
    answer_highlight_seconds: float = 2.0
    thumbs_up_feedback_seconds: float = 2.0
    feedback_seconds: float = 6.0
    attraction_fps: int = 12
    volume: float = 1.0
    debug_camera: bool = False
    debug_gestures: bool = False
    runtime_dir: Path = PROJECT_ROOT / "runtime"
    content_root: Path = PROJECT_ROOT / "runtime" / "content"
    database_path: Path = PROJECT_ROOT / "runtime" / "totem.sqlite3"
    control_socket: Path = PROJECT_ROOT / "runtime" / "totem-control.sock"
    admin_host: str = "127.0.0.1"
    admin_port: int = 8787
    admin_enabled: bool = True
    log_level: str = "INFO"

    @property
    def pose_model_path(self) -> Path:
        return self.project_root / "pose_landmarker_lite.task"

    @property
    def hand_model_path(self) -> Path:
        return self.project_root / "hand_landmarker.task"

    @property
    def logo_path(self) -> Path:
        return self.project_root / "embrap_logo.png"


_ENV_MAP = {
    "TOTEM_MODE": ("mode", str),
    "TOTEM_HEADLESS": ("headless", lambda value: value == "1"),
    "TOTEM_FULLSCREEN": ("fullscreen", lambda value: value != "0"),
    "TOTEM_CAMERA_DEVICE": ("camera_device", str),
    "TOTEM_RUNTIME_DIR": ("runtime_dir", Path),
    "TOTEM_CONTENT_ROOT": ("content_root", Path),
    "TOTEM_DATABASE_PATH": ("database_path", Path),
    "TOTEM_CONTROL_SOCKET": ("control_socket", Path),
    "TOTEM_ADMIN_HOST": ("admin_host", str),
    "TOTEM_ADMIN_PORT": ("admin_port", int),
    "TOTEM_LOG_LEVEL": ("log_level", str),
    "DEBUG_CAMERA": ("debug_camera", lambda value: value == "1"),
    "DEBUG_GESTOS": ("debug_gestures", lambda value: value == "1"),
}


def _flatten(data: dict) -> dict:
    aliases = {
        "execution": {"mode", "fullscreen", "headless", "volume", "log_level"},
        "screen": {"screen_width", "screen_height"},
        "camera": {"camera_device", "camera_width", "camera_height", "camera_fps", "pose_interval_frames"},
        "recognition": {
            "pose_min_confidence", "hand_min_detection_confidence",
            "hand_min_presence_confidence", "hand_min_tracking_confidence",
            "thumbs_up_confirm_seconds", "answer_confirm_seconds", "answer_release_seconds",
        },
        "timers": {
            "absence_seconds", "inactivity_seconds", "answer_highlight_seconds",
            "thumbs_up_feedback_seconds", "feedback_seconds",
        },
        "admin": {"admin_host", "admin_port", "admin_enabled"},
    }
    result = {}
    for section, allowed in aliases.items():
        for key, value in data.get(section, {}).items():
            if key in allowed:
                result[key] = value
    return result


def load_settings(config_path: str | Path | None = None, **overrides) -> Settings:
    path = Path(config_path or os.environ.get("TOTEM_CONFIG", DEFAULT_CONFIG))
    values = {}
    if path.is_file():
        with path.open("rb") as stream:
            values.update(_flatten(tomllib.load(stream)))
    for env_name, (field_name, converter) in _ENV_MAP.items():
        if env_name in os.environ:
            values[field_name] = converter(os.environ[env_name])
    values.update({key: value for key, value in overrides.items() if value is not None})
    valid = {field.name for field in fields(Settings)}
    unknown = set(values) - valid
    if unknown:
        raise ValueError(f"Configuracoes desconhecidas: {', '.join(sorted(unknown))}")
    settings = Settings(**values)
    settings = replace(settings, platform=detected_platform())
    if "TOTEM_RUNTIME_DIR" in os.environ and "TOTEM_CONTENT_ROOT" not in os.environ:
        settings = replace(settings, content_root=settings.runtime_dir / "content")
    if "TOTEM_RUNTIME_DIR" in os.environ and "TOTEM_DATABASE_PATH" not in os.environ:
        settings = replace(settings, database_path=settings.runtime_dir / "totem.sqlite3")
    if "TOTEM_RUNTIME_DIR" in os.environ and "TOTEM_CONTROL_SOCKET" not in os.environ:
        settings = replace(settings, control_socket=settings.runtime_dir / "totem-control.sock")
    if settings.mode not in {"hardware", "simulation"}:
        raise ValueError("mode deve ser 'hardware' ou 'simulation'.")
    return settings
