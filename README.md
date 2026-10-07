# Totem interativo LABECO

Protótipo local para um totem sem toque e sem voz em Raspberry Pi 5. A experiência atual é **Campo Nativo: arte e ciência do manejo**:

`pessoa detectada -> joinha -> escolha do tema -> 3 perguntas -> feedbacks -> encerramento -> atracao`.

## Arquitetura V2

O baseline funcional da V1 está marcado pela tag Git `v1-functional`. O desenvolvimento da plataforma ocorre na branch `v2-admin-architecture`; a V1 continua sendo o fallback de conteúdo e o mesmo fluxo público de câmera, MediaPipe, Pygame e KMSDRM permanece proprietário do hardware.

```text
camera + HDMI
     |
totem.py (runtime publico) ---- Unix socket ---- admin FastAPI
     |                                                    |
SQLite: sessoes, eventos, metricas                 dashboard e operacao
     |
content/current -> content/bundles/<versao>         draft -> validate -> preview
                                                     -> publish -> activate/rollback
```

- O Runtime funciona sem o Admin ou rede; ele carrega conteúdo ativo uma vez e mantém a experiência.
- O Admin não importa Pygame, não abre a câmera e só conversa com o Runtime pelo socket Unix local.
- SQLite guarda fatos cronológicos e sessões, nunca imagens ou vídeo. Métricas são calculadas a partir desses fatos.
- O primeiro bundle `labeco-pampa 0.1.0` é criado a partir de `roteiro.py`. Se um bundle falhar, o adaptador legado preserva o roteiro V1.
- O modelo editorial aceita de 1 a 5 alternativas, mas a ativação V2 atual bloqueia conteúdo diferente de `1` e `2`: os gestos e cartões públicos ainda têm essa capacidade física.

As decisões e operações V2 estão detalhadas em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/CONTENT.md](docs/CONTENT.md), [docs/EVENTS.md](docs/EVENTS.md), [docs/ADMIN.md](docs/ADMIN.md) e [docs/DEPLOY_RPI5.md](docs/DEPLOY_RPI5.md).

## Estrutura

```text
totem/
├── totem.py                  # Orquestrador principal e máquina de estados
├── pessoa.py                 # Detecção de presença humana com PoseLandmarker
├── gestos.py                 # Joinha e classificacao de 1/2 dedos com HandLandmarker
├── roteiro.py                # Conteudo configuravel dos temas, perguntas e feedbacks
├── dialogo.py                # Interface grafica fullscreen em Pygame
├── tela_pygame.py             # Sessao KMSDRM compartilhada entre as cenas
├── tela_atracao.py            # Cena procedural de atracao rural
├── reprodutor_video.py        # Utilitario legado, preservado e fora do fluxo atual
├── camera.py                 # Captura de frames via ffmpeg
├── config.py                 # Parâmetros configuráveis
├── run_totem.sh              # Execução usando o Python da .venv
├── deploy.sh                 # Sincronização com o Raspberry via rsync
├── liberar_console.sh        # Libera permissão temporária para /dev/tty1
├── movimento.py              # Teste anterior de movimento, preservado
├── pose_landmarker_lite.task # Modelo de pose já validado
├── hand_landmarker.task      # Modelo de mão usado nesta etapa
├── bemvindo.mp4               # Vídeo da etapa anterior, não usado neste fluxo
└── Arte_e_Ciencia-port1.mp4   # Vídeo de referência, excluído do deploy
```

## O que foi reaproveitado

- A captura por `ffmpeg` em `/dev/video0`, agora isolada em `camera.py`.
- A detecção de pessoa por MediaPipe Tasks em `pessoa.py`.
- Os parâmetros usados no fluxo atual: `320x240`, `5 FPS` e confiança mínima `0.5`.
- `movimento.py`, os vídeos e `reprodutor_video.py` continuam no projeto para referência/testes anteriores, mas não são chamados pelo totem.

## Uso de recursos

O Raspberry opera com uma fonte abaixo dos `5 A` recomendados e um cartao de `8 GB`. Por isso o fluxo atual usa captura em `320x240` a `5 FPS`, nao grava imagens nem videos no disco e exclui caches e ambiente virtual do deploy. Durante a experiencia, a pose e verificada a cada dois frames; a mao continua sendo acompanhada em todos os frames pelo mesmo HandLandmarker. A cena de atracao atualiza a `12 FPS` a partir de um buffer de ultimo frame, sem aumentar a taxa da camera ou a carga do MediaPipe.

