# Implantação no Raspberry Pi 5

## Dependências V2

No Raspberry, depois de sincronizar o projeto, instale as dependências administrativas no mesmo ambiente virtual que já contém MediaPipe:

```bash
cd ~/totem
source .venv/bin/activate
pip install --no-cache-dir -r requirements-v2.txt
chmod +x run_admin.sh install_v2_services.sh totem_ctl.py
```

## Serviços

O diagnóstico anterior confirmou que `labeco` pertence aos grupos `video`, `render` e `input`; as unidades systemd mantêm esses grupos suplementares para preservar acesso a KMSDRM e `/dev/video0`.

```bash
cd ~/totem
./install_v2_services.sh
sudoedit /etc/totem-labeco/admin.env
```

Defina ao menos:

```text
TOTEM_ADMIN_HOST=0.0.0.0
TOTEM_ADMIN_PORT=8787
TOTEM_ADMIN_TOKEN=cole-um-token-longo-gerado-com-secrets.token_urlsafe
```

Depois inicie e acompanhe:

```bash
sudo systemctl start totem-kiosk.service totem-admin.service
sudo systemctl status totem-kiosk.service totem-admin.service
sudo journalctl -u totem-kiosk.service -u totem-admin.service -f
```

Operação por SSH:

```bash
cd ~/totem
./totem_ctl.py status
./totem_ctl.py restart
./totem_ctl.py reload-content
./totem_ctl.py logs-kiosk
./totem_ctl.py camera-check
```

O Admin estará em `http://IP_DO_RASPBERRY:8787`. Para parar/iniciar o kiosk use `totem-ctl.py stop` e `totem-ctl.py start`; o Admin continua independente.

## Validação

1. Faça o fluxo público completo no HDMI.
2. Execute `totem-ctl.py status` e confirme estado, conteúdo e sessão.
3. Consulte `/api/metrics` e `/api/events` com o token configurado.
4. Crie/valide/publique um draft pela API; ative o bundle e confirme `reload-content` somente em `ESPERA`.
5. Ative um bundle anterior para testar rollback.
6. Pare `totem-admin.service`: o kiosk deve continuar a experiência atual sem rede ou Admin.
