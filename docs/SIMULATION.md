# Modo de simulação

O modo é ativado somente com `--simulate`, `--script` ou
`TOTEM_MODE=simulation`. Ele não importa câmera/MediaPipe e envia eventos para a
mesma `TotemEngine` usada pelo hardware.

## Uso interativo

```bash
./totem.sh run --simulate
```

Cada gesto aceita uma duração. Uma duração menor que o limiar permite testar a
rejeição; a duração padrão confirma o gesto:

```text
enter
thumbs-up 0.2
thumbs-up 0.8
next
next
fingers 1 0.6
next
correct
next
```

`correct`/`incorrect` consultam a pergunta ativa. `fingers 1` a `fingers 5`
permitem verificar eventos fora da capacidade atual do conteúdo, que só publica
alternativas 1 e 2. `leave` inicia a ausência; `absence` e `inactivity`
disparam imediatamente os encerramentos correspondentes. `reset` reinicia a
experiência e `wait` avança o relógio simulado.

## Scripts e CI

```bash
./.venv/bin/python totem.py --simulate --headless \
  --script examples/simulation-full.txt
```

Linhas iniciadas por `#` e linhas vazias são ignoradas. Um comando inválido
encerra o script com número da linha e erro. O relógio simulado elimina esperas
reais e torna os testes determinísticos.
