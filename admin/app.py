"""Admin local: status, metricas e operacao controlada do kiosk."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from content.bundles import BundleInvalido, GerenciadorBundles
from ipc.control import request as ipc_request
from operations import ControleServico
from storage.database import Database
from storage.repositories import RepositorioTotem
from v2_config import ADMIN_TOKEN, CONTENT_ROOT, CONTROL_SOCKET_PATH, DATABASE_PATH


BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "admin" / "templates"))


class ServicosAdmin:
    def __init__(self, database_path=DATABASE_PATH, content_root=CONTENT_ROOT, socket_path=CONTROL_SOCKET_PATH, controller=None):
        database = Database(database_path)
        database.migrate()
        self.repositorio = RepositorioTotem(database)
        self.bundles = GerenciadorBundles(content_root)
        self.socket_path = Path(socket_path)
        self.controller = controller or ControleServico()

    def status_runtime(self):
        try:
            return ipc_request(self.socket_path, "status")["status"]
        except (OSError, KeyError, TimeoutError):
            return {
                "running": False,
                "state": "unavailable",
                "camera_ok": "unknown",
                "mediapipe_ok": "unknown",
                "current_content_bundle": None,
                "current_session": None,
                "uptime_seconds": None,
                "last_event": None,
            }

    def recarregar_conteudo(self):
        try:
            return ipc_request(self.socket_path, "reload_content")
        except (OSError, TimeoutError):
            return {"ok": False, "reason": "runtime_unavailable"}


def create_app(servicos=None, token=ADMIN_TOKEN):
    app = FastAPI(title="Totem LABECO Admin", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "admin" / "static")), name="static")
    servicos = servicos or ServicosAdmin()

    def autorizado(x_admin_token: Annotated[str | None, Header()] = None):
        if token and x_admin_token != token:
            raise HTTPException(status_code=401, detail="Token administrativo invalido.")

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request):
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {"auth_configured": bool(token)},
        )

    @app.get("/logo")
    def logo():
        return FileResponse(BASE_DIR / "embrap_logo.png")

    @app.get("/api/status", dependencies=[Depends(autorizado)])
    def status():
        return {"runtime": servicos.status_runtime(), "service": servicos.controller.status()}

    @app.get("/api/metrics", dependencies=[Depends(autorizado)])
    def metrics():
        return servicos.repositorio.metricas_basicas()

    @app.get("/api/events", dependencies=[Depends(autorizado)])
    def events():
        return servicos.repositorio.eventos_recentes()

    @app.post("/api/kiosk/{action}", dependencies=[Depends(autorizado)])
    def kiosk_action(action: str):
        try:
            resultado = servicos.controller.executar(action)
        except (ValueError, RuntimeError) as erro:
            raise HTTPException(status_code=409, detail=str(erro)) from erro
        servicos.repositorio.registrar_evento("admin", f"kiosk.{action}ed")
        return resultado

    @app.get("/api/content/bundles", dependencies=[Depends(autorizado)])
    def bundles():
        return servicos.bundles.listar()

    @app.post("/api/content/drafts", dependencies=[Depends(autorizado)])
    def create_draft():
        draft = servicos.bundles.criar_draft()
        servicos.repositorio.registrar_evento("admin", "content.draft_created", {"draft": draft.name})
        return {"draft": draft.name}

    @app.post("/api/content/drafts/{draft}/validate", dependencies=[Depends(autorizado)])
    def validate_draft(draft: str):
        try:
            resultado = servicos.bundles.validar(_draft_path(servicos, draft))
        except BundleInvalido as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from erro
        servicos.repositorio.registrar_evento("admin", "content.validated", {"draft": draft})
        return resultado

    @app.post("/api/content/drafts/{draft}/publish", dependencies=[Depends(autorizado)])
    def publish_draft(draft: str, version: str):
        try:
            bundle = servicos.bundles.publicar(_draft_path(servicos, draft), version)
        except BundleInvalido as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from erro
        servicos.repositorio.registrar_publicacao(bundle, status="published")
        servicos.repositorio.registrar_evento(
            "admin", "content.published", {"bundle": bundle.bundle_id, "version": bundle.version}
        )
        return {"bundle_id": bundle.bundle_id, "version": bundle.version, "content_hash": bundle.content_hash}

    @app.post("/api/content/bundles/{bundle_name}/activate", dependencies=[Depends(autorizado)])
    def activate_bundle(bundle_name: str):
        try:
            bundle = servicos.bundles.ativar(_bundle_name(bundle_name))
        except BundleInvalido as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from erro
        servicos.repositorio.registrar_publicacao(bundle, status="active")
        reload_result = servicos.recarregar_conteudo()
        servicos.repositorio.registrar_evento(
            "admin", "content.activated", {"bundle": bundle_name, "reload": reload_result}
        )
        return {"content": bundle.bundle_id, "reload": reload_result}

    @app.post("/api/content/bundles/{bundle_name}/rollback", dependencies=[Depends(autorizado)])
    def rollback_bundle(bundle_name: str):
        resposta = activate_bundle(bundle_name)
        servicos.repositorio.registrar_evento("admin", "content.rollback", {"bundle": bundle_name})
        return resposta

    return app


def _draft_path(servicos, draft):
    if Path(draft).name != draft or not draft.startswith("draft-"):
        raise HTTPException(status_code=404, detail="Draft nao encontrado.")
    caminho = servicos.bundles.staging_dir / draft
    if not caminho.is_dir():
        raise HTTPException(status_code=404, detail="Draft nao encontrado.")
    return caminho


def _bundle_name(bundle_name):
    if Path(bundle_name).name != bundle_name:
        raise HTTPException(status_code=404, detail="Bundle nao encontrado.")
    return bundle_name


app = create_app()
