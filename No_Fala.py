#!/usr/bin/env python3
import json, queue, threading, wave, io, rclpy, traceback
import numpy as np
import sounddevice as sd
from piper import PiperVoice
from rclpy.node import Node
from std_msgs.msg import String

ARQUIVO_AUDIO    = '/home/vrmine-sim/piper_voices/fala.wav'
MODELO_ONNX      = '/home/vrmine-sim/piper_voices/pt_BR-faber-medium.onnx'
MODELO_CONFIG    = '/home/vrmine-sim/piper_voices/pt_BR-faber-medium.onnx.json'
CONFIANCA_MINIMA = 0.80
_ENCERRAR        = object()


class FalaNode(Node):
    def __init__(self):
        super().__init__('fala_node')
        self.ultima_fala = ''
        self._fila_fala  = queue.Queue()
        self._parar      = threading.Event()

        self.get_logger().info('Carregando modelo neural offline (Piper)...')
        try:
            self.voz = PiperVoice.load(MODELO_ONNX, config_path=MODELO_CONFIG)
            self.get_logger().info('Voz Piper (pt-BR) carregada! 100% Offline e pronta para falar.')
        except Exception as e:
            self.get_logger().error(f'Erro ao carregar o modelo: {e}')
            self.voz = None

        threading.Thread(target=self._loop_audio, daemon=True, name='piper-audio').start()
        self.create_subscription(String, '/resposta_bot', self._cb, 10)

    def _cb(self, msg: String):
        try:
            dados     = json.loads(msg.data)
            texto     = ' '.join(dados.get('respostas', []))
            texto     = texto.replace('"', '').replace("'", '').replace('*', '').replace('\n', ' ').strip()
            confianca = dados.get('confianca', 1.0)
            streaming = dados.get('streaming', False)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON inválido: {e}')
            return

        if not texto or confianca < CONFIANCA_MINIMA:
            return
        if not streaming and texto == self.ultima_fala:
            return
        if not streaming:
            self.ultima_fala = texto

        self.get_logger().info(f'Enfileirando: "{texto}"')
        self._fila_fala.put(texto)

    def _loop_audio(self):
        while not self._parar.is_set():
            try:
                texto = self._fila_fala.get(block=True, timeout=0.1)
            except queue.Empty:
                continue
            if texto is _ENCERRAR:
                break
            self._sintetizar_e_tocar(texto)
            self._fila_fala.task_done()

    def _sintetizar_e_tocar(self, texto: str):
        if self.voz is None:
            return
        try:
            # 1. Sintetiza em memória (evita corrida de leitura/escrita no mesmo arquivo em disco)
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_mem:
                wav_mem.setnchannels(1)
                wav_mem.setsampwidth(2)
                wav_mem.setframerate(self.voz.config.sample_rate)
                self.voz.synthesize(texto, wav_mem)

            audio_bytes = buffer.getvalue()

            # 2. Salva uma cópia em disco (apenas para registro/depuração)
            with open(ARQUIVO_AUDIO, 'wb') as f:
                f.write(audio_bytes)

            # 3. Toca direto da memória
            buffer.seek(0)
            with wave.open(buffer, 'rb') as wf:
                sample_rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
                audio_np = np.frombuffer(frames, dtype=np.int16)

            sd.play(audio_np, sample_rate)
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