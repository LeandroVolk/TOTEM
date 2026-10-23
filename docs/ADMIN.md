# Administração local

O Admin do TOTEM é FastAPI/Jinja/CSS simples. Ele não importa `totem.py`, Pygame, câmera ou MediaPipe. O dashboard consulta o socket local; se o Runtime estiver parado, mostra `unavailable` em vez de inventar dados.

O bind é configurável por `TOTEM_ADMIN_HOST` e a porta por `TOTEM_ADMIN_PORT`. O padrão é `127.0.0.1`. Para LAN, configure explicitamente `0.0.0.0` em `/etc/totem/admin.env` e forneça `TOTEM_ADMIN_TOKEN`; a API aceita esse token no cabeçalho `X-Admin-Token`.

Sem token, o serviço não deve ser apresentado como seguro para rede hostil. Não há terminal web, upload de código ou comando arbitrário. O painel só oferece ações fixas do kiosk e registra auditoria no stream `admin`.
