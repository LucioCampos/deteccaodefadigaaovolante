# ==========================================================
# DETECÇÃO DE SONOLÊNCIA E FADIGA — EAR + MAR (MEDIAPIPE)
# ==========================================================
#
# Este programa monitora dois sinais com MediaPipe Face Mesh:
#
#   1) EAR (Eye Aspect Ratio) — abertura dos olhos.
#      Olhos fechados por mais de 2 segundos -> alarme de sono.
#      (Implementação simples já fornecida em aula.)
#
#   2) MAR (Mouth Aspect Ratio) — abertura da boca.
#      Detecta bocejos de fadiga segundo os parâmetros do projeto:
#         a) Cada bocejo de fadiga deve durar ao menos 4 segundos;
#         b) A partir de 1 bocejo de 6 s (dentro de uma janela de
#            1 minuto), o alarme de fadiga é disparado.
#
# ==========================================================

# Biblioteca OpenCV — captura da webcam e exibição das imagens.
import cv2

# Biblioteca MediaPipe — detecção dos landmarks faciais.
import mediapipe as mp

# Biblioteca cvzone — exibição de textos e elementos gráficos.
import cvzone

# Cálculo de distâncias entre os landmarks.
import math

# Controle de tempo.
import time

# Execução paralela do alarme (não trava o vídeo).
import threading

# Identifica o sistema operacional para escolher a forma de emitir som.
import platform

# winsound só existe no Windows; importa apenas quando disponível.
if platform.system() == "Windows":
    import winsound


# ==========================================================
# PARÂMETROS DE CONFIGURAÇÃO
# ==========================================================

# ---- Olhos (EAR simples por distância em pixels) ----
LIMIAR_OLHOS = 12        # distância (px) abaixo da qual o olho é "fechado"
TEMPO_SONO = 2           # segundos de olhos fechados para alarme de sono

# ---- Boca (MAR — razão abertura/largura) ----
MAR_LIMIAR = 0.6         # acima disso a boca é considerada bem aberta (bocejo)
DURACAO_BOCEJO = 4       # segundos mínimos para contar como bocejo de fadiga
JANELA_FADIGA = 60       # janela (s) para acumular os bocejos de fadiga
COOLDOWN_ALARME = 60     # intervalo mínimo (s) entre alarmes de fadiga


# ==========================================================
# INICIALIZAÇÃO DA WEBCAM
# ==========================================================

# Captura vídeo da webcam padrão.
# CAP_DSHOW utiliza o backend DirectShow do Windows.
video = cv2.VideoCapture(0, cv2.CAP_DSHOW)


# ==========================================================
# INICIALIZAÇÃO DO MEDIAPIPE FACE MESH
# ==========================================================

mpFaceMesh = mp.solutions.face_mesh
faceMesh = mpFaceMesh.FaceMesh()
mp_drawing = mp.solutions.drawing_utils


# ==========================================================
# VARIÁVEIS DE CONTROLE
# ==========================================================

# ---- Estado dos olhos ----
inicio = 0           # instante em que os olhos foram fechados
status = ""          # estado anterior: "A" aberto / "F" fechado
alarmeCtl = False    # evita disparos repetidos do alarme de sono
tempo = 0            # tempo acumulado com os olhos fechados

# ---- Estado da boca / bocejos ----
boca_aberta = False        # True enquanto a boca está acima do limiar
inicio_bocejo = 0          # instante em que a boca começou a abrir
bocejo_contado = False     # garante que cada bocejo conte só uma vez
tempos_bocejos = []        # timestamps dos bocejos de fadiga (>= 6 s)
ultimo_alarme_fadiga = 0   # instante do último alarme de fadiga (cooldown)


# ==========================================================
# FUNÇÃO DE ALARME
# ==========================================================
def beep_alarme():
    """Emite cinco bipes consecutivos (multiplataforma)."""
    for _ in range(5):
        if platform.system() == "Windows":
            winsound.Beep(1000, 500)
        else:
            # Fallback para macOS/Linux: sino do terminal.
            print("\a", end="", flush=True)
            time.sleep(0.5)