## Decisao de interface

`dialogo.py` usa Pygame em tela cheia, com fonte TTF antialiasada, fundo preto, marca da Embrapa, cursor piscando e cartões de alternativa. Os cartões mostram somente `1` e `2`, com as instruções `MOSTRE 1 DEDO` e `MOSTRE 2 DEDOS`; não dependem de emoji. Durante um gesto válido, a tela mostra o gesto detectado e três círculos de progresso. O cartão escolhido recebe um destaque breve e o aviso para baixar a mão antes do feedback.

Para calibração, `DEBUG_CAMERA=1` adiciona uma prévia pequena e espelhada da câmera no canto superior direito. Ela desenha somente na tela os 21 landmarks da mão, o gesto candidato e seu progresso; nenhum frame é salvo em disco.

No estado `ESPERA`, `tela_atracao.py` mostra a marca da Embrapa centralizada sobre fundo preto. Um brilho curto percorre o contorno da forma verde sem alterar a legibilidade do logo. Ao detectar uma pessoa, o dialogo assume a mesma superficie grafica. Ao encerrar ou abandonar a interacao, a cena de atracao retorna automaticamente.

No Raspberry Pi OS Lite, a interface tenta abrir diretamente o display HDMI por `kmsdrm` e, se necessario, por `fbcon`; nenhum desktop e iniciado. Assim, mesmo executando o processo por SSH, os logs ficam no terminal remoto e a tela de interacao aparece no monitor ligado ao Raspberry.

O conteúdo fica em `roteiro.py`, e a máquina de estados em `totem.py` usa apenas os estados gerais `ESPERA`, `SAUDACAO`, `ESCOLHA_TEMA`, `PERGUNTA`, `FEEDBACK` e `ENCERRAMENTO`. Não há reprodução de vídeo nesta experiência.

Para forcar um driver de video durante um teste:

```bash
DIALOGO_SDL_DRIVER=fbcon ./run_totem.sh
```

Se Pygame ou o framebuffer nao puderem abrir, o sistema volta automaticamente para a interface de emergencia em `/dev/tty1`. Nesse caso, a permissao temporaria de console continua sendo liberada com:

```bash
cd ~/totem
./liberar_console.sh
```

Essa liberacao e temporaria e pode precisar ser refeita apos reiniciar o Raspberry ou trocar de console.

## Dependências

No Raspberry Pi:

```bash
sudo apt update
sudo apt install -y --no-install-recommends ffmpeg python3-venv python3-pygame
```

No ambiente virtual já criado:

```bash
source .venv/bin/activate
pip install --no-cache-dir mediapipe numpy
```

Os modelos esperados são:

- `pose_landmarker_lite.task`
- `hand_landmarker.task`

Se precisar baixar novamente o modelo de mão:

```bash
curl -L -o hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
```

## Como executar

Conecte a Logitech C270 em `/dev/video0`, abra um terminal no Raspberry Pi OS Lite e execute:

```bash
cd /home/leandrovolk/dev/totem
source .venv/bin/activate
python totem.py
```

No Raspberry implantado em `~/totem`, o comando recomendado é:

```bash
cd ~/totem
./run_totem.sh
```

Rodando por SSH, os eventos continuam aparecendo no SSH e a interface grafica aparece no monitor HDMI do Raspberry.

Se preferir rodar manualmente:

```bash
cd ~/totem
source .venv/bin/activate
python totem.py
```

Eventos importantes aparecem no terminal:

- `pessoa_detectada`
- `inicio_interacao`
- `joinha_inicial`
- `tema_escolhido`
- `pergunta_exibida`
- `resposta_recebida`
- `interacao_concluida`
- `abandono_interacao`

Para sair, use `Ctrl+C`.

## Como implantar no Raspberry

Use `deploy.sh` para sincronizar este diretório local com o Raspberry Pi via `rsync`.

Por padrão, o script usa:

- `PI_USER=labeco`
- `PI_HOST=raspberrypi`
- `PI_PATH=/home/labeco/totem`
- `SSH_PORT=22`

Isso corresponde ao destino SSH `labeco@raspberrypi:~/totem`.

Primeiro rode em modo simulação:

```bash
./deploy.sh
```

Para copiar de verdade:

```bash
./deploy.sh --apply
```

Para um Raspberry com usuário, IP ou caminho diferente:

