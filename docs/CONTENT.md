# Conteúdo versionado

O conteúdo ativo vive em `CONTENT_ROOT/current`, um symlink para um diretório imutável em `bundles/`. Um bundle contém:

```text
manifest.json
catalog/experience.json
assets/
```

O manifesto identifica `bundle_id`, `version`, `schema_version`, data, proveniência e `content_hash` SHA-256 do catálogo. A publicação sela um novo diretório; a ativação cria um symlink temporário e usa `rename` atômico. Portanto, o Runtime encontra o bundle anterior inteiro ou o novo inteiro.

`staging/` contém drafts. O fluxo é `draft -> validate -> preview -> publish -> activate`; bundles antigos continuam disponíveis para rollback. `roteiro.py` não foi removido: ele é o provider de fallback e origina o primeiro bundle.

O schema editorial comporta até cinco alternativas. O Runtime público atual é compatível apenas com alternativas `1` e `2`, e recusa ativar um bundle que exija outra capacidade.
