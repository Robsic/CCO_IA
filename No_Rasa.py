#!/usr/bin/env python3
# /fala_reconhecida → Rasa NLU API → verifica evento → publica em '/resposta_rasa'

import bisect
import json
import threading
import rclpy
import requests
from rclpy.node import Node
from std_msgs.msg import String

URL_NLU    = 'http://localhost:5005/model/parse'
TIMEOUT_S  = 30
DEBOUNCE_S = 0.6

# Mapeamento evento_id → intenções válidas
EVENTO_INTENCOES = {
    0 : {'informar_problema_mecanico'},
    1 : {'informar_falha_critica'},
    3 : {'informar_problema_mecanico'},
    4 : {'informar_problema_mecanico'},
    6 : {'informar_emergencia', 'confirmar_entendimento'},
    7 : {'informar_problema_mecanico', 'informar_falha_critica'},
    8 : {'informar_problema_mecanico'},
    9 : {'informar_problema_mecanico'},
    10: {'informar_problema_mecanico', 'informar_status_operacional'},
    24: {'informar_problema_mecanico', 'informar_falha_critica'},
    25: {'informar_problema_mecanico'},
    26: {'informar_falha_critica'},
    27: {'informar_falha_critica'},
    28: {'informar_problema_mecanico'},
    29: {'informar_problema_mecanico'},
    31: {'informar_problema_mecanico'},
    32: {'informar_condicao_via', 'confirmar_entendimento'},
    35: {'informar_emergencia_incendio', 'informar_emergencia'},
    36: {'informar_problema_mecanico'},
    37: {'informar_emergencia_incendio', 'informar_emergencia'},
    39: {'informar_problema_mecanico', 'informar_falha_critica'},
    40: {'informar_condicao_via'},
    41: {'informar_emergencia', 'informar_emergencia_incendio'},
    42: {'informar_condicao_via'},
    44: {'solicitar_ultrapassagem'},
    45: {'solicitar_ultrapassagem'},
    46: {'solicitar_ultrapassagem'},
    47: {'solicitar_ultrapassagem'},
    49: {'informar_problema_mecanico'},
    52: {'informar_condicao_via', 'solicitar_ultrapassagem'},
    53: {'informar_condicao_via'},
}


def _intencao_valida(evento_id: int, intencao: str) -> bool:
    intencoes = EVENTO_INTENCOES.get(evento_id, set())
    return intencao in intencoes


class RasaNode(Node):
    def __init__(self):
        super().__init__('rasa_node')
        self.pub      = self.create_publisher(String, '/resposta_rasa', 10)
        self.pub_fala = self.create_publisher(String, '/resposta_bot',  10)
        self.sess     = requests.Session()
        self._debounce_lock  = threading.Lock()
        self._debounce_timer = None
        self.create_subscription(String, '/fala_reconhecida', self._cb, 10)
        self.get_logger().info('No Rasa NLU iniciado.')

    def _cb(self, msg: String):
        try:
            dados = json.loads(msg.data)
            texto  = dados.get('fala', '').strip()
            evento = dados.get('evento', {})
        except (json.JSONDecodeError, AttributeError):
            texto  = msg.data.strip()
            evento = {}

        if not texto:
            return

        with self._debounce_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(
                DEBOUNCE_S, self._processar, args=(texto, evento)
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _processar(self, texto: str, evento: dict):
        try:
            resp = self.sess.post(URL_NLU, json={'text': texto}, timeout=TIMEOUT_S)
            resp.raise_for_status()
            nlu = resp.json()
        except Exception as e:
            self.get_logger().error(f'Erro NLU: {e}')
            return

        intencao  = nlu.get('intent', {}).get('name', 'desconhecido')
        confianca = round(nlu.get('intent', {}).get('confidence', 0.0), 4)
        entidades = [
            {'entidade': e.get('entity'), 'valor': e.get('value')}
            for e in nlu.get('entities', [])
        ]
        evento_id = evento.get('id')

        entidades_str = ', '.join(
            f"{e['entidade']}={e['valor']}" for e in entidades
        ) if entidades else 'Nenhuma'

        self.get_logger().info(
            f'NLU -> Texto: "{texto}" | '
            f'Intencao: {intencao} ({confianca}) | '
            f'Entidades: {entidades_str} | '
            f'Evento: {evento_id}'
        )

        # Verifica se a intenção condiz com o evento
        if evento and not _intencao_valida(evento_id, intencao):
            self.get_logger().warn(
                f'Intencao "{intencao}" nao condiz com evento {evento_id}.'
            )
            self._publicar_erro('Sua fala nao foi condizente com a realidade.')
            return

        payload = {
            'texto_original': texto,
            'intencao'      : intencao,
            'confianca'     : confianca,
            'entidades'     : entidades,
            'evento'        : evento,
        }
        out      = String()
        out.data = json.dumps(payload, ensure_ascii=False)
        self.pub.publish(out)

    def _publicar_erro(self, mensagem: str):
        payload  = {'respostas': [mensagem], 'confianca': 1.0, 'streaming': False}
        out      = String()
        out.data = json.dumps(payload, ensure_ascii=False)
        self.pub_fala.publish(out)


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
