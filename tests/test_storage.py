from content.providers import LegacyRoteiroProvider
from storage.database import Database
from storage.repositories import RepositorioTotem


def test_sessao_eventos_e_metricas(tmp_path):
    database = Database(tmp_path / "totem.sqlite3")
    database.migrate()
    repositorio = RepositorioTotem(database)
    conteudo = LegacyRoteiroProvider().carregar()

    session_id = repositorio.criar_sessao(conteudo)
    repositorio.registrar_evento("runtime", "presence.detected")
    repositorio.registrar_evento("runtime", "interaction.started", session_id=session_id)
    repositorio.registrar_evento(
        "runtime", "question.answered", {"answer_id": "1"}, session_id
    )
    repositorio.incrementar_respostas(session_id)
    repositorio.encerrar_sessao(session_id, "completed")

    metricas = repositorio.metricas_basicas()
    assert metricas["presencas_detectadas"] == 1
    assert metricas["respostas"] == 1
    assert metricas["sessoes_concluidas"] == 1
    assert repositorio.eventos_recentes()[0]["event_type"] == "question.answered"