# ==========================================================
# LOOP PRINCIPAL
# ==========================================================
while True:

    # Captura um frame da webcam.
    _, img = video.read()

    # Padroniza o tamanho da imagem.
    img = cv2.resize(img, (800, 640))

    # Converte BGR para RGB (o MediaPipe trabalha com RGB).
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Processa a imagem procurando landmarks faciais.
    results = faceMesh.process(imgRGB)

    # Obtém as dimensões da imagem.
    h, w, _ = img.shape

    # Verifica se alguma face foi de fato encontrada.
    if results.multi_face_landmarks:

        for face in results.multi_face_landmarks:

            # ==================================================
            # LANDMARKS DOS OLHOS  (EAR simples)
            # ==================================================
            # Olho direito: 159 (pálpebra sup.) / 145 (pálpebra inf.)
            # Olho esquerdo: 386 (pálpebra sup.) / 374 (pálpebra inf.)
            di1x, di1y = int(face.landmark[159].x * w), int(face.landmark[159].y * h)
            di2x, di2y = int(face.landmark[145].x * w), int(face.landmark[145].y * h)

            es1x, es1y = int(face.landmark[386].x * w), int(face.landmark[386].y * h)
            es2x, es2y = int(face.landmark[374].x * w), int(face.landmark[374].y * h)

            # ==================================================
            # LANDMARKS DA BOCA  (MAR)
            # ==================================================
            # Vertical (abertura): 13 (lábio sup. interno) / 14 (lábio inf. interno)
            # Horizontal (largura): 61 (canto esq.) / 291 (canto dir.)
            bSupx, bSupy = int(face.landmark[13].x * w),  int(face.landmark[13].y * h)
            bInfx, bInfy = int(face.landmark[14].x * w),  int(face.landmark[14].y * h)
            bEsqx, bEsqy = int(face.landmark[61].x * w),  int(face.landmark[61].y * h)
            bDirx, bDiry = int(face.landmark[291].x * w), int(face.landmark[291].y * h)

            # ==================================================
            # DESENHO DOS LANDMARKS
            # ==================================================
            # Olhos (azul)
            cv2.circle(img, (di1x, di1y), 1, (255, 0, 0), 2)
            cv2.circle(img, (di2x, di2y), 1, (255, 0, 0), 2)
            cv2.circle(img, (es1x, es1y), 1, (255, 0, 0), 2)
            cv2.circle(img, (es2x, es2y), 1, (255, 0, 0), 2)
            # Boca (verde)
            cv2.circle(img, (bSupx, bSupy), 1, (0, 255, 0), 2)
            cv2.circle(img, (bInfx, bInfy), 1, (0, 255, 0), 2)
            cv2.circle(img, (bEsqx, bEsqy), 1, (0, 255, 0), 2)
            cv2.circle(img, (bDirx, bDiry), 1, (0, 255, 0), 2)

            # ==================================================
            # CÁLCULO DA ABERTURA DOS OLHOS  (distância euclidiana)
            # ==================================================
            distDi = math.hypot(di1x - di2x, di1y - di2y)
            distEs = math.hypot(es1x - es2x, es1y - es2y)

            # ==================================================
            # CÁLCULO DO MAR (Mouth Aspect Ratio)
            # ==================================================
            # MAR = abertura vertical / largura horizontal.
            # Usar a razão (e não a distância pura) deixa a medida
            # robusta à distância do rosto em relação à câmera.
            abertura_boca = math.hypot(bSupx - bInfx, bSupy - bInfy)
            largura_boca = math.hypot(bEsqx - bDirx, bEsqy - bDiry)
            mar = abertura_boca / largura_boca if largura_boca != 0 else 0

            # ==================================================
            # CLASSIFICAÇÃO DOS OLHOS  (EAR)
            # ==================================================
            if distDi <= LIMIAR_OLHOS and distEs <= LIMIAR_OLHOS:
                situacao = "F"
                # Detecta a transição Aberto -> Fechado.
                if situacao != status:
                    inicio = time.time()
            else:
                situacao = "A"
                inicio = time.time()
                tempo = 0
                alarmeCtl = False

            # Contagem do tempo de fechamento.
            if situacao == "F":
                tempo = int(time.time() - inicio)

            # Atualiza o estado atual dos olhos.
            status = situacao

            # ==================================================
            # ALARME DE SONO  (olhos fechados por mais de 2 s)
            # ==================================================
            if tempo >= TEMPO_SONO:
                cvzone.putTextRect(
                    img,
                    f'DORMINDO {tempo} SEG',
                    (50, 50), 3, 3,
                    (255, 255, 255), (0, 0, 200)
                )
                if not alarmeCtl:
                    alarmeCtl = True
                    threading.Thread(target=beep_alarme).start()

            # ==================================================
            # DETECÇÃO DE BOCEJO  (MAR)
            # ==================================================
            agora = time.time()

            if mar >= MAR_LIMIAR:
                # Boca aberta acima do limiar.
                if not boca_aberta:
                    # Início de um novo bocejo.
                    boca_aberta = True
                    inicio_bocejo = agora
                    bocejo_contado = False

                # Duração atual do bocejo em andamento.
                duracao_bocejo = agora - inicio_bocejo

                # Mostra o cronômetro do bocejo na tela.
                cvzone.putTextRect(
                    img,
                    f'BOCEJANDO {int(duracao_bocejo)}s',
                    (50, 120), 2, 2,
                    (255, 255, 255), (0, 140, 200)
                )

                # (a) Só conta como "bocejo de fadiga" se durar >= 4 s.
                #     Registra apenas uma vez ao cruzar o limiar de 4 s.
                if duracao_bocejo >= DURACAO_BOCEJO and not bocejo_contado:
                    bocejo_contado = True
                    tempos_bocejos.append(agora)
                    threading.Thread(target=beep_alarme).start()
                    print(f'Bocejo de fadiga registrado ({DURACAO_BOCEJO}s+).')
            else:
                # Boca fechada -> encerra o bocejo atual.
                boca_aberta = False

            # ==================================================
            # ANÁLISE DE FADIGA  (item b)
            # ==================================================
            # Mantém na lista apenas os bocejos ocorridos dentro
            # da janela de 1 minuto.
            tempos_bocejos = [
                t for t in tempos_bocejos if agora - t <= JANELA_FADIGA
            ]

            # (b) A partir de 2 bocejos de fadiga na janela e
            #     respeitando o intervalo mínimo de 1 minuto entre
            #     alarmes, dispara o alarme de fadiga.
            if len(tempos_bocejos) >= 2 and (agora - ultimo_alarme_fadiga) >= COOLDOWN_ALARME:
                ultimo_alarme_fadiga = agora
                tempos_bocejos.clear()   # reinicia a contagem após o alarme

                cvzone.putTextRect(
                    img,
                    'FADIGA DETECTADA!',
                    (50, 190), 3, 3,
                    (255, 255, 255), (0, 0, 200)
                )
                threading.Thread(target=beep_alarme).start()

            # ==================================================
            # PAINEL DE INFORMAÇÕES
            # ==================================================
            cv2.putText(
                img, f'MAR: {mar:.2f}', (50, 600),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
            )
            cv2.putText(
                img, f'Bocejos (1 min): {len(tempos_bocejos)}', (50, 630),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
            )

    # ==========================================================
    # EXIBE O FRAME PROCESSADO
    # ==========================================================
    cv2.imshow('IMG', img)

    # Tecla ESC encerra a aplicação.
    if cv2.waitKey(1) & 0xFF == 27:
        break


# ==========================================================
# FINALIZAÇÃO
# ==========================================================
video.release()
cv2.destroyAllWindows()
