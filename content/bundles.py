"""Workspace editorial, bundles selados e ativacao atomica por symlink."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
from uuid import uuid4

from content.providers import BundleContentProvider, LegacyRoteiroProvider, hash_conteudo


class BundleInvalido(ValueError):
    pass


def _agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class GerenciadorBundles:
    def __init__(self, content_root: Path, legacy_provider=None):
        self.root = Path(content_root)
        self.bundles_dir = self.root / "bundles"
        self.staging_dir = self.root / "staging"
        self.current_link = self.root / "current"
        self.legacy_provider = legacy_provider or LegacyRoteiroProvider()
        self.bundles_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def carregar_ativo(self):
        if self.current_link.is_symlink() and self.current_link.exists():
            try:
                return BundleContentProvider(self.current_link.resolve()).carregar()
            except (OSError, ValueError, json.JSONDecodeError, KeyError) as erro:
                print(f"[content] bundle ativo invalido; usando roteiro legado: {erro}")
        return self.legacy_provider.carregar()

    def bootstrap_legado(self):
        """Cria o primeiro bundle, mas preserva roteiro.py como fonte de recuperacao."""
        if self.current_link.exists() or self.current_link.is_symlink():
            return self.carregar_ativo()
        legado = self.legacy_provider.carregar()
        nome = "labeco-pampa-0.1.0"
        destino = self.bundles_dir / nome
        if not destino.exists():
            temporario = self.staging_dir / f"bootstrap-{uuid4().hex}"
            self._escrever_bundle(
                temporario,
                bundle_id="labeco-pampa",
                version="0.1.0",
                experiencia=legado.experiencia,
                parent_bundle=None,
                name="Campo Nativo e Solo Vivo",
            )
            os.replace(temporario, destino)
        self.ativar(nome)
        return self.carregar_ativo()

    def criar_draft(self):
        origem = self._origem_atual()
        destino = self.staging_dir / f"draft-{uuid4().hex}"
        if origem is None:
            legado = self.legacy_provider.carregar()
            self._escrever_bundle(
                destino,
                bundle_id=legado.bundle_id,
                version="draft",
                experiencia=legado.experiencia,
                parent_bundle=None,
                name="Draft a partir do roteiro legado",
            )
        else:
            shutil.copytree(origem, destino)
        return destino

    def validar(self, bundle_path: Path):
        bundle_path = Path(bundle_path)
        try:
            manifesto = json.loads((bundle_path / "manifest.json").read_text(encoding="utf-8"))
            experiencia = json.loads((bundle_path / "catalog" / "experience.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erro:
            raise BundleInvalido(f"Bundle incompleto: {erro}") from erro
        for campo in ("bundle_id", "version", "schema_version", "name", "created_at"):
            if not manifesto.get(campo):
                raise BundleInvalido(f"Manifesto sem {campo}.")
        self._validar_experiencia(experiencia)
        esperado = hash_conteudo(experiencia)
        atual = manifesto.get("content_hash")
        if atual and atual != esperado:
            raise BundleInvalido("Hash declarado nao corresponde ao catalogo.")
        return {"manifest": manifesto, "content_hash": esperado}

    def publicar(self, draft_path: Path, version: str):
        draft_path = Path(draft_path)
        validado = self.validar(draft_path)
        experiencia = json.loads((draft_path / "catalog" / "experience.json").read_text(encoding="utf-8"))
        manifesto = validado["manifest"]
        destino = self.bundles_dir / f"{manifesto['bundle_id']}-{version}"
        if destino.exists():
            raise BundleInvalido("Ja existe um bundle com essa versao.")
        temporario = self.staging_dir / f"seal-{uuid4().hex}"
        self._escrever_bundle(
            temporario,
            bundle_id=manifesto["bundle_id"],
            version=version,
            experiencia=experiencia,
            parent_bundle=manifesto.get("parent_bundle"),
            name=manifesto["name"],
        )
        os.replace(temporario, destino)
        return BundleContentProvider(destino).carregar()

    def ativar(self, nome_bundle: str):
        destino = self.bundles_dir / nome_bundle
        self.validar(destino)
        temporario = self.root / f".current-{uuid4().hex}"
        relativo = os.path.relpath(destino, self.root)
        temporario.symlink_to(relativo, target_is_directory=True)
        os.replace(temporario, self.current_link)
        return BundleContentProvider(destino).carregar()

    def rollback(self, nome_bundle: str):
        return self.ativar(nome_bundle)

    def listar(self):
        resultado = []
        for caminho in sorted(self.bundles_dir.iterdir()):
            if not caminho.is_dir():
                continue
            try:
                conteudo = BundleContentProvider(caminho).carregar()
            except (OSError, ValueError, json.JSONDecodeError, KeyError):
                continue
            resultado.append(
                {
                    "name": caminho.name,
                    "bundle_id": conteudo.bundle_id,
                    "version": conteudo.version,
                    "content_hash": conteudo.content_hash,
                    "active": self.current_link.is_symlink()
                    and self.current_link.resolve() == caminho.resolve(),
                }
            )
        return resultado

    def _origem_atual(self):
        if self.current_link.is_symlink() and self.current_link.exists():
            return self.current_link.resolve()
        return None

    @staticmethod
    def _validar_experiencia(experiencia):
        for chave in ("saudacao", "escolha_tema", "temas", "encerramento"):
            if chave not in experiencia:
                raise BundleInvalido(f"Catalogo sem {chave}.")
        if not isinstance(experiencia["temas"], dict) or not experiencia["temas"]:
            raise BundleInvalido("Catalogo precisa de pelo menos um tema.")
        for tema in experiencia["temas"].values():
            for pergunta in tema.get("perguntas", []):
                quantidade = len(pergunta.get("alternativas", {}))
                if not 1 <= quantidade <= 5:
                    raise BundleInvalido("Cada pergunta deve ter entre 1 e 5 alternativas.")

    @staticmethod
    def _escrever_bundle(destino, bundle_id, version, experiencia, parent_bundle, name):
        destino.mkdir(parents=True)
        catalogo = destino / "catalog"
        catalogo.mkdir()
        experiencia = deepcopy(experiencia)
        content_hash = hash_conteudo(experiencia)
        manifesto = {
            "bundle_id": bundle_id,
            "version": version,
            "schema_version": "1",
            "name": name,
            "created_at": _agora(),
            "content_hash": content_hash,
            "parent_bundle": parent_bundle,
        }
        (destino / "manifest.json").write_text(
            json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (catalogo / "experience.json").write_text(
            json.dumps(experiencia, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
