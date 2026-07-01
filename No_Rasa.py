#!/usr/bin/env python3
# /fala_reconhecida → Rasa NLU API → publica intenções/entidades em '/resposta_rasa'
import json
import threading
import rclpy
import requests
from rclpy.node import Node
from std_msgs.msg import String

URL_NLU = 'http://localhost:5005/model/parse'
TIMEOUT_S = 5
DEBOUNCE_S = 0.6  # tempo de espera sem novas mensagens antes de processar


class RasaNode(Node):
    def __init__(self):
        super().__init__('rasa_node')
        self.pub = self.create_publisher(String, '/resposta_rasa', 10)
        # O requests.Session() reutiliza o túnel TCP, acelerando a comunicação local
        self.sess = requests.Session()
        self._debounce_lock = threading.Lock()
        self._debounce_timer = None
        self.create_subscription(String, '/fala_reconhecida', self._cb, 10)
        self.get_logger().info('Nó Rasa NLU iniciado.')

    def _cb(self, msg: String):
        texto = msg.data.strip()
        if not texto:
            return

        # Debounce: cada nova transcrição reinicia o temporizador.
        # Só processamos o texto quando ficar DEBOUNCE_S sem novas mensagens,
        # evitando disparar o NLU várias vezes para transcrições parciais.
        with self._debounce_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(DEBOUNCE_S, self._processar, args=(texto,))
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _processar(self, texto: str):
        try:
            resp = self.sess.post(URL_NLU, json={'text': texto}, timeout=TIMEOUT_S)
            resp.raise_for_status()
            nlu = resp.json()
        except Exception as e:
            self.get_logger().error(f"Erro NLU: {e}")
            return

        payload = {
            'texto_original': texto,
            'intencao': nlu.get('intent', {}).get('name', 'desconhecido'),
            'confianca': round(nlu.get('intent', {}).get('confidence', 0.0), 4),
            'entidades': [
                {'entidade': e.get('entity'), 'valor': e.get('value')}
                for e in nlu.get('entities', [])
            ]
        }

        out = String()
        out.data = json.dumps(payload, ensure_ascii=False)
        self.pub.publish(out)

        # Log limpo para não travar o terminal com I/O desnecessário
        self.get_logger().info(f"NLU -> Intent: {payload['intencao']} | Entidades extraídas: {len(payload['entidades'])}")

        # Impressão detalhada de intenção e entidades identificadas no terminal
        entidades_str = ', '.join(
            f"{e['entidade']}={e['valor']}" for e in payload['entidades']
        ) if payload['entidades'] else "Nenhuma"
        print(
            f"[NLU] Texto: \"{payload['texto_original']}\" | "
            f"Intenção: {payload['intencao']} (confiança: {payload['confianca']}) | "
            f"Entidades: {entidades_str}",
            flush=True
        )


def main(args=None):
    rclpy.init(args=args)
    node = RasaNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