```bash
PI_HOST=10.163.4.35 ./deploy.sh --apply
```

O script exclui virtualenvs (`.venv/`, `.venv-kms/` e semelhantes), `__pycache__/`, `.git/` e caches locais. O ambiente virtual e as dependências Python devem existir no Raspberry.

Na V2, `runtime/`, `logs/` e `tmp/` também são excluídos do deploy: o estado mutável fica fora do checkout quando executado pelo systemd, em `/var/lib/totem-labeco`.

Quando houver um `python3-pygame` instalado pelo sistema, a interface grafica o prioriza apenas para Pygame/SDL. MediaPipe e NumPy continuam sendo carregados da `.venv` do projeto. Isso permite usar o backend KMSDRM do sistema sem duplicar o ambiente virtual.

## Diagnostico de video

Antes de trocar dependencias graficas, rode no Raspberry:

```bash
cd ~/totem
./.venv/bin/python diagnosticar_video.py
```

O utilitario nao inicializa uma tela e nao modifica o sistema. Ele mostra a origem e versao de Pygame/SDL, drivers SDL disponiveis, variaveis `SDL_*`, dispositivos em `/dev/dri` e `/dev/fb`, modulos DRM e permissoes do usuario atual.

Se a interface grafica nao aparecer no HDMI, o log indicara o driver que falhou. No Raspberry validado, use `kmsdrm`:

```bash
cd ~/totem
DIALOGO_SDL_DRIVER=kmsdrm ./run_totem.sh
```

Se a aplicacao cair no console de emergencia e houver erro de permissao para `/dev/tty1`, rode:

```bash
cd ~/totem
./liberar_console.sh
```

## Como testar esta etapa

1. Execute `./run_totem.sh` no Raspberry.
2. Entre no campo da câmera e confirme a saudação.
3. Faça um joinha para abrir a escolha de tema.
4. Mostre um dedo para `Campo Nativo` ou dois dedos para `Solo Vivo`.
5. Em cada pergunta, confirme que os três círculos acompanham o gesto `1` ou `2`, então confirme o destaque breve do cartão e o aviso para baixar a mão antes do feedback.
6. Retire ou neutralize a mão antes da pergunta seguinte.
7. Cada explicação permanece por cerca de seis segundos. Ao fim da terceira, confirme a mensagem de encerramento por cerca de oito segundos e o retorno à atração.
8. Afaste-se durante uma etapa para confirmar o evento `abandono_interacao`.

Para ver somente o diagnóstico de gestos no terminal:

```bash
DEBUG_GESTOS=1 ./run_totem.sh
```

O log inclui mão detectada, dedos estendidos, gesto candidato, frames estáveis, frames neutros e a confirmação da resposta.

Para abrir também a prévia visual da câmera no HDMI:

```bash
DEBUG_CAMERA=1 ./run_totem.sh
```

## Testes auxiliares

Para testar o fluxo anterior de presença humana com reprodução de `bemvindo.mp4`:

```bash
python pessoa.py
```

Para rodar o teste antigo de movimento:

```bash
python movimento.py
```

## Ajustes úteis

Parâmetros de câmera, confiança, caminhos de modelos e quantidade de frames para confirmar saída/joinha ficam em `config.py`. Nesta etapa, `ABANDONO_SEGUNDOS=15` segura a interação por cerca de 15 segundos sem pose detectada, evitando abandono falso por oscilação da câmera/modelo.

Se o reconhecimento de gestos ficar sensível demais ou lento demais no Raspberry, os primeiros ajustes recomendados são:

- `JOINHA_FRAMES_CONFIRMAR`
- `RESPOSTA_FRAMES_CONFIRMAR`
- `RESPOSTA_FRAMES_LIBERAR`
- `RESPOSTA_INTERVALO_SEGUNDOS`
- `MAO_FRAMES_CONFIRMAR`
- `MAO_FRAMES_PERDER`
- `HAND_MIN_DETECTION_CONFIDENCE`
- `HAND_MIN_PRESENCE_CONFIDENCE`
- `FPS`

## V2: testes locais

Os testes V2 não usam câmera, HDMI ou MediaPipe físico:

```bash
pytest -q
```

Eles cobrem SQLite, sessões, Event Log, métricas, bundles, ativação/rollback, IPC e endpoints FastAPI. A instalação e os comandos de operação do Raspberry estão em [docs/DEPLOY_RPI5.md](docs/DEPLOY_RPI5.md).
