from datetime import datetime
from enum import Enum, auto
import time

from camera import FfmpegCamera
from config import (
    ABANDONO_SEGUNDOS,
    ATRACAO_FPS,
    CAMERA_DEVICE,
    DEBUG_CAMERA,
    DEBUG_GESTOS,
    DEBUG_GESTOS_INTERVALO_SEGUNDOS,
    FPS,
    HEIGHT,
    JOINHA_FRAMES_CONFIRMAR,
    JOINHA_RECONHECIDO_SEGUNDOS,
    MAO_FRAMES_CONFIRMAR,
    MAO_FRAMES_PERDER,
    POSE_INTERVALO_FRAMES,
    RESPOSTA_DESTAQUE_SEGUNDOS,
    RESPOSTA_FRAMES_CONFIRMAR,
    RESPOSTA_FRAMES_LIBERAR,
    RESPOSTA_INTERVALO_SEGUNDOS,
    WIDTH,
)
from dialogo import DialogoPygame
from gestos import GestosDetector
from pessoa import PessoaDetector
from roteiro import ENCERRAMENTO, ESCOLHA_TEMA, SAUDACAO, feedback_da_resposta, tema_por_numero
from tela_atracao import TelaAtracao
from tela_pygame import TelaPygame


class Estado(Enum):
    ESPERA = auto()
    SAUDACAO = auto()
    CONFIRMACAO_JOINHA = auto()
    ESCOLHA_TEMA = auto()
    PERGUNTA = auto()
    FEEDBACK = auto()
    ENCERRAMENTO = auto()


def registrar_evento(nome, **dados):
    agora = datetime.now().isoformat(timespec="seconds")
    extras = " ".join(f"{chave}={valor}" for chave, valor in dados.items())
    if extras:
        print(f"[{agora}] {nome} {extras}")
    else:
        print(f"[{agora}] {nome}")


def novo_controle_gestos():
    return {
        "mao_visivel": False,
        "frames_com_mao": 0,
        "frames_sem_mao": 0,
        "frames_joinha": 0,
        "numero_candidato": None,
        "frames_numero": 0,
        "frames_neutros": 0,
        "aguarda_neutro": True,
        "ultima_resposta_em": 0.0,
    }


def atualizar_mao(controle, gesto):
    if gesto["mao_detectada"]:
        controle["frames_com_mao"] += 1
        controle["frames_sem_mao"] = 0
    else:
        controle["frames_sem_mao"] += 1
        controle["frames_com_mao"] = 0

    if (
        not controle["mao_visivel"]
        and controle["frames_com_mao"] >= MAO_FRAMES_CONFIRMAR
    ):
        controle["mao_visivel"] = True
        registrar_evento("mao_detectada")
    elif (
        controle["mao_visivel"]
        and controle["frames_sem_mao"] >= MAO_FRAMES_PERDER
    ):
        controle["mao_visivel"] = False
        registrar_evento("mao_perdida")


def atualizar_joinha(controle, gesto):
    if gesto["joinha"]:
        controle["frames_joinha"] += 1
    else:
        controle["frames_joinha"] = 0


def atualizar_numero(controle, gesto):
    numero = gesto["numero"]
    if numero is None:
        controle["numero_candidato"] = None
        controle["frames_numero"] = 0
        controle["frames_neutros"] += 1
        return

    controle["frames_neutros"] = 0
    if numero == controle["numero_candidato"]:
        controle["frames_numero"] += 1
    else:
        controle["numero_candidato"] = numero
        controle["frames_numero"] = 1


def bloquear_respostas(controle, agora):
    controle["numero_candidato"] = None
    controle["frames_numero"] = 0
    controle["frames_neutros"] = 0
    controle["aguarda_neutro"] = True
    controle["ultima_resposta_em"] = agora


def atualizar_liberacao_resposta(controle, agora):
    if (
        controle["aguarda_neutro"]
        and controle["frames_neutros"] >= RESPOSTA_FRAMES_LIBERAR
        and agora - controle["ultima_resposta_em"] >= RESPOSTA_INTERVALO_SEGUNDOS
    ):
        controle["aguarda_neutro"] = False
        registrar_evento(
            "resposta_liberada",
            liberar_frames=RESPOSTA_FRAMES_LIBERAR,
        )


