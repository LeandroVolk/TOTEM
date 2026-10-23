# Arquitetura do TOTEM

## Princípios

- A regra de interação não depende de Pygame, câmera ou MediaPipe.
- Hardware e simulador produzem os mesmos eventos.
- O Runtime público continua funcionando sem Admin ou rede.
- Configuração, código, conteúdo publicado e dados operacionais têm ciclos de
  vida separados.
- Falhas de telemetria não derrubam a experiência pública.

## Fluxo

```text
┌────────────────────┐       ┌────────────────────┐
│ ffmpeg + MediaPipe │       │ SimulationCommands │
└─────────┬──────────┘       └──────────┬─────────┘
          └────────── Evento ───────────┘
                         │
                  ┌──────▼──────┐
                  │ TotemEngine │
                  └───┬─────┬───┘
                      │     │
           ┌──────────▼─┐ ┌─▼─────────────────┐
           │ Presenter  │ │ RuntimeV2         │
           │ Pygame     │ │ SQLite + conteúdo │
           └────────────┘ └─────────┬─────────┘
                                    │ AF_UNIX JSON
                              ┌─────▼──────┐
                              │ FastAPI    │
                              │ Admin      │
                              └────────────┘
```

`TotemEngine` possui os estados `ESPERA`, `SAUDACAO`,
`CONFIRMACAO_JOINHA`, `ESCOLHA_TEMA`, `PERGUNTA`, `FEEDBACK` e
`ENCERRAMENTO`. Confirmações e transições usam relógio monotônico. A máquina
aceita gestos 1–5; o bundle atual limita alternativas públicas a 1 e 2.

## Configuração

`totem_app/settings.py` carrega `config/default.toml`, um arquivo indicado por
`TOTEM_CONFIG` e variáveis de ambiente. As constantes antigas de `config.py`
continuam como adaptador para componentes gráficos e detectores preservados.

## Persistência e conteúdo

SQLite guarda sessões e eventos, nunca frames. Bundles vivem em
`CONTENT_ROOT/bundles`; `current` é um symlink trocado atomicamente. O roteiro
Python legado continua como fallback e fonte do bundle inicial.

## Administração e privilégios

Admin e kiosk são processos distintos. O Admin consulta o runtime por socket
Unix e só controla ações fixas por helper/sudoers. Nenhum processo Python roda
como root. O instalador eleva privilégio somente para pacotes, `/etc`, diretórios
de estado e unidades systemd.

## Componentes legados

`movimento.py`, `reprodutor_video.py` e vídeos anteriores são mantidos como
referência, mas não participam do fluxo principal. `deploy.sh` permanece apenas
como aviso de migração; o código original está na tag preservada.
