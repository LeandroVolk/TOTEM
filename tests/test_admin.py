from fastapi.testclient import TestClient

from admin.app import ServicosAdmin, create_app
from content.bundles import GerenciadorBundles


class ControllerFake:
    def __init__(self):
        self.actions = []

    def status(self):
        return "active"

    def executar(self, action):
        self.actions.append(action)
        return {"ok": True, "action": action}


def test_endpoints_admin_com_token(tmp_path):
    controller = ControllerFake()
    servicos = ServicosAdmin(
        tmp_path / "totem.sqlite3",
        tmp_path / "content",
        tmp_path / "missing.sock",
        controller,
    )
    servicos.bundles.bootstrap_legado()
    app = create_app(servicos, token="token-de-teste")
    client = TestClient(app)

    assert client.get("/api/status").status_code == 401
    headers = {"X-Admin-Token": "token-de-teste"}
    assert client.get("/api/status", headers=headers).json()["service"] == "active"
    assert client.post("/api/kiosk/restart", headers=headers).status_code == 200
    assert controller.actions == ["restart"]
    assert client.get("/api/content/bundles", headers=headers).status_code == 200

    draft = client.post("/api/content/drafts", headers=headers).json()["draft"]
    assert client.post(f"/api/content/drafts/{draft}/validate", headers=headers).status_code == 200
    assert client.get(f"/api/content/drafts/{draft}/preview", headers=headers).status_code == 200
    publish = client.post(
        f"/api/content/drafts/{draft}/publish", params={"version": "0.2.0"}, headers=headers
    )
    assert publish.status_code == 200
    assert client.post(
        "/api/content/bundles/labeco-pampa-0.2.0/activate", headers=headers
    ).status_code == 200