def resposta_confirmada(controle):
    return (
        not controle["aguarda_neutro"]
        and controle["numero_candidato"] in (1, 2)
        and controle["frames_numero"] >= RESPOSTA_FRAMES_CONFIRMAR
    )


def indicador_joinha(controle):
    if controle["frames_joinha"] <= 0:
        return None
    return {
        "gesto": "joinha",
        "progresso": controle["frames_joinha"],
        "total": JOINHA_FRAMES_CONFIRMAR,
    }


def indicador_resposta(controle):
    if controle["aguarda_neutro"] or controle["numero_candidato"] not in (1, 2):
        return None
    return {
        "gesto": str(controle["numero_candidato"]),
        "progresso": controle["frames_numero"],
        "total": RESPOSTA_FRAMES_CONFIRMAR,
    }


def dados_debug_camera(frame, gesto, controle, estado):
    if not DEBUG_CAMERA:
        return None
    if estado == Estado.SAUDACAO:
        candidato = "joinha" if gesto["joinha"] else "indefinido"
        progresso = controle["frames_joinha"]
        total = JOINHA_FRAMES_CONFIRMAR
    else:
        candidato = gesto["gesto_candidato"]
        progresso = controle["frames_numero"]
        total = RESPOSTA_FRAMES_CONFIRMAR
    return {
        "frame": frame,
        "landmarks": gesto["landmarks"],
        "mao_detectada": gesto["mao_detectada"],
        "candidato": candidato,
        "progresso": progresso,
        "total": total,
    }


def registrar_debug_gesto(gesto, estado, controle, limite_estavel):
    dedos = "+".join(gesto["dedos_estendidos"]) or "nenhum"
    frames_estaveis = (
        controle["frames_joinha"]
        if estado == Estado.SAUDACAO
        else controle["frames_numero"]
    )
    registrar_evento(
        "gesto_debug",
        estado=estado.name,
        mao=int(gesto["mao_detectada"]),
        dedos=dedos,
        joinha=int(gesto["joinha"]),
        candidato=gesto["gesto_candidato"],
        estavel=f"{frames_estaveis}/{limite_estavel}",
        neutro=f"{controle['frames_neutros']}/{RESPOSTA_FRAMES_LIBERAR}",
        liberado=int(not controle["aguarda_neutro"]),
    )


