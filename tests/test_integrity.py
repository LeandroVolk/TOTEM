from pathlib import Path

from content.bundles import GerenciadorBundles


ROOT = Path(__file__).resolve().parents[1]


def test_recursos_obrigatorios_e_conteudo_sao_validos(tmp_path):
    for filename in ("pose_landmarker_lite.task", "hand_landmarker.task", "embrap_logo.png"):
        path = ROOT / filename
        assert path.is_file()
        assert path.stat().st_size > 1024
    manager = GerenciadorBundles(tmp_path / "content")
    content = manager.bootstrap_legado()
    assert manager.validar((tmp_path / "content" / "current").resolve())["content_hash"] == content.content_hash
