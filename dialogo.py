import fcntl
import shutil
import struct
import sys
import termios
import textwrap
import time
import unicodedata
from math import sin

from config import (
    DIALOGO_TEMPO_PAGINA_SEGUNDOS,
    DIALOGO_TITULO,
    DIALOGO_TTY_PATH,
    EMBRAPA_LOGO_PATH,
)
from tela_pygame import TelaPygame


class DialogoPygame:
    """Interface grafica fullscreen com fallback para o console Linux."""

    COR_FUNDO = (0, 0, 0)
    COR_TEXTO = (232, 243, 236)
    COR_DESTAQUE = (61, 215, 140)
    COR_CARTAO = (10, 21, 16)
    COR_BORDA = (39, 93, 67)
    COR_COMPLEMENTO = (152, 184, 163)
    CONEXOES_MAO = (
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (0, 9), (9, 10), (10, 11), (11, 12),
        (0, 13), (13, 14), (14, 15), (15, 16),
        (0, 17), (17, 18), (18, 19), (19, 20),
        (5, 9), (9, 13), (13, 17),
    )

    def __init__(
        self,
        tela_pygame=None,
        titulo=DIALOGO_TITULO,
        tty_path=DIALOGO_TTY_PATH,
    ):
        self.titulo = titulo
        self.tty_path = tty_path
        self.tela_pygame = tela_pygame or TelaPygame(titulo)
        self.pygame = None
        self.tela = None
        self.fallback = None
        self.ativo = False
        self.ultima_cena = None
        self.ultimo_quadro = None
        self.logo = None
        self.logo_tamanho_preparado = None

    def abrir(self):
        if self.ativo:
            return

        if self.tela_pygame.abrir():
            self.pygame = self.tela_pygame.pygame
            self.tela = self.tela_pygame.superficie
            self.ativo = True
        else:
            print(f"[dialogo] interface grafica indisponivel: {self.tela_pygame.erro}")
            print("[dialogo] usando interface de emergencia no console.")
            self.fallback = DialogoTerminal(self.titulo, self.tty_path)
            self.fallback.abrir()
            self.ativo = True

    def fechar(self):
        if not self.ativo:
            return

        if self.fallback is not None:
            self.fallback.fechar()
        self.pygame = None
        self.tela = None
        self.fallback = None
        self.ativo = False
        self.ultima_cena = None
        self.ultimo_quadro = None

    def mostrar(
        self,
        mensagem,
        aguardando=True,
        complemento=None,
        indicador=None,
        confirmado=False,
        debug_camera=None,
    ):
        if not self.ativo:
            self.abrir()

        if self.fallback is not None:
            partes = [mensagem]
            if complemento:
                partes.append(complemento)
            if indicador:
                partes.append(f"Gesto detectado: {indicador['gesto']}")
            if confirmado:
                partes.append("[OK]")
            texto = "\n\n".join(partes)
            self.fallback.mostrar(texto, aguardando)
            return

        self._atualizar_cena(
            (
                "mensagem",
                mensagem,
                complemento,
                self._chave_indicador(indicador),
                confirmado,
                self._chave_debug_camera(debug_camera),
                aguardando,
            ),
            aguardando,
            lambda agora: self._desenhar_mensagem(
                mensagem,
                complemento,
                indicador,
                confirmado,
                debug_camera,
                aguardando,
                agora,
            ),
        )

    def mostrar_pergunta(
        self,
        pergunta,
        alternativas,
        aguardando=True,
        selecionada=None,
        titulo=None,
        indicador=None,
        status=None,
        confirmado=False,
        debug_camera=None,
    ):
        if not self.ativo:
            self.abrir()

        if self.fallback is not None:
            texto = "\n\n".join(
                [
                    titulo or "",
                    pergunta,
                    f"1 - {alternativas[1]}",
                    f"2 - {alternativas[2]}",
                    f"{status} [OK]" if status and confirmado else status or "",
                ]
            )
            self.fallback.mostrar(texto, aguardando)
            return

        chave = (
            "pergunta",
            pergunta,
            tuple(sorted(alternativas.items())),
            aguardando,
            selecionada,
            titulo,
            self._chave_indicador(indicador),
            status,
            confirmado,
            self._chave_debug_camera(debug_camera),
        )
        self._atualizar_cena(
            chave,
            aguardando,
            lambda agora: self._desenhar_pergunta(
                pergunta,
                alternativas,
                aguardando,
                selecionada,
                titulo,
                indicador,
                status,
                confirmado,
                debug_camera,
                agora,
            ),
        )

    @staticmethod
    def _chave_indicador(indicador):
        if indicador is None:
            return None
        return (
            indicador["gesto"],
            indicador["progresso"],
            indicador["total"],
        )

    @staticmethod
    def _chave_debug_camera(debug_camera):
        if debug_camera is None:
            return None
        return (
            debug_camera["mao_detectada"],
            debug_camera["candidato"],
            debug_camera["progresso"],
            debug_camera["total"],
        )

    def _atualizar_cena(self, cena, animada, desenhar):
        self.tela_pygame.processar_eventos()
        quadro = int(time.monotonic() * 12) if animada else None
        if cena == self.ultima_cena and quadro == self.ultimo_quadro:
            return

        self.ultima_cena = cena
        self.ultimo_quadro = quadro
        desenhar(time.monotonic())

    def _desenhar_mensagem(
        self,
        mensagem,
        complemento,
        indicador,
        confirmado,
        debug_camera,
        aguardando,
        agora,
    ):
        pygame = self.pygame
        largura, altura = self.tela.get_size()

        self.tela.fill(self.COR_FUNDO)
        self._desenhar_logo(pygame, largura, altura)

        corpo = pygame.Rect(
            int(largura * 0.12),
            int(altura * 0.30),
            int(largura * 0.76),
            int(altura * (0.31 if complemento else 0.40)),
        )
        retangulos_texto = self._desenhar_texto_central(mensagem, corpo, self.COR_TEXTO)
        if confirmado and len(retangulos_texto) == 1:
            retangulo = retangulos_texto[0]
            self._desenhar_selo_confirmacao(
                pygame,
                (retangulo.right + max(18, int(altura * 0.024)), retangulo.centery),
            )

        if complemento:
            area_complemento = pygame.Rect(
                int(largura * 0.16),
                int(altura * 0.64),
                int(largura * 0.68),
                int(altura * 0.10),
            )
            self._desenhar_texto_central(
                complemento,
                area_complemento,
                self.COR_COMPLEMENTO,
                tamanho_maximo=max(20, int(altura * 0.035)),
                tamanho_minimo=max(17, int(altura * 0.025)),
            )

        if indicador:
            self._desenhar_indicador_gesto(
                pygame,
                largura,
                altura,
                indicador,
                y=int(altura * 0.79),
            )
        if aguardando:
            self._desenhar_prompt(
                pygame,
                largura,
                altura,
                agora,
                y=int(altura * (0.90 if complemento else 0.82)),
            )
        if debug_camera:
            self._desenhar_preview_camera(pygame, debug_camera)
        pygame.display.flip()

    def _desenhar_pergunta(
        self,
        pergunta,
        alternativas,
        aguardando,
        selecionada,
        titulo,
        indicador,
        status,
        confirmado,
        debug_camera,
        agora,
    ):
        pygame = self.pygame
        largura, altura = self.tela.get_size()
        self.tela.fill(self.COR_FUNDO)
        self._desenhar_logo(pygame, largura, altura)

        if titulo:
            fonte_titulo = self._fonte(max(23, int(altura * 0.038)))
            superficie_titulo = fonte_titulo.render(titulo.upper(), True, self.COR_DESTAQUE)
            self.tela.blit(
                superficie_titulo,
                superficie_titulo.get_rect(center=(largura // 2, int(altura * 0.24))),
            )

        area_pergunta = pygame.Rect(
            int(largura * 0.11),
            int(altura * (0.27 if titulo else 0.24)),
            int(largura * 0.78),
            int(altura * 0.20),
        )
        self._desenhar_texto_central(pergunta, area_pergunta, self.COR_TEXTO)

        margem = int(largura * 0.09)
        espacamento = int(largura * 0.04)
        largura_cartao = (largura - margem * 2 - espacamento) // 2
        altura_cartao = int(altura * 0.25)
        y_cartao = int(altura * 0.53)
        for numero in (1, 2):
            cartao = pygame.Rect(
                margem + (numero - 1) * (largura_cartao + espacamento),
                y_cartao,
                largura_cartao,
                altura_cartao,
            )
            self._desenhar_cartao(
                pygame,
                cartao,
                numero,
                alternativas[numero],
                aguardando,
                numero == selecionada,
                agora,
            )

        if status:
            self._desenhar_status(pygame, largura, altura, status, confirmado)
        elif indicador:
            self._desenhar_indicador_gesto(
                pygame,
                largura,
                altura,
                indicador,
                y=int(altura * 0.84),
            )
        if aguardando and not status:
            self._desenhar_prompt(pygame, largura, altura, agora, y=int(altura * 0.92))
        if debug_camera:
            self._desenhar_preview_camera(pygame, debug_camera)
        pygame.display.flip()

    def _desenhar_preview_camera(self, pygame, dados):
        frame = dados["frame"]
        try:
            altura_camera, largura_camera = frame.shape[:2]
        except (AttributeError, IndexError, TypeError):
            return
        if largura_camera <= 0 or altura_camera <= 0:
            return

        largura_tela, altura_tela = self.tela.get_size()
        margem = max(14, int(min(largura_tela, altura_tela) * 0.025))
        largura_preview = max(
            160,
            min(int(largura_tela * 0.23), int(altura_tela * 0.28 * 4 / 3)),
        )
        altura_preview = max(1, int(largura_preview * altura_camera / largura_camera))
        retangulo = pygame.Rect(
            largura_tela - largura_preview - margem,
            margem,
            largura_preview,
            altura_preview,
        )

        try:
            imagem = pygame.image.frombuffer(
                frame.tobytes(),
                (largura_camera, altura_camera),
                "RGB",
            )
            imagem = pygame.transform.flip(imagem, True, False)
            imagem = pygame.transform.smoothscale(imagem, retangulo.size)
        except (pygame.error, ValueError):
            return

        self.tela.blit(imagem, retangulo)
        pygame.draw.rect(self.tela, self.COR_DESTAQUE, retangulo, width=2, border_radius=4)

        pontos = dados["landmarks"]
        if pontos:
            coordenadas = [
                (
                    retangulo.x + int((1 - x) * retangulo.width),
                    retangulo.y + int(y * retangulo.height),
                )
                for x, y in pontos
            ]
            for inicio, fim in self.CONEXOES_MAO:
                if inicio < len(coordenadas) and fim < len(coordenadas):
                    pygame.draw.line(
                        self.tela,
                        self.COR_DESTAQUE,
                        coordenadas[inicio],
                        coordenadas[fim],
                        width=2,
                    )
            for ponto in coordenadas:
                pygame.draw.circle(self.tela, self.COR_TEXTO, ponto, 3)
                pygame.draw.circle(self.tela, self.COR_DESTAQUE, ponto, 3, width=1)

        fonte = self._fonte(max(16, int(altura_tela * 0.024)))
        if dados["mao_detectada"]:
            rotulo = (
                f"MAO: {dados['candidato'].upper()}  "
                f"{dados['progresso']}/{dados['total']}"
            )
        else:
            rotulo = "MAO: AUSENTE"
        superficie = fonte.render(rotulo, True, self.COR_TEXTO)
        faixa = pygame.Rect(retangulo.x, retangulo.bottom - superficie.get_height() - 6, retangulo.width, superficie.get_height() + 6)
        pygame.draw.rect(self.tela, self.COR_FUNDO, faixa)
        self.tela.blit(superficie, superficie.get_rect(center=faixa.center))

    def _desenhar_indicador_gesto(self, pygame, largura, altura, indicador, y):
        fonte = self._fonte(max(20, int(altura * 0.032)))
        gesto = indicador["gesto"]
        rotulo = "JOINHA DETECTADO" if gesto == "joinha" else f"GESTO {gesto} DETECTADO"
        texto = fonte.render(rotulo, True, self.COR_COMPLEMENTO)
        espacamento = max(12, int(altura * 0.018))
        raio = max(7, int(altura * 0.012))
        largura_circulos = raio * 6 + espacamento * 2
        inicio_x = (largura - texto.get_width() - espacamento - largura_circulos) // 2
        self.tela.blit(texto, texto.get_rect(midleft=(inicio_x, y)))

        preenchidos = min(3, indicador["progresso"])
        centro_x = inicio_x + texto.get_width() + espacamento + raio
        for indice in range(3):
            cor = self.COR_DESTAQUE if indice < preenchidos else self.COR_BORDA
            pygame.draw.circle(self.tela, cor, (centro_x + indice * (raio * 2 + espacamento), y), raio)
            pygame.draw.circle(
                self.tela,
                self.COR_TEXTO,
                (centro_x + indice * (raio * 2 + espacamento), y),
                raio,
                width=1,
            )

    def _desenhar_status(self, pygame, largura, altura, status, confirmado):
        fonte = self._fonte(max(22, int(altura * 0.034)))
        texto = fonte.render(status, True, self.COR_DESTAQUE)
        espacamento = max(14, int(altura * 0.020)) if confirmado else 0
        raio = max(9, int(altura * 0.016)) if confirmado else 0
        largura_total = texto.get_width() + espacamento + raio * 2
        inicio_x = (largura - largura_total) // 2
        self.tela.blit(texto, texto.get_rect(midleft=(inicio_x, int(altura * 0.88))))
        if confirmado:
            self._desenhar_selo_confirmacao(
                pygame,
                (inicio_x + texto.get_width() + espacamento + raio, int(altura * 0.88)),
                raio,
            )

    def _desenhar_selo_confirmacao(self, pygame, centro, raio=None):
        raio = raio or max(10, int(self.tela.get_height() * 0.018))
        pygame.draw.circle(self.tela, self.COR_DESTAQUE, centro, raio, width=2)
        x, y = centro
        pontos = [
            (x - int(raio * 0.48), y),
            (x - int(raio * 0.12), y + int(raio * 0.38)),
            (x + int(raio * 0.55), y - int(raio * 0.42)),
        ]
        pygame.draw.lines(self.tela, self.COR_DESTAQUE, False, pontos, width=max(2, raio // 4))

    def _desenhar_cartao(self, pygame, cartao, numero, alternativa, aguardando, selecionado, agora):
        pulso = (sin(agora * 2.0) + 1) / 2
        if selecionado:
            fundo = (24, 105, 69)
            borda = self.COR_DESTAQUE
            cor_texto = (0, 0, 0)
            espessura = 4
        else:
            fundo = self.COR_CARTAO
            borda = self.COR_DESTAQUE if aguardando else self.COR_BORDA
            cor_texto = self.COR_TEXTO
            espessura = 2 + int(pulso) if aguardando else 2

        pygame.draw.rect(self.tela, fundo, cartao, border_radius=8)
        pygame.draw.rect(self.tela, borda, cartao, width=espessura, border_radius=8)

        fonte_numero = self._fonte(max(46, int(cartao.height * 0.38)))
        numero_surface = fonte_numero.render(str(numero), True, borda if not selecionado else cor_texto)
        numero_rect = numero_surface.get_rect(center=(cartao.centerx, cartao.y + int(cartao.height * 0.24)))
        self.tela.blit(numero_surface, numero_rect)

        area_alternativa = pygame.Rect(
            cartao.x + int(cartao.width * 0.10),
            cartao.y + int(cartao.height * 0.40),
            int(cartao.width * 0.80),
            int(cartao.height * 0.32),
        )
        self._desenhar_texto_central(
            alternativa,
            area_alternativa,
            cor_texto,
            tamanho_maximo=max(19, int(cartao.height * 0.18)),
            tamanho_minimo=max(16, int(cartao.height * 0.12)),
        )

        instrucao = f"MOSTRE {numero} DEDO" + ("S" if numero == 2 else "")
        fonte_instrucao = self._fonte(max(16, int(cartao.height * 0.105)))
        texto_instrucao = fonte_instrucao.render(instrucao, True, borda if not selecionado else cor_texto)
        self.tela.blit(
            texto_instrucao,
            texto_instrucao.get_rect(center=(cartao.centerx, cartao.bottom - int(cartao.height * 0.12))),
        )

    def _desenhar_texto_central(
        self,
        mensagem,
        area,
        cor,
        tamanho_maximo=None,
        tamanho_minimo=None,
    ):
        if tamanho_maximo is None:
            tamanho_maximo = max(34, int(area.height * 0.18))
        if tamanho_minimo is None:
            tamanho_minimo = max(24, int(area.height * 0.07))
        fonte, linhas = self._texto_que_cabe(
            mensagem,
            area,
            tamanho_maximo=tamanho_maximo,
            tamanho_minimo=tamanho_minimo,
        )
        altura_linha = fonte.get_linesize()
        altura_total = self._altura_linhas(linhas, altura_linha)
        y = area.y + (area.height - altura_total) // 2
        retangulos = []
        for linha in linhas:
            if linha is None:
                y += int(altura_linha * 0.55)
                continue
            superficie = fonte.render(linha, True, cor)
            retangulo = superficie.get_rect(centerx=area.centerx, y=y)
            self.tela.blit(superficie, retangulo)
            retangulos.append(retangulo)
            y += altura_linha
        return retangulos

    def _texto_que_cabe(self, mensagem, area, tamanho_maximo=None, tamanho_minimo=None):
        tamanho_maximo = tamanho_maximo or max(34, int(area.height * 0.18))
        tamanho_minimo = tamanho_minimo or max(24, int(area.height * 0.07))
        for tamanho in range(tamanho_maximo, tamanho_minimo - 1, -2):
            fonte = self._fonte(tamanho)
            linhas = self._quebrar_texto(mensagem, fonte, area.width)
            if self._altura_linhas(linhas, fonte.get_linesize()) <= area.height:
                return fonte, linhas
        fonte = self._fonte(tamanho_minimo)
        return fonte, self._quebrar_texto(mensagem, fonte, area.width)

    def _desenhar_logo(self, pygame, largura, altura):
        tamanho_tela = (largura, altura)
        if tamanho_tela != self.logo_tamanho_preparado:
            self._preparar_logo(pygame, tamanho_tela)
        if self.logo is None:
            return

        retangulo = self.logo.get_rect(center=(largura // 2, int(altura * 0.14)))
        self.tela.blit(self.logo, retangulo)

    def _preparar_logo(self, pygame, tamanho_tela):
        self.logo_tamanho_preparado = tamanho_tela
        self.logo = None
        try:
            original = pygame.image.load(str(EMBRAPA_LOGO_PATH)).convert_alpha()
        except pygame.error as erro:
            print(f"[dialogo] nao foi possivel carregar {EMBRAPA_LOGO_PATH}: {erro}")
            return

        limite = original.get_bounding_rect()
        if limite.width <= 0 or limite.height <= 0:
            return
        original = original.subsurface(limite).copy()
        escala = min(
            tamanho_tela[0] * 0.34 / original.get_width(),
            tamanho_tela[1] * 0.17 / original.get_height(),
        )
        tamanho_logo = (
            max(1, int(original.get_width() * escala)),
            max(1, int(original.get_height() * escala)),
        )
        self.logo = pygame.transform.smoothscale(original, tamanho_logo)

    def _desenhar_prompt(self, pygame, largura, altura, agora, y=None):
        fonte = self._fonte(max(30, int(altura * 0.055)))
        prompt = fonte.render(">", True, self.COR_DESTAQUE)
        centro_y = y if y is not None else int(altura * 0.82)
        prompt_rect = prompt.get_rect(midright=(largura // 2 - 10, centro_y))
        self.tela.blit(prompt, prompt_rect)

        if int(agora * 2) % 2 == 0:
            cursor = pygame.Rect(
                prompt_rect.right + 12,
                prompt_rect.y + max(3, prompt_rect.height // 8),
                max(12, int(altura * 0.018)),
                max(22, int(altura * 0.039)),
            )
            pygame.draw.rect(self.tela, self.COR_DESTAQUE, cursor)

    @staticmethod
    def _altura_linhas(linhas, altura_linha):
        return sum(
            int(altura_linha * 0.55) if linha is None else altura_linha
            for linha in linhas
        )

    @staticmethod
    def _quebrar_texto(mensagem, fonte, largura):
        linhas = []
        for paragrafo in mensagem.replace("👋", "").replace("👍", "").split("\n\n"):
            palavras = paragrafo.replace("\n", " ").split()
            if not palavras:
                continue
            linha = palavras.pop(0)
            for palavra in palavras:
                candidata = f"{linha} {palavra}"
                if fonte.size(candidata)[0] <= largura:
                    linha = candidata
                else:
                    linhas.append(linha)
                    linha = palavra
            linhas.append(linha)
            linhas.append(None)
        return linhas[:-1] or [""]

    def _fonte(self, tamanho):
        return self.pygame.font.Font(None, tamanho)


FONTE_GRANDE = {
    "A": (".#.", "#.#", "###", "#.#", "#.#"),
    "B": ("##.", "#.#", "##.", "#.#", "##."),
    "C": (".##", "#..", "#..", "#..", ".##"),
    "D": ("##.", "#.#", "#.#", "#.#", "##."),
    "E": ("###", "#..", "##.", "#..", "###"),
    "F": ("###", "#..", "##.", "#..", "#.."),
    "G": (".##", "#..", "#.##", "#.#", ".##"),
    "H": ("#.#", "#.#", "###", "#.#", "#.#"),
    "I": ("###", ".#.", ".#.", ".#.", "###"),
    "J": ("..#", "..#", "..#", "#.#", ".#."),
    "K": ("#.#", "#.#", "##.", "#.#", "#.#"),
    "L": ("#..", "#..", "#..", "#..", "###"),
    "M": ("#.#", "###", "###", "#.#", "#.#"),
    "N": ("#.#", "###", "###", "###", "#.#"),
    "O": (".#.", "#.#", "#.#", "#.#", ".#."),
    "P": ("##.", "#.#", "##.", "#..", "#.."),
    "Q": (".#.", "#.#", "#.#", ".##", "..#"),
    "R": ("##.", "#.#", "##.", "#.#", "#.#"),
    "S": (".##", "#..", ".#.", "..#", "##."),
    "T": ("###", ".#.", ".#.", ".#.", ".#."),
    "U": ("#.#", "#.#", "#.#", "#.#", ".#."),
    "V": ("#.#", "#.#", "#.#", ".#.", ".#."),
    "W": ("#.#", "#.#", "###", "###", "#.#"),
    "X": ("#.#", "#.#", ".#.", "#.#", "#.#"),
    "Y": ("#.#", "#.#", ".#.", ".#.", ".#."),
    "Z": ("###", "..#", ".#.", "#..", "###"),
    "!": (".#.", ".#.", ".#.", "...", ".#."),
    "?": ("##.", "..#", ".#.", "...", ".#."),
    ".": ("...", "...", "...", "...", ".#."),
    ",": ("...", "...", "...", ".#.", "#.."),
    "-": ("...", "...", "###", "...", "..."),
    " ": ("...", "...", "...", "...", "..."),
}


class DialogoTerminal:
    def __init__(self, titulo=DIALOGO_TITULO, tty_path=DIALOGO_TTY_PATH):
        self.titulo = titulo
        self.tty_path = tty_path
        self.saida = None
        self.ativo = False
        self.ultima_mensagem = None
        self.ultimo_blink = None
        self.ultima_pagina = None
        self.inicio_mensagem = None
        self.ultimo_log_fallback = None
        self.usando_console = False

    def abrir(self):
        if self.ativo:
            return

        self.saida = self._abrir_saida()
        self.ativo = True
        self.ultima_mensagem = None
        self.ultimo_blink = None
        self.ultima_pagina = None
        self.inicio_mensagem = None
        if self.saida is not None:
            self._write("\033[?25l")

    def fechar(self):
        if not self.ativo:
            return

        if self.saida is not None:
            self._write("\033[2J\033[H\033[?25h")
            if self.usando_console:
                self.saida.close()

        self.ativo = False
        self.ultima_mensagem = None
        self.ultimo_blink = None
        self.ultima_pagina = None
        self.inicio_mensagem = None
        self.ultimo_log_fallback = None
        self.saida = None
        self.usando_console = False

    def mostrar(self, mensagem, aguardando=True):
        if not self.ativo:
            self.abrir()

        blink_ligado = int(time.monotonic() * 2) % 2 == 0 if aguardando else False
        if self.saida is None:
            if mensagem != self.ultimo_log_fallback:
                print(f"[DIALOGO] {mensagem.replace(chr(10), ' | ')}")
                self.ultimo_log_fallback = mensagem
            return

        largura, altura = self._tamanho_terminal()
        paginas = self._paginas_grandes(mensagem, largura, altura)
        agora = time.monotonic()
        if mensagem != self.ultima_mensagem:
            self.inicio_mensagem = agora
        pagina = int(
            (agora - self.inicio_mensagem) / DIALOGO_TEMPO_PAGINA_SEGUNDOS
        ) % len(paginas)
        if (
            mensagem == self.ultima_mensagem
            and blink_ligado == self.ultimo_blink
            and pagina == self.ultima_pagina
        ):
            return

        self.ultima_mensagem = mensagem
        self.ultimo_blink = blink_ligado
        self.ultima_pagina = pagina
        cursor = "█" if blink_ligado else " "
        bloco = self._montar_bloco(paginas[pagina], cursor, pagina, len(paginas))
        topo = max(1, (altura - len(bloco)) // 2)

        self._write("\033[2J\033[H")
        self._write("\n" * topo)
        for linha in bloco:
            self._write(self._centralizar(linha, largura) + "\n")

    def _abrir_saida(self):
        if self.tty_path:
            try:
                saida = open(self.tty_path, "w", encoding="utf-8", errors="replace", buffering=1)
                self.usando_console = True
                print(f"[dialogo] exibindo interface em {self.tty_path}")
                return saida
            except OSError as erro:
                print(f"[dialogo] nao foi possivel abrir {self.tty_path}: {erro}")
                print("[dialogo] sem tela fullscreen; apenas logs serao exibidos nesta sessao.")
                return None

        if sys.stdout.isatty():
            self.usando_console = False
            return sys.stdout

        return None

    def _write(self, texto):
        self.saida.write(texto)
        self.saida.flush()

    def _tamanho_terminal(self):
        if self.saida is not None:
            try:
                linhas, colunas, _, _ = struct.unpack(
                    "HHHH",
                    fcntl.ioctl(self.saida.fileno(), termios.TIOCGWINSZ, b"\0" * 8),
                )
                if colunas and linhas:
                    return colunas, linhas
            except OSError:
                pass

        tamanho = shutil.get_terminal_size((80, 24))
        return tamanho.columns, tamanho.lines

    def _montar_bloco(self, linhas, cursor, pagina, total_paginas):
        return [
            self.titulo,
            "",
            *linhas,
            "",
            f"{cursor} {pagina + 1}/{total_paginas}" if total_paginas > 1 else cursor,
            "",
        ]

    def _paginas_grandes(self, mensagem, largura, altura):
        limite = max(6, (largura + 1) // 4)
        texto = unicodedata.normalize("NFD", mensagem).encode("ascii", "ignore").decode()
        linhas_texto = [
            linha.upper()
            for linha in textwrap.wrap(texto.replace("\n", " "), width=limite)
        ]
        if not linhas_texto:
            linhas_texto = [""]
        linhas_por_pagina = max(1, (altura - 5) // 6)
        paginas = []
        for inicio in range(0, len(linhas_texto), linhas_por_pagina):
            paginas.append(self._renderizar_linhas_grandes(linhas_texto[inicio : inicio + linhas_por_pagina]))
        return paginas

    @staticmethod
    def _renderizar_linhas_grandes(linhas):
        bloco = []
        for numero, linha in enumerate(linhas):
            if numero:
                bloco.append("")
            bloco.extend(
                " ".join(FONTE_GRANDE.get(caractere, FONTE_GRANDE[" "])[indice] for caractere in linha)
                for indice in range(5)
            )
        return bloco

    @staticmethod
    def _centralizar(texto, largura):
        espacos = max(0, (largura - len(texto)) // 2)
        return " " * espacos + texto
