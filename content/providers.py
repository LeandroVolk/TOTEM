"""Provedores de conteudo. O legado segue sendo uma fonte valida de fallback."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from roteiro import ENCERRAMENTO, ESCOLHA_TEMA, SAUDACAO, TEMAS


def hash_conteudo(conteudo):
    serializado = json.dumps(
        conteudo, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{sha256(serializado).hexdigest()}"


def normalizar_experiencia(experiencia):
    """Restaura chaves numericas de alternativas apos leitura do JSON."""
    resultado = deepcopy(experiencia)
    for etapa in (resultado["escolha_tema"],):
        etapa["alternativas"] = {int(chave): valor for chave, valor in etapa["alternativas"].items()}
    for tema in resultado["temas"].values():
        for pergunta in tema["perguntas"]:
            pergunta["alternativas"] = {
                int(chave): valor for chave, valor in pergunta["alternativas"].items()
            }
            pergunta["explicacoes"] = {
                int(chave): valor for chave, valor in pergunta["explicacoes"].items()
            }
    return resultado


@dataclass(frozen=True)
class ConteudoAtivo:
    bundle_id: str
    version: str
    content_hash: str
    experiencia: dict
    origem: str

    @property
    def saudacao(self):
        return self.experiencia["saudacao"]

    @property
    def escolha_tema(self):
        return self.experiencia["escolha_tema"]

    @property
    def temas(self):
        return self.experiencia["temas"]

    @property
    def encerramento(self):
        return self.experiencia["encerramento"]

    def tema_por_numero(self, numero):
        return {1: self.temas["campo_nativo"], 2: self.temas["solo_vivo"]}.get(numero)

    @staticmethod
    def feedback_da_resposta(pergunta, numero):
        resposta_esperada = pergunta["resposta_esperada"]
        return {
            **pergunta["explicacoes"][numero],
            "correta": None if resposta_esperada is None else numero == resposta_esperada,
            "duracao": pergunta["duracao"],
        }


class LegacyRoteiroProvider:
    """Adapter da V1: nenhum conteudo legado precisa ser movido para iniciar a V2."""

    def carregar(self):
        experiencia = {
            "saudacao": deepcopy(SAUDACAO),
            "escolha_tema": deepcopy(ESCOLHA_TEMA),
            "temas": deepcopy(TEMAS),
            "encerramento": deepcopy(ENCERRAMENTO),
        }
        return ConteudoAtivo(
            bundle_id="legacy-roteiro",
            version="v1-functional",
            content_hash=hash_conteudo(experiencia),
            experiencia=experiencia,
            origem="legacy",
        )


class BundleContentProvider:
    def __init__(self, bundle_path: Path):
        self.bundle_path = Path(bundle_path)

    def carregar(self):
        manifesto = json.loads((self.bundle_path / "manifest.json").read_text(encoding="utf-8"))
        experiencia = normalizar_experiencia(
            json.loads((self.bundle_path / "catalog" / "experience.json").read_text(encoding="utf-8"))
        )
        content_hash = hash_conteudo(experiencia)
        if manifesto.get("content_hash") != content_hash:
            raise ValueError("Hash do bundle nao confere com o catalogo.")
        return ConteudoAtivo(
            bundle_id=manifesto["bundle_id"],
            version=manifesto["version"],
            content_hash=content_hash,
            experiencia=experiencia,
            origem="bundle",
        )
