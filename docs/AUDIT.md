# Auditoria do estado preservado

Referência imutável: tag `pre-reorganizacao-2026-10-23`, commit `b145fae`.

## Estrutura encontrada

- Runtime público monolítico em `totem.py`, com máquina de estados, câmera,
  presença, gestos e apresentação no mesmo laço.
- Interface Pygame/KMSDRM em `dialogo.py`, `tela_pygame.py` e
  `tela_atracao.py`, com fallback em `/dev/tty1`.
- Captura ffmpeg/V4L2 e modelos MediaPipe Tasks separados em `camera.py`,
  `pessoa.py` e `gestos.py`.
- Roteiro Python com dois temas e três perguntas por tema.
- Plataforma V2 já funcional: SQLite, Event Log, métricas, bundles, IPC local,
  FastAPI Admin, publicação, ativação e rollback de conteúdo.
- Scripts anteriores de rsync por SSH e instalação manual de serviços.
- `movimento.py`, vídeos e reprodutor preservados como experimentos/legado.

## Funcionalidades existentes

Presença humana, confirmação por joinha, escolha por um/dois dedos,
questionário, feedback temporizado, abandono por ausência, atração em tela cheia,
prévia diagnóstica, persistência de sessões/eventos, métricas e painel Admin.

## Dependências identificadas

Python, ffmpeg, NumPy, MediaPipe Tasks, OpenCV (transitivo), Pygame/SDL,
FastAPI, Uvicorn e Jinja. Os modelos `.task`, imagens e vídeos pertencem à
distribuição. SQLite e caches são operacionais e não pertencem ao Git.

## Problemas de portabilidade encontrados

- Inicialização gráfica priorizava apenas KMSDRM/fbcon, sem Wayland/X11.
- Imports de MediaPipe aconteciam no caminho principal, impedindo simulação.
- Dependências nativas não estavam fixadas nem separadas por plataforma.
- Configurações estavam divididas entre constantes e variáveis de ambiente.
- Não havia simulador da experiência nem testes da máquina de estados pública.
- Instalação dependia de passos manuais e `rsync` para o Raspberry.
- Dados/serviços ainda usavam caminhos históricos `totem-labeco`.
- Não havia GitHub Actions, backup/restore ou atualização por versão estável.

## Modificações aplicadas

Máquina de estados independente, entradas intercambiáveis, simulador explícito,
configuração TOML central, dependências por plataforma, testes sem hardware, CI,
instalador/operador único `totem.sh`, diretórios persistentes, serviços systemd,
diagnóstico, atualização por tag, backup, restauração e documentação reproduzível.
