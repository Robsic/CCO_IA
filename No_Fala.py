#!/usr/bin/env python3
import json, queue, threading, rclpy, traceback
import torch
import torchaudio
import sounddevice as sd
from rclpy.node import Node
from std_msgs.msg import String

# Arquivo agora em .wav para evitar dependências chatas de conversão
ARQUIVO_AUDIO    = '/home/giovanna/Downloads/IA/piper_voices/fala.wav'
CONFIANCA_MINIMA = 0.70
_ENCERRAR        = object()

class FalaNode(Node):
    def __init__(self):
        super().__init__('fala_node')
        self.ultima_fala = ''
        self._fila_fala  = queue.Queue()
        self._parar      = threading.Event()
        
        self.get_logger().info('Carregando modelo neural offline (Silero)...')
        
        # O Silero precisa baixar o modelo na 1ª vez. Depois fica no cache e roda 100% offline.
        self.device = torch.device('cpu')
        try:
            self.model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-models',
                model='silero_tts',
                language='pt',
                speaker='v3_pt',
                trust_repo=True
            )
            self.sample_rate = 48000
            self.voz = 'camila' # Voz feminina super natural
            self.get_logger().info('Voz da Camila ativada! 100% Offline e pronto para falar.')
        except Exception as e:
            self.get_logger().error(f'Erro ao carregar o modelo: {e}')
            self.model = None

        threading.Thread(target=self._loop_audio, daemon=True, name='silero-audio').start()
        self.create_subscription(String, '/resposta_bot', self._cb, 10)

    def _cb(self, msg: String):
        try:
            dados     = json.loads(msg.data)
            texto     = ' '.join(dados.get('respostas', []))
            texto     = texto.replace('"','').replace("'",'').replace('*','').replace('\n',' ').strip()
            confianca = dados.get('confianca', 1.0)
            streaming = dados.get('streaming', False)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON inválido: {e}')
            return

        if not texto or confianca < CONFIANCA_MINIMA: return
        if not streaming and texto == self.ultima_fala: return
        if not streaming: self.ultima_fala = texto

        self.get_logger().info(f'Enfileirando: "{texto}"')
        self._fila_fala.put(texto)

    def _loop_audio(self):
        while not self._parar.is_set():
            try:
                texto = self._fila_fala.get(block=True, timeout=0.1)
            except queue.Empty:
                continue
            if texto is _ENCERRAR: break
            self._sintetizar_e_tocar(texto)
            self._fila_fala.task_done()

    def _sintetizar_e_tocar(self, texto: str):
        if self.model is None: return
        
        try:
            # 1. A IA gera o áudio puramente na memória (rápido!)
            audio_tensor = self.model.apply_tts(
                text=texto,
                speaker=self.voz,
                sample_rate=self.sample_rate
            )

            # 2. Salva o arquivo .wav na pasta que você pediu
            torchaudio.save(ARQUIVO_AUDIO, audio_tensor.unsqueeze(0), self.sample_rate)

            # 3. Toca o áudio diretamente (sem precisar de mpg123 ou pydub)
            audio_np = audio_tensor.numpy()
            sd.play(audio_np, self.sample_rate)
            sd.wait()
            
            self.get_logger().info(f'Áudio salvo em {ARQUIVO_AUDIO} e reproduzido.')

        except Exception:
            self.get_logger().error(f'Erro ao processar/tocar:\n{traceback.format_exc()}')

    def destroy_node(self):
        self._parar.set()
        self._fila_fala.put(_ENCERRAR)
        sd.stop()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    n = FalaNode()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()