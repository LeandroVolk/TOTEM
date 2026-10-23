"""Adaptadores de apresentacao para a mesma maquina de estados."""

from __future__ import annotations

from .engine import Estado


class HeadlessPresenter:
    def __init__(self):
        self.last = None

    def render(self, engine, now=None, **_):
        view = engine.view(now)
        key = (view.estado, view.pergunta, view.mensagem, view.fase_feedback)
        if key != self.last:
            print(f"[simulacao] estado={view.estado.name}")
            self.last = key

    def close(self):
        pass


class PygamePresenter:
    def __init__(self):
        from dialogo import DialogoPygame
        from tela_atracao import TelaAtracao
        from tela_pygame import TelaPygame

        self.screen = TelaPygame()
        self.dialog = DialogoPygame(self.screen)
        self.attraction = TelaAtracao(self.screen)
        self.was_waiting = True

    def render(self, engine, now=None, debug_camera=None):
        view = engine.view(now)
        if view.estado == Estado.ESPERA:
            if not self.was_waiting:
                self.dialog.fechar()
                self.attraction.reiniciar()
            self.was_waiting = True
            self.attraction.mostrar()
            return
        if self.was_waiting:
            self.attraction.ocultar()
        self.was_waiting = False
        if view.pergunta is not None:
            self.dialog.mostrar_pergunta(
                view.pergunta, view.alternativas, aguardando=view.aguardando,
                selecionada=view.selecionada, titulo=view.titulo,
                indicador=view.indicador, status=view.status,
                confirmado=view.confirmado, debug_camera=debug_camera,
            )
        else:
            self.dialog.mostrar(
                view.mensagem, aguardando=view.aguardando,
                complemento=view.complemento, indicador=view.indicador,
                confirmado=view.confirmado, debug_camera=debug_camera,
            )

    def close(self):
        self.dialog.fechar()
        self.screen.fechar()
