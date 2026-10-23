from pathlib import Path

from totem_app.settings import load_settings


def test_configuracao_toml_e_ambiente(tmp_path, monkeypatch):
    config = tmp_path / "totem.toml"
    config.write_text(
        "[execution]\nmode='simulation'\nfullscreen=false\n"
        "[camera]\ncamera_device='/dev/video9'\ncamera_fps=7\n"
        "[timers]\ninactivity_seconds=12.5\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TOTEM_RUNTIME_DIR", str(tmp_path / "state"))
    settings = load_settings(config)
    assert settings.mode == "simulation"
    assert settings.camera_device == "/dev/video9"
    assert settings.camera_fps == 7
    assert settings.inactivity_seconds == 12.5
    assert settings.database_path == tmp_path / "state" / "totem.sqlite3"


def test_configuracao_padrao_nao_tem_caminho_de_usuario():
    settings = load_settings()
    assert "/home/" not in str(settings.camera_device)
    assert settings.pose_model_path.is_absolute()
