"""Repositorios: fatos cronologicos primeiro, metricas derivadas depois."""

from __future__ import annotations

from datetime import datetime
import json
from uuid import uuid4

from storage.database import Database


def agora_iso():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


class RepositorioTotem:
    def __init__(self, database: Database):
        self.database = database

    def criar_sessao(self, conteudo):
        session_id = str(uuid4())
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO sessions(
                    session_id, started_at, status, content_bundle_id,
                    content_bundle_version, content_bundle_hash
                ) VALUES (?, ?, 'started', ?, ?, ?)""",
                (
                    session_id,
                    agora_iso(),
                    conteudo.bundle_id,
                    conteudo.version,
                    conteudo.content_hash,
                ),
            )
        return session_id

    def encerrar_sessao(self, session_id, status):
        if status not in {"completed", "abandoned"}:
            raise ValueError("Status final de sessao invalido.")
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE sessions SET ended_at = ?, status = ? WHERE session_id = ?",
                (agora_iso(), status, session_id),
            )

    def definir_tema(self, session_id, theme_id):
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE sessions SET theme_id = ? WHERE session_id = ?",
                (theme_id, session_id),
            )

    def incrementar_respostas(self, session_id):
        with self.database.connect() as connection:
            connection.execute(
                """UPDATE sessions
                   SET questions_answered = questions_answered + 1
                   WHERE session_id = ?""",
                (session_id,),
            )

    def registrar_evento(self, stream, event_type, payload=None, session_id=None):
        if stream not in {"runtime", "admin"}:
            raise ValueError("Stream de evento invalido.")
        with self.database.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO events(stream, session_id, timestamp, event_type, payload_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    stream,
                    session_id,
                    agora_iso(),
                    event_type,
                    json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
                ),
            )
        return cursor.lastrowid

    def registrar_publicacao(self, bundle, status="published"):
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE content_publications SET status = 'superseded' WHERE status = 'active'"
            )
            connection.execute(
                """INSERT INTO content_publications(
                    bundle_id, bundle_version, content_hash, status, created_at, activated_at
                ) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(bundle_id, bundle_version)
                DO UPDATE SET content_hash = excluded.content_hash, status = excluded.status,
                              activated_at = excluded.activated_at""",
                (
                    bundle.bundle_id,
                    bundle.version,
                    bundle.content_hash,
                    status,
                    agora_iso(),
                    agora_iso() if status == "active" else None,
                ),
            )

    def metricas_basicas(self):
        with self.database.connect() as connection:
            valores = {}
            for nome, tipo in {
                "presencas_detectadas": "presence.detected",
                "interacoes_iniciadas": "interaction.started",
                "joinhas_confirmados": "gesture.confirmed",
                "temas_escolhidos": "theme.selected",
                "perguntas_exibidas": "question.shown",
                "respostas": "question.answered",
            }.items():
                valores[nome] = connection.execute(
                    "SELECT COUNT(*) FROM events WHERE stream = 'runtime' AND event_type = ?",
                    (tipo,),
                ).fetchone()[0]
            valores["sessoes_concluidas"] = connection.execute(
                "SELECT COUNT(*) FROM sessions WHERE status = 'completed'"
            ).fetchone()[0]
            valores["sessoes_abandonadas"] = connection.execute(
                "SELECT COUNT(*) FROM sessions WHERE status = 'abandoned'"
            ).fetchone()[0]
            duracao = connection.execute(
                """SELECT AVG((julianday(ended_at) - julianday(started_at)) * 86400.0)
                   FROM sessions WHERE ended_at IS NOT NULL"""
            ).fetchone()[0]
            valores["duracao_media_segundos"] = round(duracao or 0, 1)
            iniciadas = valores["interacoes_iniciadas"]
            valores["taxa_engajamento"] = round(
                valores["joinhas_confirmados"] / iniciadas, 3
            ) if iniciadas else 0
            finalizadas = valores["sessoes_concluidas"] + valores["sessoes_abandonadas"]
            valores["taxa_conclusao"] = round(
                valores["sessoes_concluidas"] / finalizadas, 3
            ) if finalizadas else 0
            return valores

    def eventos_recentes(self, limite=30):
        with self.database.connect() as connection:
            linhas = connection.execute(
                """SELECT event_id, stream, session_id, timestamp, event_type, payload_json
                   FROM events ORDER BY event_id DESC LIMIT ?""",
                (limite,),
            ).fetchall()
        return [
            {
                **dict(linha),
                "payload": json.loads(linha["payload_json"]),
            }
            for linha in linhas
        ]
