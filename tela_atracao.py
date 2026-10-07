"""Cena de espera minimalista baseada na marca da Embrapa."""

from time import monotonic

from config import ATRACAO_FPS, EMBRAPA_LOGO_PATH


class TelaAtracao:
    COR_FUNDO = (0, 0, 0)

    def __init__(self, tela):
        self.tela = tela
        self.ativo = True
        self.ultimo_desenho = 0.0
        self.inicio = monotonic()
        self.tamanho_preparado = None
        self.logo = None
        self.contorno_verde = []

    def mostrar(self):
        if not self.ativo or not self.tela.abrir():
            return

        agora = monotonic()
        if agora - self.ultimo_desenho < 1 / ATRACAO_FPS:
            return
        self.ultimo_desenho = agora
        self.tela.processar_eventos()
        self._desenhar(agora - self.inicio)

    def ocultar(self):
        self.ativo = False

    def reiniciar(self):
        self.ativo = True
        self.inicio = monotonic()
        self.ultimo_desenho = 0.0

    def _desenhar(self, tempo):
        pygame = self.tela.pygame
        superficie = self.tela.superficie
        tamanho_tela = superficie.get_size()
        if tamanho_tela != self.tamanho_preparado:
            self._preparar_logo(pygame, tamanho_tela)

        superficie.fill(self.COR_FUNDO)
        if self.logo is None:
            pygame.display.flip()
            return

        retangulo = self.logo.get_rect(center=(tamanho_tela[0] // 2, tamanho_tela[1] // 2))
        self._desenhar_brilho_contorno(pygame, superficie, retangulo, tempo)
        superficie.blit(self.logo, retangulo)
        pygame.display.flip()

    def _preparar_logo(self, pygame, tamanho_tela):
        self.tamanho_preparado = tamanho_tela
        try:
            original = pygame.image.load(str(EMBRAPA_LOGO_PATH)).convert_alpha()
        except pygame.error as erro:
            print(f"[atracao] nao foi possivel carregar {EMBRAPA_LOGO_PATH}: {erro}")
            return

        limite = original.get_bounding_rect()
        original = original.subsurface(limite).copy()
        escala = min(
            tamanho_tela[0] * 0.68 / original.get_width(),
            tamanho_tela[1] * 0.46 / original.get_height(),
        )
        tamanho_logo = (
            max(1, int(original.get_width() * escala)),
            max(1, int(original.get_height() * escala)),
        )
        self.logo = pygame.transform.smoothscale(original, tamanho_logo)
        mascara = self._mascara_verde(pygame, self.logo)
        self.contorno_verde = mascara.outline(every=2)

    @staticmethod
    def _mascara_verde(pygame, imagem):
        largura, altura = imagem.get_size()
        mascara = pygame.mask.Mask((largura, altura))
        for y in range(altura):
            for x in range(largura):
                vermelho, verde, azul, alfa = imagem.get_at((x, y))
                if alfa and verde > 70 and verde > vermelho * 1.25 and verde > azul * 1.2:
                    mascara.set_at((x, y))
        return mascara

    def _desenhar_brilho_contorno(self, pygame, superficie, retangulo, tempo):
        if len(self.contorno_verde) < 2:
            return
        destaque = pygame.Surface(self.logo.get_size(), pygame.SRCALPHA)
        tamanho_trilha = max(18, len(self.contorno_verde) // 16)
        inicio = int(tempo * 92) % len(self.contorno_verde)
        trilha = (self.contorno_verde * 2)[inicio : inicio + tamanho_trilha]
        meio = max(2, len(trilha) * 2 // 3)
        ponta = trilha[meio:]
        pygame.draw.lines(destaque, (31, 175, 106, 170), False, trilha, width=4)
        pygame.draw.lines(destaque, (74, 255, 168, 80), False, ponta, width=10)
        pygame.draw.lines(destaque, (208, 255, 228, 255), False, ponta, width=6)
        superficie.blit(destaque, retangulo)
