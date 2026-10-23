# Produção no Raspberry Pi 5

Alvo: Raspberry Pi 5 ARM64, Debian 13, Python 3.13, Logitech C270, monitor HDMI
e execução dedicada no console `tty1`.

## Instalação limpa

Instale uma tag estável, nunca uma branch de trabalho:

```bash
git clone git@github.com:LeandroVolk/TOTEM.git
cd TOTEM
git switch --detach vX.Y.Z
./totem.sh install
```

O instalador:

1. valida Debian/ARM64;
2. instala Python, venv, ffmpeg, Pygame/SDL, V4L2 e utilitários;
3. instala dependências Python fixadas, inclusive o wheel ARM64 do MediaPipe;
4. preserva `/etc/totem` e `/var/lib/totem` em repetições;
5. instala kiosk/Admin e o helper de operação restrito;
6. habilita inicialização automática sem iniciar Python como root;
7. executa diagnóstico final.

## Configuração

Edite `/etc/totem/totem.toml` para câmera, limiares e tempos. Para habilitar o
Admin na LAN:

```bash
sudoedit /etc/totem/admin.env
```

```text
TOTEM_ADMIN_HOST=0.0.0.0
TOTEM_ADMIN_PORT=8787
TOTEM_ADMIN_TOKEN=um-token-longo-gerado-com-secrets
```

Mantenha o bind em `127.0.0.1` se o acesso remoto não for necessário.

## Validação física obrigatória

```bash
./totem.sh doctor --strict-hardware
./totem.sh restart
./totem.sh status
./totem.sh logs
```

Confirme no equipamento:

1. câmera e reconhecimento de pose/mão;
2. KMSDRM em tela cheia no HDMI;
3. áudio, quando usado pelo conteúdo;
4. fluxo público completo e abandono;
5. reinício após falha e após reboot;
6. Admin, métricas e operações na LAN;
7. funcionamento do kiosk com Admin e rede parados.

As unidades entram pelo `graphical.target`, ocupam `/dev/tty1`, usam
`SDL_VIDEODRIVER=kmsdrm` e recebem grupos suplementares `video`, `render`,
`input` e `tty`. Se a imagem Debian adotada usar uma sessão gráfica diferente,
valide e ajuste essa integração antes de publicar a versão de produção.

## Atualização

```bash
./totem.sh update vX.Y.Z
```

O comando requer tag explícita, recusa alterações no checkout, cria backup,
atualiza dependências e reinstala unidades. Nunca usa force-push.

## Backup e recuperação

Exporte para mídia fora do cartão do Raspberry:

```bash
./totem.sh backup /media/usb/totem-$(date +%F).tar.gz
```

Em uma reinstalação: instale a mesma tag com `totem.sh install`, conecte a mídia
e restaure:

```bash
./totem.sh restore /media/usb/totem-AAAA-MM-DD.tar.gz
./totem.sh doctor --strict-hardware
./totem.sh restart
```

O restore valida caminhos/manifesto e cria backup pré-restauração em produção.

## Estado da compatibilidade

- MediaPipe 1.1.1 declara Python 3.13/3.14 e publica wheels manylinux ARM64.
- Debian 13 fornece Pygame 2.6.1 ARM64; ele é usado para manter SDL/KMS nativo.
- A suíte CI e o Fedora não substituem o teste físico de wheel, câmera, KMSDRM,
  permissões, áudio e systemd no Raspberry.