def main():
    estado = Estado.ESPERA
    camera = None
    pessoa = None
    gestos = None
    tela_pygame = TelaPygame()
    dialogo = DialogoPygame(tela_pygame)
    atracao = TelaAtracao(tela_pygame)
    controle = novo_controle_gestos()
    ultimo_debug_gestos = 0.0
    pessoa_estado = None
    numero_frame = 0
    tema = None
    indice_pergunta = 0
    pergunta_atual = None
    feedback_atual = None
    resposta_atual = None
    inicio_interacao = None
    inicio_pergunta = None
    inicio_feedback = None
    inicio_encerramento = None
    inicio_confirmacao_joinha = None

    try:
        gestos = GestosDetector()
        pessoa = PessoaDetector()
        camera = FfmpegCamera(CAMERA_DEVICE, WIDTH, HEIGHT, FPS).start()

        registrar_evento(
            "totem_iniciado",
            estado=estado.name,
            camera=CAMERA_DEVICE,
            abandono_segundos=ABANDONO_SEGUNDOS,
            pose_intervalo_frames=POSE_INTERVALO_FRAMES,
            resolucao=f"{WIDTH}x{HEIGHT}",
            fps=FPS,
        )
        print("Ctrl+C para sair.")
        atracao.mostrar()

        while True:
            timeout = 1 / ATRACAO_FPS if estado == Estado.ESPERA else None
            frame = camera.read_com_timeout(timeout)
            if frame is None:
                if camera.encerrada:
                    registrar_evento("erro_camera", detalhe="falha_ao_receber_frame")
                    break
                atracao.mostrar()
                continue

            if numero_frame % POSE_INTERVALO_FRAMES == 0:
                pessoa_estado = pessoa.atualizar(
                    frame,
                    peso_frames=POSE_INTERVALO_FRAMES,
                )
            numero_frame += 1
            agora = time.monotonic()

            if estado != Estado.ESPERA and pessoa_estado["saiu"]:
                duracao = 0.0 if inicio_interacao is None else agora - inicio_interacao
                registrar_evento(
                    "abandono_interacao",
                    sem_pose_segundos=ABANDONO_SEGUNDOS,
                    duracao_segundos=round(duracao, 1),
                )
                estado = Estado.ESPERA
                controle = novo_controle_gestos()
                tema = None
                pergunta_atual = None
                feedback_atual = None
                dialogo.fechar()
                atracao.reiniciar()
                atracao.mostrar()
                continue

            if estado == Estado.ESPERA:
                atracao.mostrar()
                if pessoa_estado["entrou"] or pessoa_estado["presente"]:
                    estado = Estado.SAUDACAO
                    inicio_interacao = agora
                    controle = novo_controle_gestos()
                    atracao.ocultar()
                    registrar_evento("pessoa_detectada")
                    registrar_evento("inicio_interacao")
                    dialogo.mostrar(
                        SAUDACAO["mensagem"],
                        aguardando=True,
                        complemento=SAUDACAO["cta"],
                    )
                continue

            if estado == Estado.SAUDACAO:
                gesto = gestos.atualizar(frame)
                atualizar_mao(controle, gesto)
                atualizar_joinha(controle, gesto)
                if (
                    DEBUG_GESTOS
                    and agora - ultimo_debug_gestos >= DEBUG_GESTOS_INTERVALO_SEGUNDOS
                ):
                    registrar_debug_gesto(gesto, estado, controle, JOINHA_FRAMES_CONFIRMAR)
                    ultimo_debug_gestos = agora

                if (
                    controle["mao_visivel"]
                    and controle["frames_joinha"] >= JOINHA_FRAMES_CONFIRMAR
                ):
                    registrar_evento("joinha_inicial", confirmar_frames=JOINHA_FRAMES_CONFIRMAR)
                    estado = Estado.CONFIRMACAO_JOINHA
                    inicio_confirmacao_joinha = agora
                    dialogo.mostrar("Joinha reconhecido", aguardando=False, confirmado=True)
                else:
                    dialogo.mostrar(
                        SAUDACAO["mensagem"],
                        aguardando=True,
                        complemento=SAUDACAO["cta"],
                        indicador=indicador_joinha(controle),
                        debug_camera=dados_debug_camera(frame, gesto, controle, estado),
                    )
                continue

            if estado == Estado.CONFIRMACAO_JOINHA:
                dialogo.mostrar("Joinha reconhecido", aguardando=False, confirmado=True)
                if agora - inicio_confirmacao_joinha >= JOINHA_RECONHECIDO_SEGUNDOS:
                    estado = Estado.ESCOLHA_TEMA
                    bloquear_respostas(controle, agora)
                    dialogo.mostrar_pergunta(
                        ESCOLHA_TEMA["pergunta"],
                        ESCOLHA_TEMA["alternativas"],
                        aguardando=True,
                    )
                continue

            if estado in (Estado.ESCOLHA_TEMA, Estado.PERGUNTA):
                if estado == Estado.ESCOLHA_TEMA:
                    etapa = ESCOLHA_TEMA
                    titulo = None
                else:
                    etapa = pergunta_atual
                    titulo = tema["titulo"]

                gesto = gestos.atualizar(frame)
                atualizar_mao(controle, gesto)
                atualizar_numero(controle, gesto)
                atualizar_liberacao_resposta(controle, agora)
                if (
                    DEBUG_GESTOS
                    and agora - ultimo_debug_gestos >= DEBUG_GESTOS_INTERVALO_SEGUNDOS
                ):
                    registrar_debug_gesto(gesto, estado, controle, RESPOSTA_FRAMES_CONFIRMAR)
                    ultimo_debug_gestos = agora

                dialogo.mostrar_pergunta(
                    etapa["pergunta"],
                    etapa["alternativas"],
                    aguardando=True,
                    titulo=titulo,
                    indicador=indicador_resposta(controle),
                    debug_camera=dados_debug_camera(frame, gesto, controle, estado),
                )

                if not resposta_confirmada(controle):
                    continue

                numero = controle["numero_candidato"]
                bloquear_respostas(controle, agora)
                if estado == Estado.ESCOLHA_TEMA:
                    tema = tema_por_numero(numero)
                    indice_pergunta = 0
                    pergunta_atual = tema["perguntas"][indice_pergunta]
                    inicio_pergunta = agora
                    estado = Estado.PERGUNTA
                    registrar_evento(
                        "tema_escolhido",
                        numero=numero,
                        tema=tema["id"],
                    )
                    registrar_evento(
                        "pergunta_exibida",
                        pergunta=pergunta_atual["id"],
                        tema=tema["id"],
                    )
                    continue

                resposta_atual = numero
                feedback_atual = feedback_da_resposta(pergunta_atual, numero)
                inicio_feedback = agora
                tempo_resposta = agora - inicio_pergunta
                estado = Estado.FEEDBACK
                registrar_evento(
                    "resposta_recebida",
                    pergunta=pergunta_atual["id"],
                    numero=numero,
                    alternativa=pergunta_atual["alternativas"][numero],
                    esperada=pergunta_atual["resposta_esperada"],
                    correta=feedback_atual["correta"],
                    tempo_segundos=round(tempo_resposta, 1),
                    confirmar_frames=RESPOSTA_FRAMES_CONFIRMAR,
                )
                dialogo.mostrar_pergunta(
                    pergunta_atual["pergunta"],
                    pergunta_atual["alternativas"],
                    aguardando=False,
                    selecionada=resposta_atual,
                    titulo=tema["titulo"],
                    status="Resposta registrada. Pode baixar a mão",
                    confirmado=True,
                )
                continue

            if estado == Estado.FEEDBACK:
                tempo_feedback = agora - inicio_feedback
                if tempo_feedback < RESPOSTA_DESTAQUE_SEGUNDOS:
                    dialogo.mostrar_pergunta(
                        pergunta_atual["pergunta"],
                        pergunta_atual["alternativas"],
                        aguardando=False,
                        selecionada=resposta_atual,
                        titulo=tema["titulo"],
                        status="Resposta registrada. Pode baixar a mão",
                        confirmado=True,
                    )
                    continue

                if tempo_feedback < RESPOSTA_DESTAQUE_SEGUNDOS + feedback_atual["duracao"]:
                    dialogo.mostrar(
                        feedback_atual["texto"],
                        aguardando=False,
                        complemento=feedback_atual["complemento"],
                    )
                    continue

                indice_pergunta += 1
                if indice_pergunta < len(tema["perguntas"]):
                    pergunta_atual = tema["perguntas"][indice_pergunta]
                    inicio_pergunta = agora
                    estado = Estado.PERGUNTA
                    bloquear_respostas(controle, agora)
                    registrar_evento(
                        "pergunta_exibida",
                        pergunta=pergunta_atual["id"],
                        tema=tema["id"],
                    )
                else:
                    estado = Estado.ENCERRAMENTO
                    inicio_encerramento = agora
                    dialogo.mostrar(ENCERRAMENTO["mensagem"], aguardando=False)
                continue

            if estado == Estado.ENCERRAMENTO:
                dialogo.mostrar(ENCERRAMENTO["mensagem"], aguardando=False)
                if agora - inicio_encerramento >= ENCERRAMENTO["duracao"]:
                    duracao = agora - inicio_interacao
                    registrar_evento(
                        "interacao_concluida",
                        tema=tema["id"],
                        duracao_segundos=round(duracao, 1),
                    )
                    estado = Estado.ESPERA
                    controle = novo_controle_gestos()
                    tema = None
                    pergunta_atual = None
                    feedback_atual = None
                    dialogo.fechar()
                    atracao.reiniciar()
                    atracao.mostrar()

    except KeyboardInterrupt:
        print("\nEncerrado.")

    finally:
        dialogo.fechar()
        tela_pygame.fechar()
        if camera is not None:
            camera.close()
        if gestos is not None:
            gestos.close()
        if pessoa is not None:
            pessoa.close()
        registrar_evento("totem_encerrado")


if __name__ == "__main__":
    main()
