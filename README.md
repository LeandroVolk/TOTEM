# TOTEM — Totem Interativo

Aplicação interativa sem toque para comunicação entre pesquisa e público. A
experiência atual usa Pygame, câmera, MediaPipe e gestos para apresentar os
temas Campo Nativo e Solo Vivo. O painel administrativo usa FastAPI e os dados
operacionais são armazenados em SQLite, sem guardar imagens ou biometria.

O fluxo oficial é:

> Desenvolvemos no Fedora. Testamos no Fedora. Versionamos no GitHub.
> Instalamos versões estáveis no Raspberry Pi.

O Raspberry Pi 5 é equipamento de produção; `rsync` por SSH não é mais o
processo de implantação.

## Início rápido no Fedora 44

```bash
git clone git@github.com:LeandroVolk/TOTEM.git
cd TOTEM
./totem.sh install
./totem.sh test
./totem.sh run --simulate
```

O instalador identifica Fedora x86_64 ou Debian ARM64, cria `.venv`, instala
dependências fixadas e preserva configurações/dados existentes. Para apenas
revalidar a `.venv` sem usar o gerenciador de pacotes do sistema:

```bash
TOTEM_SKIP_SYSTEM=1 ./totem.sh install
```

Execução real, usando webcam e MediaPipe:

```bash
./totem.sh doctor --strict-hardware
./totem.sh run
```

No desktop, a SDL seleciona Wayland/X11 automaticamente. Use `--windowed` ao
chamar `totem.py` diretamente se não quiser tela cheia.

## Simulação

O simulador só é habilitado por `--simulate` ou `TOTEM_MODE=simulation`; ele
jamais é ativado silenciosamente em produção. Câmera e simulador alimentam a
mesma máquina de estados em `totem_app/engine.py`.

```bash
./totem.sh run --simulate
```

Comandos disponíveis:

```text
enter / leave / movement / absence / inactivity / reset / quit
thumbs-up [segundos]
fingers <1..5> [segundos]
correct [segundos] / incorrect [segundos]
wait <segundos> / next / status / help
```

Há aliases em português. Para um fluxo completo e acelerado:

```bash
./.venv/bin/python totem.py --simulate --headless \
  --script examples/simulation-full.txt
```

Detalhes estão em [docs/SIMULATION.md](docs/SIMULATION.md).

## Arquitetura

```text
camera + MediaPipe ─┐
                    ├─ eventos ─ TotemEngine ─ Pygame/terminal
simulador explícito ┘               │
                                    ├─ SQLite (sessões/eventos/métricas)
                                    └─ socket local ─ FastAPI Admin
```

- `totem.py`: ponto de entrada único e seleção explícita do modo.
- `totem_app/engine.py`: estados, temporizadores e regras sem hardware.
- `totem_app/application.py`: composição de câmera/simulador, interface e runtime.
- `camera.py`, `pessoa.py`, `gestos.py`: adaptadores de hardware.
- `dialogo.py`, `tela_pygame.py`, `tela_atracao.py`: interface preservada.
- `content/`: bundles publicados e adaptador do roteiro legado.
- `storage/`: esquema SQLite, sessões, eventos e métricas.
- `admin/`: dashboard e API separados do processo gráfico.
- `config/default.toml`: parâmetros padrão versionados.
- `systemd/`: unidades de produção para kiosk e Admin.
- `tests/`: testes unitários, integração, regressão e integridade.

Veja [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e o diagnóstico inicial em
[docs/AUDIT.md](docs/AUDIT.md).

## Configuração e dados

Os padrões ficam em `config/default.toml`. Para ajustes de desenvolvimento:

```bash
cp config/default.toml config/local.toml
TOTEM_CONFIG=config/local.toml ./totem.sh run --simulate
```

`config/local.toml` é ignorado pelo Git. Variáveis `TOTEM_*` têm precedência.
Em produção, os dados são separados assim:

| Categoria | Local |
|---|---|
| Código e recursos | clone Git, somente versões/tags publicadas |
| Configuração local | `/etc/totem/` |
| SQLite e conteúdo ativo | `/var/lib/totem/` |
| Logs | journal do systemd e `/var/log/totem/` |
| Backups exportáveis | destino escolhido em `totem.sh backup` |

## Testes e CI

```bash
./totem.sh test
```

Os testes não exigem câmera, monitor ou MediaPipe ativo. Cobrem inicialização,
estados, eventos simulados, confirmação temporal, escolhas, questionário,
transições, inatividade, persistência, métricas, configuração, Admin, IPC e
integridade de conteúdo. GitHub Actions executa a mesma suíte em cada push/PR.

## Instalação limpa no Raspberry Pi 5

Requisitos-alvo: Raspberry Pi 5 ARM64, Debian 13, câmera Logitech C270 e monitor
HDMI. Em um sistema recém-instalado:

```bash
git clone --branch vX.Y.Z --depth 1 git@github.com:LeandroVolk/TOTEM.git
cd TOTEM
./totem.sh install
sudoedit /etc/totem/admin.env
./totem.sh doctor --strict-hardware
./totem.sh restart
```

`install` instala pacotes, prepara a `.venv`, cria diretórios persistentes,
instala unidades systemd, configura acesso a vídeo/áudio e habilita a
inicialização automática. Ele não inicia toda a aplicação como root e preserva
arquivos já existentes em `/etc/totem` e `/var/lib/totem`.

As unidades usam o console `/dev/tty1` e KMSDRM, reiniciam após falhas e não
dependem de SSH. O Admin só deve escutar na LAN depois que um token for definido.
Consulte [docs/DEPLOY_RPI5.md](docs/DEPLOY_RPI5.md).

## Operação

```bash
./totem.sh install
./totem.sh run
./totem.sh stop
./totem.sh restart
./totem.sh status
./totem.sh logs
./totem.sh test
./totem.sh doctor
./totem.sh update vX.Y.Z
./totem.sh backup /midia/usb/totem-backup.tar.gz
./totem.sh restore /midia/usb/totem-backup.tar.gz
```

`update` exige uma tag estável explícita, recusa código local alterado, cria um
backup antes da troca e não usa `push --force`. `restore` valida o arquivo e
cria um backup pré-restauração em produção.

## Administração web

O Admin pode ser executado localmente com:

```bash
./run_admin.sh
```

O padrão é `http://127.0.0.1:8787`. Para acesso por LAN configure
`TOTEM_ADMIN_HOST=0.0.0.0` e um `TOTEM_ADMIN_TOKEN` longo em
`/etc/totem/admin.env`. Consulte [docs/ADMIN.md](docs/ADMIN.md).

## Versionamento e recuperação

- `main` representa versões estáveis.
- Funcionalidades são desenvolvidas em branches e integradas após os testes.
- Produção usa tags `vX.Y.Z`.
- O baseline funcional antigo é `v1-functional`.
- O estado imediatamente anterior a esta reorganização é
  `pre-reorganizacao-2026-10-23`.

O código pode ser reconstruído pelo GitHub. Configurações e dados operacionais
devem ser recuperados com `totem.sh backup`/`restore`; eles nunca são enviados
automaticamente ao repositório.

## Limites de validação

O modo simulado, a interface SDL virtual, MediaPipe x86_64, Admin e testes são
validados no Fedora. Os arquivos de instalação Debian 13/ARM64 e systemd estão
preparados, mas a câmera, KMSDRM, áudio, boot automático e wheel ARM64 precisam
ser validados fisicamente no Raspberry antes de uma versão ser declarada pronta
para produção.
