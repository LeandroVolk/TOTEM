import subprocess
import numpy as np
import time

WIDTH = 320
HEIGHT = 240
FPS = 5

# Sensibilidade
LIMIAR_PIXEL = 25
PERCENTUAL_MOVIMENTO = 5.0
COOLDOWN = 5

cmd = [
    "ffmpeg",
    "-loglevel", "quiet",
    "-f", "v4l2",
    "-video_size", f"{WIDTH}x{HEIGHT}",
    "-framerate", str(FPS),
    "-i", "/dev/video0",
    "-f", "rawvideo",
    "-pix_fmt", "gray",
    "-"
]

processo = subprocess.Popen(cmd, stdout=subprocess.PIPE)

frame_size = WIDTH * HEIGHT
frame_anterior = None
ultimo_evento = 0

print("Totem iniciado.")
print("Aguardando movimento...")

try:
    while True:
        dados = processo.stdout.read(frame_size)

        if len(dados) != frame_size:
            print("Falha ao receber imagem da câmera.")
            break

        frame = np.frombuffer(
            dados,
            dtype=np.uint8
        ).reshape((HEIGHT, WIDTH))

        if frame_anterior is not None:
            diferenca = np.abs(
                frame.astype(np.int16)
                - frame_anterior.astype(np.int16)
            )

            pixels_movimento = np.sum(
                diferenca > LIMIAR_PIXEL
            )

            percentual = (
                pixels_movimento / (WIDTH * HEIGHT)
            ) * 100

            agora = time.time()

            if (
                percentual > PERCENTUAL_MOVIMENTO
                and agora - ultimo_evento > COOLDOWN
            ):
                print(
                    f"🚶 MOVIMENTO DETECTADO "
                    f"({percentual:.1f}%)"
                )

                subprocess.run([
                    "mpv",
                    "--fs",
                    "--really-quiet",
                    "bemvindo.mp4"
                ])


                # Descarta frames acumulados enquanto o vídeo estava tocando
                for _ in range(10):
                    processo.stdout.read(frame_size)

                # Cria uma nova referência para comparação
                frame_anterior = None

                ultimo_evento = time.time()

                print("Aguardando novo movimento...")


        frame_anterior = frame.copy()

        time.sleep(0.02)

except KeyboardInterrupt:
    print("\nTotem encerrado.")

finally:
    processo.terminate()
