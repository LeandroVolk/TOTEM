# Sessões, eventos e métricas

Uma sessão representa uma interação, não uma pessoa. Ela armazena identificador, início/fim, status (`started`, `completed`, `abandoned`), bundle/hash de conteúdo, tema e quantidade de respostas.

O Event Log em SQLite armazena fatos cronológicos em `events`:

```text
event_id, stream, session_id, timestamp, event_type, payload_json
```

Eventos de visitante pertencem ao stream `runtime`, por exemplo `presence.detected`, `interaction.started`, `gesture.confirmed`, `theme.selected`, `question.shown`, `question.answered`, `interaction.completed` e `interaction.abandoned`. Ações administrativas pertencem ao stream `admin`.

Não são gravados frames, fotografias, vídeos, biometria ou identificadores pessoais. Métricas como taxa de conclusão, duração média e respostas são consultas derivadas, não agregados independentes.
