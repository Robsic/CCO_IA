#!/usr/bin/env python3
# Vosk → /fala_reconhecida (Com corte PTT agressivo)

import json
import queue
import threading
import rclpy
import sounddevice as sd
from rclpy.node import Node
from std_msgs.msg import Int8, String
from vosk import KaldiRecognizer, Model, SetLogLevel

SetLogLevel(-1)

_SAMPLE_RATE = 16000
_BLOCK_SIZE  = 4000

class VoskNode(Node):
    def __init__(self):
        super().__init__('vosk_node')
        self.pub = self.create_publisher(String, '/fala_reconhecida', 10)
        self.rec = KaldiRecognizer(Model('vosk-model-small-pt-0.3'), _SAMPLE_RATE)
        self.q = queue.Queue()
        
        self.ouvindo = False
        self.botao_estado = False
        self.ja_publicou = False
        self._parar = threading.Event()
        
        self._thread_audio = threading.Thread(target=self._loop_audio, daemon=True, name='vosk-audio')
        
        # Callback customizado para só enfileirar áudio se o botão estiver apertado
        self.stream = sd.RawInputStream(
            samplerate=_SAMPLE_RATE,
            blocksize=_BLOCK_SIZE,
            dtype='int16',
            channels=1,
            callback=self._audio_callback
        )
        self.stream.start()
        self._thread_audio.start()
        
        self.create_subscription(Int8, '/botao_acionado', self._botao_cb, 10)
        self.get_logger().info('Nó Vosk iniciado. Aguardando acionamento do rádio (PTT)...')

    def _audio_callback(self, indata, frames, time, status):
        # Evita processamento inútil de CPU quando o rádio está desligado
        if self.ouvindo:
            self.q.put(bytes(indata))

    def _botao_cb(self, msg: Int8):
        novo_estado = bool(msg.data)
        
        # Botão Pressionado -> Começa a gravar
        if novo_estado and not self.botao_estado:
            self.rec.Reset()
            self.ja_publicou = False
            # Limpa qualquer lixo da fila instantaneamente usando mutex
            with self.q.mutex:
                self.q.queue.clear()
            self.ouvindo = True
            self.get_logger().info('🎙️ PTT Pressionado: Escutando...')

        # Botão Solto -> Corte agressivo e envio imediato
        elif not novo_estado and self.botao_estado:
            self.ouvindo = False
            if not self.ja_publicou:
                self._forcar_resultado_imediato()

        self.botao_estado = novo_estado

    def _forcar_resultado_imediato(self):
        # Processa o restinho da fila rápido
        while not self.q.empty():
            try:
                self.rec.AcceptWaveform(self.q.get_nowait())
            except queue.Empty:
                break

        # Extrai o PartialResult (não espera o tempo de silêncio para dar FinalResult)
        texto = json.loads(self.rec.PartialResult()).get('partial', '').strip()
        
        if not texto:
            texto = json.loads(self.rec.FinalResult()).get('text', '').strip()

        if texto:
            self.get_logger().info(f'✅ Enviado (Corte PTT): "{texto}"')
            self._publicar(texto)
        else:
            self.get_logger().info('❌ Nenhuma fala detectada.')
            
        self.rec.Reset()

    def _loop_audio(self):
        while not self._parar.is_set():
            try:
                data = self.q.get(block=True, timeout=0.1)
            except queue.Empty:
                continue

            if not self.ouvindo:
                continue

            # Se o Vosk detectar uma pausa natural ENQUANTO o botão ainda tá apertado
            if self.rec.AcceptWaveform(data):
                texto = json.loads(self.rec.Result()).get('text', '').strip()
                if texto and not self.ja_publicou:
                    self.get_logger().info(f'✅ Enviado (Pausa Natural): "{texto}"')
                    self._publicar(texto)
                    self.ja_publicou = True
                    self.rec.Reset()

    def _publicar(self, texto: str):
        m = String()
        m.data = texto
        self.pub.publish(m)
        self.ja_publicou = True

    def destroy_node(self):
        self._parar.set()
        self._thread_audio.join(timeout=1.0)
        self.stream.stop()
        self.stream.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = VoskNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()