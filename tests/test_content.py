from content.bundles import GerenciadorBundles


def test_bootstrap_publicacao_ativacao_e_rollback(tmp_path):
    manager = GerenciadorBundles(tmp_path / "content")
    inicial = manager.bootstrap_legado()
    assert inicial.version == "0.1.0"
    assert (tmp_path / "content" / "current").is_symlink()

    draft = manager.criar_draft()
    validado = manager.validar(draft)
    assert validado["content_hash"].startswith("sha256:")
    publicado = manager.publicar(draft, "0.2.0")
    manager.ativar("labeco-pampa-0.2.0")
    assert manager.carregar_ativo().version == "0.2.0"
    manager.rollback("labeco-pampa-0.1.0")
    assert manager.carregar_ativo().version == "0.1.0"
    assert publicado.bundle_id == "labeco-pampa"
