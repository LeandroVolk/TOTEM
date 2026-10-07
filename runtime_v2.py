"""Servicos V2 consumidos pelo runtime, sem dependencias de Pygame ou MediaPipe."""

from __future__ import annotations

from threading import RLock
from time import monotonic

from content.bundles import GerenciadorBundles
from content.providers import LegacyRoteiroProvider
from storage.database import Database
from storage.repositories import RepositorioTotem
from v2_config import CONTENT_ROOT, DATABASE_PATH, preparar_diretorios


class RuntimeV2:
    def __init__(self, database_path=DATABASE_PATH, content_root=CONTENT_ROOT):
        preparar_diretorios()
        self.database = Database(database_path)
        self.database.migrate()
        self.repositorio = RepositorioTotem(self.database)
        self.bundles = GerenciadorBundles(content_root, LegacyRoteiroProvider())
        self.conteudo = self.bundles.bootstrap_legado()
        self.repositorio.registrar_publicacao(self.conteudo, status="active")
        self._lock = RLock()
        self._inicio = monotonic()
        self._session_id = None
        self._estado = "ESPERA"
        self._camera_ok = False
        self._mediapipe_ok = False
        self._last_event = None

    @property
    def session_id(self):
        return self._session_id

    def pronto(self, camera_ok=True, mediapipe_ok=True):
        with self._lock:
            self._camera_ok = camera_ok
            self._mediapipe_ok = mediapipe_ok
        self.evento("runtime.started", {"camera_ok": camera_ok, "mediapipe_ok": mediapipe_ok})

    def atualizar_estado(self, estado):
        with self._lock:
            self._estado = estado

    def iniciar_sessao(self):
        with self._lock:
            if self._session_id is None:
                self._session_id = self._tentar(
                    "criar sessao", self.repositorio.criar_sessao, self.conteudo
                )
            session_id = self._session_id
        self.evento("interaction.started", session_id=session_id)
        return session_id

    def encerrar_sessao(self, status, payload=None):
        with self._lock:
            session_id = self._session_id
            self._session_id = None
        if session_id is None:
            return
        self.evento(f"interaction.{status}", payload or {}, session_id=session_id)
        self._tentar("encerrar sessao", self.repositorio.encerrar_sessao, session_id, status)

    def tema_selecionado(self, theme_id, numero):
        if self._session_id:
            self._tentar("registrar tema", self.repositorio.definir_tema, self._session_id, theme_id)
        self.evento("theme.selected", {"theme_id": theme_id, "answer_id": str(numero)})

    def pergunta_exibida(self, question_id, theme_id):
        self.evento("question.shown", {"question_id": question_id, "theme_id": theme_id})

    def resposta_registrada(self, question_id, numero, tempo_segundos, correta):
        if self._session_id:
            self._tentar("registrar resposta", self.repositorio.incrementar_respostas, self._session_id)
        self.evento(
            "question.answered",
            {
                "question_id": question_id,
                "answer_id": str(numero),
                "response_time_ms": round(tempo_segundos * 1000),
                "correct": correta,
            },
        )

    def evento(self, event_type, payload=None, session_id=None):
        session_id = self._session_id if session_id is None else session_id
        self._tentar(
            "registrar evento", self.repositorio.registrar_evento,
            "runtime", event_type, payload, session_id,
        )
        with self._lock:
            self._last_event = event_type

    def recarregar_conteudo(self):
        with self._lock:
            if self._session_id is not None:
                return {"ok": False, "reason": "active_session"}
            self.conteudo = self.bundles.carregar_ativo()
            self._tentar("registrar conteudo ativo", self.repositorio.registrar_publicacao, self.conteudo, "active")
        self.evento("content.reloaded", {"bundle": self.conteudo.bundle_id, "version": self.conteudo.version})
        return {"ok": True, "content": self.descricao_conteudo()}

    def descricao_conteudo(self):
        return {
            "bundle_id": self.conteudo.bundle_id,
            "version": self.conteudo.version,
            "content_hash": self.conteudo.content_hash,
            "origin": self.conteudo.origem,
        }

    def status(self):
        with self._lock:
            return {
                "running": True,
                "state": self._estado,
                "camera_ok": self._camera_ok,
                "camera_fps": None,
                "mediapipe_ok": self._mediapipe_ok,
                "current_content_bundle": self.descricao_conteudo(),
                "current_session": self._session_id,
                "uptime_seconds": round(monotonic() - self._inicio, 1),
                "last_event": self._last_event,
            }

    @staticmethod
    def _tentar(operacao, funcao, *args):
        try:
            return funcao(*args)
        except Exception as erro:
            # Persistencia e observabilidade nunca podem tomar a camera ou o HDMI.
            print(f"[v2] nao foi possivel {operacao}: {erro}")
            return None


class RuntimeV2Nulo:
    """Mantem a V1 executavel caso uma falha de persistencia aconteca no boot."""

    def __init__(self):
        self.conteudo = LegacyRoteiroProvider().carregar()
        self._session_id = None

    @property
    def session_id(self):
        return self._session_id

    def pronto(self, **_): pass
    def atualizar_estado(self, _): pass
    def evento(self, *_args, **_kwargs): pass
    def tema_selecionado(self, *_args, **_kwargs): pass
    def pergunta_exibida(self, *_args, **_kwargs): pass
    def resposta_registrada(self, *_args, **_kwargs): pass
    def recarregar_conteudo(self): return {"ok": False, "reason": "unavailable"}
    def descricao_conteudo(self): return {"origin": "legacy"}
    def status(self): return {"running": True, "state": "unknown", "storage": "unavailable"}

    def iniciar_sessao(self):
        self._session_id = "unpersisted"
        return self._session_id

    def encerrar_sessao(self, *_args, **_kwargs):
        self._session_id = None
