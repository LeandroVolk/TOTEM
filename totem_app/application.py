"""Composicao do runtime com entrada real ou simulada."""

from __future__ import annotations

from datetime import datetime
import queue
import sys
from threading import Thread
import time

from ipc.control import ControlServer
from runtime_v2 import RuntimeV2, RuntimeV2Nulo

from .engine import Estado, Evento, TipoEvento, TotemEngine
from .presenter import HeadlessPresenter, PygamePresenter
from .settings import Settings
from .simulator import HELP, SimulationCommands, run_script


def log_event(name, **data):
    now = datetime.now().isoformat(timespec="seconds")
    suffix = " ".join(f"{key}={value}" for key, value in data.items())
    print(f"[{now}] {name}{' ' + suffix if suffix else ''}", flush=True)


def build_runtime(settings):
    runtime = RuntimeV2Nulo()
    server = None
    try:
        runtime = RuntimeV2(settings.database_path, settings.content_root)
        server = ControlServer(settings.control_socket, runtime)
        server.start()
    except Exception as error:
        print(f"[runtime] persistencia indisponivel; usando fallback: {error}")
    return runtime, server


def run(settings: Settings, script=None):
    runtime, server = build_runtime(settings)
    presenter = HeadlessPresenter() if settings.headless else PygamePresenter()
    engine = TotemEngine(runtime.conteudo, settings, runtime=runtime, logger=log_event)
    try:
        if settings.mode == "simulation":
            runtime.pronto(camera_ok=False, mediapipe_ok=False)
            return run_simulation(engine, presenter, script)
        return run_hardware(engine, presenter, runtime)
    finally:
        presenter.close()
        if server is not None:
            server.stop()
        runtime.evento("runtime.stopped")
        log_event("totem_encerrado")


def run_simulation(engine, presenter, script=None):
    print("Modo de simulacao explicitamente ativo. Nenhuma camera sera aberta.")
    presenter.render(engine, 0.0)
    if script is not None:
        outputs = run_script(
            engine, script, start=0.0,
            observer=lambda now: presenter.render(engine, now),
        )
        for output in outputs:
            print(output)
        return 0

    print(HELP)
    commands = SimulationCommands(engine)
    input_queue = queue.Queue()

    def read_input():
        while True:
            line = sys.stdin.readline()
            input_queue.put("quit" if line == "" else line)
            if line == "":
                return

    Thread(target=read_input, daemon=True).start()
    while not engine.encerrar_solicitado:
        try:
            line = input_queue.get(timeout=0.05)
            try:
                result = commands.execute(line)
                if result.output:
                    print(result.output)
            except (ValueError, TypeError) as error:
                print(f"[simulacao] erro: {error}")
        except queue.Empty:
            pass
        presenter.render(engine, commands.now)
    return 0


def run_hardware(engine, presenter, runtime):
    from camera import FfmpegCamera
    from gestos import GestosDetector
    from pessoa import PessoaDetector

    settings = engine.settings
    camera = gestures = person = None
    frame_number = 0
    try:
        gestures = GestosDetector(settings.hand_model_path)
        person = PessoaDetector(
            settings.pose_model_path,
            settings.pose_min_confidence,
            int(settings.camera_fps * settings.absence_seconds),
        )
        camera = FfmpegCamera(
            settings.camera_device, settings.camera_width,
            settings.camera_height, settings.camera_fps,
        ).start()
        runtime.pronto(camera_ok=True, mediapipe_ok=True)
        log_event(
            "totem_iniciado", modo="hardware", plataforma=settings.platform,
            camera=settings.camera_device, resolucao=f"{settings.camera_width}x{settings.camera_height}",
        )
        while not engine.encerrar_solicitado:
            timeout = 1 / settings.attraction_fps if engine.estado == Estado.ESPERA else None
            frame = camera.read_com_timeout(timeout)
            now = time.monotonic()
            if frame is None:
                if camera.encerrada:
                    raise RuntimeError("A camera deixou de fornecer quadros.")
                engine.tick(now)
                presenter.render(engine, now)
                continue
            if frame_number % settings.pose_interval_frames == 0:
                person_state = person.atualizar(frame, peso_frames=settings.pose_interval_frames)
                if person_state["entrou"]:
                    engine.handle(Evento(TipoEvento.PESSOA_ENTROU, now))
                if person_state["saiu"]:
                    engine.handle(Evento(TipoEvento.AUSENCIA_PROLONGADA, now))
            frame_number += 1

            debug = None
            if engine.estado == Estado.SAUDACAO:
                gesture = gestures.atualizar(frame)
                engine.handle(Evento(TipoEvento.JOINHA, now, gesture["joinha"]))
                debug = _debug_frame(frame, gesture, engine) if settings.debug_camera else None
            elif engine.estado in {Estado.ESCOLHA_TEMA, Estado.PERGUNTA}:
                gesture = gestures.atualizar(frame)
                engine.handle(Evento(TipoEvento.DEDOS, now, gesture["numero"]))
                debug = _debug_frame(frame, gesture, engine) if settings.debug_camera else None
            engine.tick(now)
            presenter.render(engine, now, debug_camera=debug)
    except KeyboardInterrupt:
        print("\nEncerrado.")
    finally:
        if camera is not None:
            camera.close()
        if gestures is not None:
            gestures.close()
        if person is not None:
            person.close()
    return 0


def _debug_frame(frame, gesture, engine):
    indicator = engine.view().indicador or {"progresso": 0, "total": 3}
    return {
        "frame": frame,
        "landmarks": gesture["landmarks"],
        "mao_detectada": gesture["mao_detectada"],
        "candidato": gesture["gesto_candidato"],
        "progresso": indicator["progresso"],
        "total": indicator["total"],
    }
