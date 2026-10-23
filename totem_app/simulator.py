"""Interpretador de eventos para desenvolvimento sem camera ou gestos reais."""

from __future__ import annotations

from dataclasses import dataclass
import shlex

from .engine import Estado, Evento, TipoEvento, TotemEngine


HELP = """Comandos do simulador:
  enter | leave | movement | absence | inactivity | reset | quit
  thumbs-up [segundos]
  fingers <1..5> [segundos]
  correct [segundos] | incorrect [segundos]
  wait <segundos> | next | status | help

Atalhos em portugues: entrar, sair, movimento, ausencia, joinha, dedos,
correta, incorreta, esperar, proximo, reiniciar, encerrar.
"""


ALIASES = {
    "entrar": "enter", "sair": "leave", "movimento": "movement",
    "ausencia": "absence", "inatividade": "inactivity", "joinha": "thumbs-up",
    "dedos": "fingers", "correta": "correct", "incorreta": "incorrect",
    "esperar": "wait", "proximo": "next", "reiniciar": "reset",
    "encerrar": "quit", "ajuda": "help", "estado": "status",
}


@dataclass
class SimulationResult:
    now: float
    output: str = ""
    quit: bool = False


class SimulationCommands:
    def __init__(self, engine: TotemEngine, now: float | None = None):
        self.engine = engine
        self.now = engine.clock() if now is None else now

    def execute(self, line: str) -> SimulationResult:
        args = shlex.split(line.strip())
        if not args or args[0].startswith("#"):
            return SimulationResult(self.now)
        command = ALIASES.get(args[0].lower(), args[0].lower())
        if command == "help":
            return SimulationResult(self.now, HELP)
        if command == "status":
            return SimulationResult(self.now, self.describe())
        if command == "quit":
            self.engine.handle(Evento(TipoEvento.ENCERRAR, self.now))
            return SimulationResult(self.now, "Simulacao encerrada.", True)
        mapping = {
            "enter": TipoEvento.PESSOA_ENTROU,
            "leave": TipoEvento.PESSOA_SAIU,
            "movement": TipoEvento.MOVIMENTO,
            "absence": TipoEvento.AUSENCIA_PROLONGADA,
            "inactivity": TipoEvento.INATIVIDADE,
            "reset": TipoEvento.REINICIAR,
        }
        if command in mapping:
            self.engine.handle(Evento(mapping[command], self.now))
            return SimulationResult(self.now, self.describe())
        if command == "wait":
            self._advance(self._required_seconds(args, 1))
            return SimulationResult(self.now, self.describe())
        if command == "next":
            self._next()
            return SimulationResult(self.now, self.describe())
        if command == "thumbs-up":
            seconds = self._optional_seconds(args, self.engine.settings.thumbs_up_confirm_seconds)
            self._hold(TipoEvento.JOINHA, True, False, seconds)
            return SimulationResult(self.now, self.describe())
        if command == "fingers":
            if len(args) < 2:
                raise ValueError("Use: fingers <1..5> [segundos]")
            number = int(args[1])
            if not 1 <= number <= 5:
                raise ValueError("O numero de dedos deve estar entre 1 e 5.")
            seconds = float(args[2]) if len(args) > 2 else self.engine.settings.answer_confirm_seconds
            self._hold(TipoEvento.DEDOS, number, None, seconds)
            return SimulationResult(self.now, self.describe())
        if command in {"correct", "incorrect"}:
            number = self._answer_number(command == "correct")
            seconds = self._optional_seconds(args, self.engine.settings.answer_confirm_seconds)
            self._hold(TipoEvento.DEDOS, number, None, seconds)
            return SimulationResult(self.now, self.describe())
        raise ValueError(f"Comando desconhecido: {command}. Digite 'help'.")

    def _hold(self, event_type, active_value, release_value, seconds):
        if seconds < 0:
            raise ValueError("A duracao nao pode ser negativa.")
        self.engine.handle(Evento(event_type, self.now, active_value))
        self._advance(seconds + 0.001)
        self.engine.handle(Evento(event_type, self.now, release_value))

    def _advance(self, seconds):
        if seconds < 0:
            raise ValueError("A duracao nao pode ser negativa.")
        self.now += seconds
        self.engine.tick(self.now)

    def _next(self):
        settings = self.engine.settings
        if self.engine.estado == Estado.CONFIRMACAO_JOINHA:
            self._advance(settings.thumbs_up_feedback_seconds + 0.001)
        elif self.engine.estado == Estado.FEEDBACK:
            duration = settings.answer_highlight_seconds + float(self.engine.feedback_atual["duracao"])
            self._advance(duration + 0.001)
        elif self.engine.estado == Estado.ENCERRAMENTO:
            self._advance(float(self.engine.conteudo.encerramento["duracao"]) + 0.001)
        elif self.engine.aguarda_neutro:
            self._advance(settings.answer_release_seconds + 0.001)
        else:
            self.engine.tick(self.now)

    def _answer_number(self, correct):
        if self.engine.estado == Estado.ESCOLHA_TEMA:
            return 1 if correct else 2
        question = self.engine.pergunta_atual
        if question is None:
            raise ValueError("Nao ha pergunta ativa.")
        expected = question["resposta_esperada"]
        if expected is None:
            return 1 if correct else 2
        if correct:
            return int(expected)
        return next(number for number in question["alternativas"] if int(number) != int(expected))

    @staticmethod
    def _required_seconds(args, index):
        if len(args) <= index:
            raise ValueError("Informe a duracao em segundos.")
        return float(args[index])

    @staticmethod
    def _optional_seconds(args, default):
        return float(args[1]) if len(args) > 1 else default

    def describe(self):
        view = self.engine.view(self.now)
        detail = view.pergunta or view.mensagem or "atracao"
        return f"estado={self.engine.estado.name} tempo={self.now:.3f} tela={detail.splitlines()[0]}"


def run_script(engine: TotemEngine, lines, start: float = 0.0, observer=None) -> list[str]:
    simulator = SimulationCommands(engine, now=start)
    outputs = []
    for number, line in enumerate(lines, 1):
        try:
            result = simulator.execute(line)
        except (ValueError, TypeError) as error:
            raise ValueError(f"Linha {number}: {error}") from error
        if result.output:
            outputs.append(result.output)
        if observer is not None:
            observer(result.now)
        if result.quit:
            break
    return outputs
