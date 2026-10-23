from dataclasses import replace

from content.providers import LegacyRoteiroProvider
from totem_app.engine import Estado, Evento, TipoEvento, TotemEngine
from totem_app.settings import Settings


class RuntimeFake:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def callback(*args):
            self.calls.append((name, args))
        return callback


def engine():
    settings = replace(
        Settings(),
        thumbs_up_confirm_seconds=0.8,
        thumbs_up_feedback_seconds=0.2,
        answer_confirm_seconds=0.6,
        answer_release_seconds=0.1,
        answer_highlight_seconds=0.2,
        inactivity_seconds=20,
        absence_seconds=2,
    )
    runtime = RuntimeFake()
    return TotemEngine(LegacyRoteiroProvider().carregar(), settings, runtime, clock=lambda: 0), runtime


def test_confirmacao_temporal_do_joinha():
    app, _ = engine()
    app.handle(Evento(TipoEvento.PESSOA_ENTROU, 0))
    app.handle(Evento(TipoEvento.JOINHA, 0.1, True))
    app.tick(0.89)
    assert app.estado == Estado.SAUDACAO
    app.tick(0.91)
    assert app.estado == Estado.CONFIRMACAO_JOINHA


def test_fluxo_de_tema_resposta_e_feedback():
    app, runtime = engine()
    app.handle(Evento(TipoEvento.PESSOA_ENTROU, 0))
    app.handle(Evento(TipoEvento.JOINHA, 0, True))
    app.tick(0.801)
    app.handle(Evento(TipoEvento.JOINHA, 0.801, False))
    app.tick(1.01)
    assert app.estado == Estado.ESCOLHA_TEMA
    app.tick(1.12)
    app.handle(Evento(TipoEvento.DEDOS, 1.2, 1))
    app.tick(1.81)
    assert app.estado == Estado.PERGUNTA
    assert app.tema["id"] == "campo_nativo"
    app.tick(1.92)
    app.handle(Evento(TipoEvento.DEDOS, 2.0, 2))
    app.tick(2.61)
    assert app.estado == Estado.FEEDBACK
    assert app.feedback_atual["correta"] is None
    assert any(name == "resposta_registrada" for name, _ in runtime.calls)


def test_saida_e_ausencia_prolongada_abandonam_sessao():
    app, runtime = engine()
    app.handle(Evento(TipoEvento.PESSOA_ENTROU, 0))
    app.handle(Evento(TipoEvento.PESSOA_SAIU, 1))
    app.tick(2.9)
    assert app.estado == Estado.SAUDACAO
    app.tick(3.01)
    assert app.estado == Estado.ESPERA
    assert any(call == ("encerrar_sessao", ("abandoned", {"reason": "ausencia_prolongada", "duration_seconds": 3.0})) for call in runtime.calls)


def test_cinco_dedos_e_aceito_como_evento_mas_nao_como_opcao_atual():
    app, _ = engine()
    app.handle(Evento(TipoEvento.PESSOA_ENTROU, 0))
    app.handle(Evento(TipoEvento.DEDOS, 0.1, 5))
    assert app.estado == Estado.SAUDACAO
