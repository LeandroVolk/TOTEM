from dataclasses import replace

from content.providers import LegacyRoteiroProvider
from totem_app.engine import Estado, TotemEngine
from totem_app.settings import Settings
from totem_app.simulator import SimulationCommands, run_script


def make_simulator():
    settings = replace(
        Settings(),
        thumbs_up_confirm_seconds=0.1,
        thumbs_up_feedback_seconds=0.1,
        answer_confirm_seconds=0.1,
        answer_release_seconds=0.1,
        answer_highlight_seconds=0.1,
        inactivity_seconds=100,
    )
    engine = TotemEngine(LegacyRoteiroProvider().carregar(), settings, clock=lambda: 0)
    return engine, SimulationCommands(engine, now=0)


def test_comandos_percorrem_a_mesma_maquina_de_estados():
    engine, simulator = make_simulator()
    simulator.execute("enter")
    simulator.execute("thumbs-up")
    simulator.execute("next")
    simulator.execute("next")
    simulator.execute("fingers 2")
    assert engine.estado == Estado.PERGUNTA
    simulator.execute("next")
    simulator.execute("correct")
    assert engine.estado == Estado.FEEDBACK


def test_script_simula_inatividade_reinicio_e_um_a_cinco_dedos():
    engine, _ = make_simulator()
    outputs = run_script(
        engine,
        ["enter", "movement", "fingers 1", "fingers 2", "fingers 3", "fingers 4", "fingers 5", "inactivity", "status", "quit"],
    )
    assert engine.estado == Estado.ESPERA
    assert "estado=ESPERA" in outputs[-2]
    assert engine.encerrar_solicitado


def test_duracao_insuficiente_nao_confirma():
    engine, simulator = make_simulator()
    simulator.execute("enter")
    simulator.execute("thumbs-up 0.01")
    assert engine.estado == Estado.SAUDACAO
