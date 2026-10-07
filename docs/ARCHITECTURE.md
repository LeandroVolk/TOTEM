# Arquitetura V2

O Totem possui ciclos de vida independentes:

```text
HARDWARE: Raspberry Pi, camera, HDMI/KMSDRM
SOFTWARE: runtime Python, MediaPipe, Pygame
CONTEUDO: bundles versionados, ativos por symlink
```

`totem.py` continua dono exclusivo de camera, MediaPipe e Pygame. `runtime_v2.py` acrescenta persistência e conteúdo sem importar módulos gráficos. Se a inicialização V2 falhar, `RuntimeV2Nulo` mantém o roteiro legado disponível.

O Admin é outro processo. Ele consulta status e solicita reload por `AF_UNIX`, no socket configurado por `TOTEM_CONTROL_SOCKET`. O protocolo é JSON delimitado por linha e aceita somente `status` e `reload_content`. Não existe porta HTTP no kiosk.

O Admin pede operações de serviço por `/usr/local/sbin/totem-kiosk-control`, instalado como root mas limitado a `start`, `stop` e `restart` de `totem-kiosk.service`. O processo FastAPI continua como `labeco` e não recebe acesso root genérico.
