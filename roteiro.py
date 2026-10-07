"""Conteudo declarativo da experiencia Campo Nativo: arte e ciencia do manejo."""

from config import DURACAO_FEEDBACK_SEGUNDOS


SAUDACAO = {
    "id": "saudacao",
    "tipo": "mensagem",
    "mensagem": "Olá! Bem-vindo ao LABECO.\n\nVamos conversar sobre o Pampa?",
    "cta": "DÊ UM JOINHA PARA COMEÇAR",
    "duracao": None,
    "proxima": "escolha_tema",
}

ESCOLHA_TEMA = {
    "id": "escolha_tema",
    "tipo": "escolha",
    "pergunta": "O que você quer conhecer?",
    "alternativas": {
        1: "Campo Nativo",
        2: "Solo Vivo",
    },
    "duracao": None,
    "proxima": "tema_selecionado",
}

TEMAS = {
    "campo_nativo": {
        "id": "campo_nativo",
        "titulo": "Campo Nativo",
        "perguntas": [
            {
                "id": "campo_nativo_1",
                "tipo": "pergunta",
                "pergunta": (
                    "Você pisaria num campo que faz parte de um bioma com cerca "
                    "de 3 mil espécies de plantas?"
                ),
                "alternativas": {1: "Sim", 2: "Não"},
                "resposta_esperada": None,
                "explicacoes": {
                    1: {
                        "texto": (
                            "Provavelmente você já fez isso. Estamos falando do campo "
                            "nativo do Pampa: um ecossistema diverso, produtivo e cheio de vida."
                        ),
                        "complemento": (
                            "O Pampa reúne cerca de 3 mil espécies de plantas, incluindo "
                            "mais de 400 espécies de gramíneas."
                        ),
                    },
                    2: {
                        "texto": (
                            "Talvez você já tenha feito isso sem perceber. Estamos falando do "
                            "campo nativo do Pampa: um ecossistema diverso, produtivo e cheio de vida."
                        ),
                        "complemento": (
                            "O Pampa reúne cerca de 3 mil espécies de plantas, incluindo "
                            "mais de 400 espécies de gramíneas."
                        ),
                    },
                },
                "duracao": DURACAO_FEEDBACK_SEGUNDOS,
                "proxima": "campo_nativo_2",
            },
            {
                "id": "campo_nativo_2",
                "tipo": "pergunta",
                "pergunta": "O pastejo bem manejado pode ajudar a conservar o campo nativo?",
                "alternativas": {1: "Sim", 2: "Não"},
                "resposta_esperada": 1,
                "explicacoes": {
                    1: {
                        "texto": (
                            "Isso mesmo! Quando ajustado às condições do campo, o pastejo "
                            "pode conciliar produção pecuária e conservação da vegetação."
                        ),
                        "complemento": None,
                    },
                    2: {
                        "texto": (
                            "Essa resposta surpreende muita gente: o pastejo bem manejado "
                            "pode ajudar a conservar o campo nativo. O resultado depende da "
                            "intensidade, do momento e das condições do campo."
                        ),
                        "complemento": None,
                    },
                },
                "duracao": DURACAO_FEEDBACK_SEGUNDOS,
                "proxima": "campo_nativo_3",
            },
            {
                "id": "campo_nativo_3",
                "tipo": "pergunta",
                "pergunta": "O bom manejo do campo nativo depende mais de:",
                "alternativas": {1: "Uma receita fixa", 2: "Observação e adaptação"},
                "resposta_esperada": 2,
                "explicacoes": {
                    1: {
                        "texto": (
                            "Uma receita fixa não funciona para todas as situações. O campo "
                            "muda com o clima, as estações, os animais e o manejo."
                        ),
                        "complemento": (
                            "É aqui que a experiência de quem conhece o campo encontra as "
                            "evidências produzidas pela ciência."
                        ),
                    },
                    2: {
                        "texto": (
                            "Exatamente! O campo muda com o clima, as estações, os animais e "
                            "o manejo. Por isso, observar e adaptar é fundamental."
                        ),
                        "complemento": (
                            "É aqui que a experiência de quem conhece o campo encontra as "
                            "evidências produzidas pela ciência."
                        ),
                    },
                },
                "duracao": DURACAO_FEEDBACK_SEGUNDOS,
                "proxima": "encerramento",
            },
        ],
    },
    "solo_vivo": {
        "id": "solo_vivo",
        "titulo": "Solo Vivo",
        "perguntas": [
            {
                "id": "solo_vivo_1",
                "tipo": "pergunta",
                "pergunta": "Quantas classes principais de solo você imagina encontrar no Pampa?",
                "alternativas": {1: "Menos de três", 2: "Pelo menos cinco"},
                "resposta_esperada": 2,
                "explicacoes": {
                    1: {
                        "texto": "São mais do que parece! O Pampa também é diverso debaixo dos nossos pés.",
                        "complemento": (
                            "Entre as classes representativas estão Neossolos, Argissolos, "
                            "Planossolos, Chernossolos e Gleissolos."
                        ),
                    },
                    2: {
                        "texto": "Isso mesmo! O Pampa também é diverso debaixo dos nossos pés.",
                        "complemento": (
                            "Entre as classes representativas estão Neossolos, Argissolos, "
                            "Planossolos, Chernossolos e Gleissolos."
                        ),
                    },
                },
                "duracao": DURACAO_FEEDBACK_SEGUNDOS,
                "proxima": "solo_vivo_2",
            },
            {
                "id": "solo_vivo_2",
                "tipo": "pergunta",
                "pergunta": "Quantas bactérias podem existir em uma colher de chá de solo produtivo?",
                "alternativas": {1: "Centenas de milhões", 2: "Algumas centenas"},
                "resposta_esperada": 1,
                "explicacoes": {
                    1: {
                        "texto": (
                            "Acertou! Uma colher de chá de solo produtivo pode conter de 100 "
                            "milhões a 1 bilhão de bactérias."
                        ),
                        "complemento": (
                            "E ainda existem fungos e muitos outros organismos trabalhando "
                            "nesse pequeno universo."
                        ),
                    },
                    2: {
                        "texto": (
                            "É muito mais! Uma colher de chá de solo produtivo pode conter de "
                            "100 milhões a 1 bilhão de bactérias."
                        ),
                        "complemento": (
                            "E ainda existem fungos e muitos outros organismos trabalhando "
                            "nesse pequeno universo."
                        ),
                    },
                },
                "duracao": DURACAO_FEEDBACK_SEGUNDOS,
                "proxima": "solo_vivo_3",
            },
            {
                "id": "solo_vivo_3",
                "tipo": "pergunta",
                "pergunta": "A fertilidade do solo depende somente dos nutrientes?",
                "alternativas": {1: "Sim", 2: "Não"},
                "resposta_esperada": 2,
                "explicacoes": {
                    1: {
                        "texto": "Os nutrientes são importantes, mas não trabalham sozinhos.",
                        "complemento": (
                            "Um solo saudável também depende de sua estrutura, água, matéria "
                            "orgânica, raízes e organismos vivos."
                        ),
                    },
                    2: {
                        "texto": "Exatamente! O solo é muito mais do que uma reserva de nutrientes.",
                        "complemento": (
                            "Um solo saudável também depende de sua estrutura, água, matéria "
                            "orgânica, raízes e organismos vivos."
                        ),
                    },
                },
                "duracao": DURACAO_FEEDBACK_SEGUNDOS,
                "proxima": "encerramento",
            },
        ],
    },
}

ENCERRAMENTO = {
    "id": "encerramento",
    "tipo": "mensagem",
    "mensagem": (
        "Campo e solo não vivem separados.\n\n"
        "O campo alimenta a vida do solo, e o solo sustenta a vida do campo.\n\n"
        "Manejar bem é compreender essa relação.\n\n"
        "Embrapa Pecuária Sul — ciência junto com você."
    ),
    "duracao": 8.0,
    "proxima": "atracao",
}


def tema_por_numero(numero):
    return {1: TEMAS["campo_nativo"], 2: TEMAS["solo_vivo"]}.get(numero)


def feedback_da_resposta(pergunta, numero):
    resposta_esperada = pergunta["resposta_esperada"]
    return {
        **pergunta["explicacoes"][numero],
        "correta": None if resposta_esperada is None else numero == resposta_esperada,
        "duracao": pergunta["duracao"],
    }
