"""Maquina de estados independente de camera, MediaPipe e interface grafica."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
import time
from typing import Any, Callable

from .settings import Settings


class Estado(Enum):
    ESPERA = auto()
    SAUDACAO = auto()
    CONFIRMACAO_JOINHA = auto()
    ESCOLHA_TEMA = auto()
    PERGUNTA = auto()
    FEEDBACK = auto()
    ENCERRAMENTO = auto()


class TipoEvento(Enum):
    PESSOA_ENTROU = auto()
    PESSOA_SAIU = auto()
    MOVIMENTO = auto()
    AUSENCIA_PROLONGADA = auto()
    JOINHA = auto()
    DEDOS = auto()
    TICK = auto()
    REINICIAR = auto()
    INATIVIDADE = auto()
    ENCERRAR = auto()


@dataclass(frozen=True)
class Evento:
    tipo: TipoEvento
    instante: float
    valor: Any = None


@dataclass
class Visao:
    estado: Estado
    mensagem: str = ""
    complemento: str | None = None
    titulo: str | None = None
    pergunta: str | None = None
    alternativas: dict[int, str] = field(default_factory=dict)
    selecionada: int | None = None
    status: str | None = None
    aguardando: bool = False
    confirmado: bool = False
    indicador: dict | None = None
    fase_feedback: str | None = None


class TotemEngine:
    """Processa eventos sem conhecer a origem (camera ou simulador)."""

    def __init__(
        self,
        conteudo,
        settings: Settings,
        runtime=None,
        logger: Callable[..., None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.conteudo = conteudo
        self.settings = settings
        self.runtime = runtime
        self.logger = logger or (lambda *_args, **_kwargs: None)
        self.clock = clock
        self.estado = Estado.ESPERA
        self.estado_desde = clock()
        self.interacao_desde: float | None = None
        self.ultima_atividade = self.estado_desde
        self.ausente_desde: float | None = None
        self.presente = False
        self.tema = None
        self.indice_pergunta = 0
        self.pergunta_atual = None
        self.feedback_atual = None
        self.resposta_atual: int | None = None
        self.inicio_pergunta: float | None = None
        self.gesto_ativo: tuple[str, int | None] | None = None
        self.gesto_desde: float | None = None
        self.neutro_desde = self.estado_desde
        self.aguarda_neutro = False
        self.encerrar_solicitado = False

    @property
    def sessao_ativa(self) -> bool:
        return self.estado != Estado.ESPERA

    def handle(self, evento: Evento) -> Estado:
        agora = evento.instante
        if evento.tipo == TipoEvento.ENCERRAR:
            self.encerrar_solicitado = True
            return self.estado
        if evento.tipo == TipoEvento.REINICIAR:
            self._abandonar(agora, "reinicio_simulado")
            return self.estado
        if evento.tipo in {TipoEvento.AUSENCIA_PROLONGADA, TipoEvento.INATIVIDADE}:
            if self.sessao_ativa:
                motivo = "ausencia_prolongada" if evento.tipo == TipoEvento.AUSENCIA_PROLONGADA else "inatividade"
                self._abandonar(agora, motivo)
            return self.estado
        if evento.tipo == TipoEvento.PESSOA_ENTROU:
            self.presente = True
            self.ausente_desde = None
            self.ultima_atividade = agora
            if self.estado == Estado.ESPERA:
                self._iniciar_interacao(agora)
            return self.estado
        if evento.tipo == TipoEvento.PESSOA_SAIU:
            self.presente = False
            self.ausente_desde = agora
            return self.estado
        if evento.tipo == TipoEvento.MOVIMENTO:
            self.ultima_atividade = agora
            self._log("movimento_detectado")
            return self.estado
        if evento.tipo == TipoEvento.JOINHA:
            self._atualizar_gesto("joinha" if evento.valor else None, None, agora)
            self.ultima_atividade = agora if evento.valor else self.ultima_atividade
        elif evento.tipo == TipoEvento.DEDOS:
            numero = evento.valor
            if numero is not None and (not isinstance(numero, int) or not 1 <= numero <= 5):
                raise ValueError("O numero de dedos deve estar entre 1 e 5.")
            self._atualizar_gesto("dedos" if numero is not None else None, numero, agora)
            self.ultima_atividade = agora if numero is not None else self.ultima_atividade

        self._avancar_temporizadores(agora)
        return self.estado

    def tick(self, agora: float | None = None) -> Estado:
        return self.handle(Evento(TipoEvento.TICK, self.clock() if agora is None else agora))

    def _iniciar_interacao(self, agora):
        self.interacao_desde = agora
        self._mudar_estado(Estado.SAUDACAO, agora)
        self._log("pessoa_detectada")
        self._runtime("evento", "presence.detected")
        self._log("inicio_interacao")
        self._runtime("iniciar_sessao")

    def _atualizar_gesto(self, tipo, numero, agora):
        novo = None if tipo is None else (tipo, numero)
        if novo != self.gesto_ativo:
            self.gesto_ativo = novo
            self.gesto_desde = agora if novo else None
            if novo is None:
                self.neutro_desde = agora

    def _avancar_temporizadores(self, agora):
        if self.sessao_ativa and self.ausente_desde is not None:
            if agora - self.ausente_desde >= self.settings.absence_seconds:
                self._abandonar(agora, "ausencia_prolongada")
                return
        if self.sessao_ativa and agora - self.ultima_atividade >= self.settings.inactivity_seconds:
            self._abandonar(agora, "inatividade")
            return

        if self.estado == Estado.SAUDACAO and self._gesto_confirmado(
            "joinha", None, agora, self.settings.thumbs_up_confirm_seconds
        ):
            self._log("joinha_inicial", confirmar_segundos=self.settings.thumbs_up_confirm_seconds)
            self._runtime("evento", "gesture.confirmed", {"gesture": "thumbs_up"})
            self._mudar_estado(Estado.CONFIRMACAO_JOINHA, agora)
            self._atualizar_gesto(None, None, agora)
            return

        if self.estado == Estado.CONFIRMACAO_JOINHA:
            if agora - self.estado_desde >= self.settings.thumbs_up_feedback_seconds:
                self.aguarda_neutro = True
                self._mudar_estado(Estado.ESCOLHA_TEMA, agora)
            return

        if self.estado in {Estado.ESCOLHA_TEMA, Estado.PERGUNTA}:
            if self.aguarda_neutro:
                if self.gesto_ativo is None and agora - self.neutro_desde >= self.settings.answer_release_seconds:
                    self.aguarda_neutro = False
                    self._log("resposta_liberada")
                return
            if self.gesto_ativo and self.gesto_ativo[0] == "dedos":
                numero = self.gesto_ativo[1]
                if numero in self._alternativas_atuais() and self._gesto_confirmado(
                    "dedos", numero, agora, self.settings.answer_confirm_seconds
                ):
                    self._confirmar_resposta(numero, agora)
            return

        if self.estado == Estado.FEEDBACK:
            duracao = self.settings.answer_highlight_seconds + float(self.feedback_atual["duracao"])
            if agora - self.estado_desde >= duracao:
                self.indice_pergunta += 1
                if self.indice_pergunta < len(self.tema["perguntas"]):
                    self.pergunta_atual = self.tema["perguntas"][self.indice_pergunta]
                    self.inicio_pergunta = agora
                    self.aguarda_neutro = True
                    self._mudar_estado(Estado.PERGUNTA, agora)
                    self._log("pergunta_exibida", pergunta=self.pergunta_atual["id"], tema=self.tema["id"])
                    self._runtime("pergunta_exibida", self.pergunta_atual["id"], self.tema["id"])
                else:
                    self._mudar_estado(Estado.ENCERRAMENTO, agora)
            return

        if self.estado == Estado.ENCERRAMENTO:
            if agora - self.estado_desde >= float(self.conteudo.encerramento["duracao"]):
                duracao = 0.0 if self.interacao_desde is None else agora - self.interacao_desde
                self._log("interacao_concluida", tema=self.tema["id"], duracao_segundos=round(duracao, 1))
                self._runtime("encerrar_sessao", "completed", {"duration_seconds": round(duracao, 1)})
                self._resetar(agora)

    def _confirmar_resposta(self, numero, agora):
        self._atualizar_gesto(None, None, agora)
        if self.estado == Estado.ESCOLHA_TEMA:
            tema = self.conteudo.tema_por_numero(numero)
            if tema is None:
                return
            self.tema = tema
            self.indice_pergunta = 0
            self.pergunta_atual = tema["perguntas"][0]
            self.inicio_pergunta = agora
            self.aguarda_neutro = True
            self._mudar_estado(Estado.PERGUNTA, agora)
            self._log("tema_escolhido", numero=numero, tema=tema["id"])
            self._runtime("tema_selecionado", tema["id"], numero)
            self._log("pergunta_exibida", pergunta=self.pergunta_atual["id"], tema=tema["id"])
            self._runtime("pergunta_exibida", self.pergunta_atual["id"], tema["id"])
            return

        self.resposta_atual = numero
        self.feedback_atual = self.conteudo.feedback_da_resposta(self.pergunta_atual, numero)
        tempo = 0.0 if self.inicio_pergunta is None else agora - self.inicio_pergunta
        self._log(
            "resposta_recebida", pergunta=self.pergunta_atual["id"], numero=numero,
            correta=self.feedback_atual["correta"], tempo_segundos=round(tempo, 1),
        )
        self._runtime(
            "resposta_registrada", self.pergunta_atual["id"], numero,
            tempo, self.feedback_atual["correta"],
        )
        self._mudar_estado(Estado.FEEDBACK, agora)

    def _alternativas_atuais(self):
        if self.estado == Estado.ESCOLHA_TEMA:
            return self.conteudo.escolha_tema["alternativas"]
        if self.pergunta_atual:
            return self.pergunta_atual["alternativas"]
        return {}

    def _gesto_confirmado(self, tipo, numero, agora, duracao):
        return (
            self.gesto_ativo == (tipo, numero)
            and self.gesto_desde is not None
            and agora - self.gesto_desde >= duracao
        )

    def _abandonar(self, agora, motivo):
        if not self.sessao_ativa:
            self._resetar(agora)
            return
        duracao = 0.0 if self.interacao_desde is None else agora - self.interacao_desde
        self._log("abandono_interacao", motivo=motivo, duracao_segundos=round(duracao, 1))
        self._runtime("encerrar_sessao", "abandoned", {"reason": motivo, "duration_seconds": round(duracao, 1)})
        self._resetar(agora)

    def _resetar(self, agora):
        self.estado = Estado.ESPERA
        self.estado_desde = agora
        self.interacao_desde = None
        self.ultima_atividade = agora
        self.ausente_desde = None
        self.presente = False
        self.tema = None
        self.indice_pergunta = 0
        self.pergunta_atual = None
        self.feedback_atual = None
        self.resposta_atual = None
        self.inicio_pergunta = None
        self.gesto_ativo = None
        self.gesto_desde = None
        self.neutro_desde = agora
        self.aguarda_neutro = False

    def _mudar_estado(self, estado, agora):
        self.estado = estado
        self.estado_desde = agora
        self._runtime("atualizar_estado", estado.name)

    def _runtime(self, method, *args):
        callback = getattr(self.runtime, method, None)
        if callback is not None:
            callback(*args)

    def _log(self, nome, **dados):
        self.logger(nome, **dados)

    def view(self, agora: float | None = None) -> Visao:
        agora = self.clock() if agora is None else agora
        if self.estado == Estado.ESPERA:
            return Visao(self.estado)
        if self.estado == Estado.SAUDACAO:
            return Visao(
                self.estado, mensagem=self.conteudo.saudacao["mensagem"],
                complemento=self.conteudo.saudacao["cta"], aguardando=True,
                indicador=self._indicador("joinha", None, agora, self.settings.thumbs_up_confirm_seconds),
            )
        if self.estado == Estado.CONFIRMACAO_JOINHA:
            return Visao(self.estado, mensagem="Joinha reconhecido", confirmado=True)
        if self.estado in {Estado.ESCOLHA_TEMA, Estado.PERGUNTA}:
            etapa = self.conteudo.escolha_tema if self.estado == Estado.ESCOLHA_TEMA else self.pergunta_atual
            numero = self.gesto_ativo[1] if self.gesto_ativo and self.gesto_ativo[0] == "dedos" else None
            return Visao(
                self.estado, pergunta=etapa["pergunta"], alternativas=etapa["alternativas"],
                titulo=None if self.estado == Estado.ESCOLHA_TEMA else self.tema["titulo"],
                aguardando=True,
                indicador=None if self.aguarda_neutro else self._indicador(
                    "dedos", numero, agora, self.settings.answer_confirm_seconds
                ),
            )
        if self.estado == Estado.FEEDBACK:
            destaque = agora - self.estado_desde < self.settings.answer_highlight_seconds
            if destaque:
                return Visao(
                    self.estado, pergunta=self.pergunta_atual["pergunta"],
                    alternativas=self.pergunta_atual["alternativas"], titulo=self.tema["titulo"],
                    selecionada=self.resposta_atual,
                    status="Resposta registrada. Pode baixar a mao",
                    confirmado=True, fase_feedback="destaque",
                )
            return Visao(
                self.estado, mensagem=self.feedback_atual["texto"],
                complemento=self.feedback_atual["complemento"], fase_feedback="explicacao",
            )
        return Visao(self.estado, mensagem=self.conteudo.encerramento["mensagem"])

    def _indicador(self, tipo, numero, agora, duracao):
        if self.gesto_ativo != (tipo, numero) or self.gesto_desde is None:
            return None
        progresso = max(0.0, min(1.0, (agora - self.gesto_desde) / max(duracao, 0.001)))
        return {
            "gesto": "joinha" if tipo == "joinha" else str(numero),
            "progresso": max(1, int(progresso * 3)),
            "total": 3,
        }
