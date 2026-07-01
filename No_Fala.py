#!/usr/bin/env python3
# '/resposta_rasa' (JSON NLU) → Ollama → publica sentença única em '/resposta_bot'

import json
import threading
import ollama
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

MODELO_LLM = 'llama3.2:1b'
MAX_HISTORICO = 2

SYSTEM_PROMPT = """Você é a central de comando (CCO) auxiliando o motorista de um equipamento de mineração via rádio.
Você receberá a intenção detectada pelo sistema e os detalhes (entidades).
Sua função é gerar uma resposta clara, natural e concisa para o motorista.

Regras de Conduta:
- Responda SEMPRE em português brasileiro.
- Máximo 2 frases curtas.
- Tom direto, profissional e focado em segurança.
- Não use markdown ou emojis. Apenas texto para ser falado.

Guia de Ação por Intenção:
- solicitar_basculamento / solicitar_carregamento: Autorize o deslocamento para o local informado.
- informar_emergencia / informar_emergencia_incendio / informar_falha_critica: Ordene parada imediata e acionamento de protocolo de segurança.
- informar_problema_mecanico: Avise que a oficina foi notificada sobre o componente.
- saudacao_radio: Diga que a CCO está na escuta."""

class LLMNode(Node):
    def __init__(self):
        super().__init__('llm_node')
        self._historico = []
        self._lock = threading.Lock()

        self.pub = self.create_publisher(String, '/resposta_bot', 10)
        self.create_subscription(String, '/resposta_rasa', self._cb, 10)
        
        self.get_logger().info(f'Nó Ollama iniciado ({MODELO_LLM}). Aguardando em /resposta_rasa...')

    def _cb(self, msg: String):
        try:
            dados = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON inválido: {e}')
            return

        texto_original = dados.get('texto_original', '')
        intencao = dados.get('intencao', '')
        confianca = dados.get('confianca', 0.0)
        entidades = dados.get('entidades', [])

        threading.Thread(
            target=self._gerar_resposta,
            args=(texto_original, intencao, confianca, entidades),
            daemon=True,
        ).start()

    def _gerar_resposta(self, texto_original, intencao, confianca, entidades):
        ents_str = ', '.join(f"{e.get('entidade')}={e.get('valor')}" for e in entidades) if entidades else "Nenhuma"
        
        prompt_llm = (
            f"O motorista disse: '{texto_original}'\n"
            f"Intenção detectada pelo sistema: {intencao} (confiança: {confianca})\n"
            f"Dados (entidades) detectadas: {ents_str}\n"
            "Gere a resposta da CCO para o motorista no rádio."
        )

        with self._lock:
            self._historico.append({'role': 'user', 'content': prompt_llm})
            if len(self._historico) > MAX_HISTORICO * 2:
                self._historico[:] = self._historico[-(MAX_HISTORICO * 2):]
            historico_snapshot = list(self._historico)

        try:
            # stream=False garante que o Ollama só devolva a resposta quando ela estiver 100% pronta!
            resposta = ollama.chat(
                model=MODELO_LLM,
                messages=[{'role': 'system', 'content': SYSTEM_PROMPT}, *historico_snapshot],
                stream=False, 
                keep_alive=-1,
                options={
                    'temperature': 0.4,
                    'num_predict': 80,
                    'num_ctx': 512
                }
            )

            texto_completo = resposta['message']['content'].strip()

            if texto_completo:
                self._publicar_sentenca(texto_completo)
                with self._lock:
                    self._historico.append({'role': 'assistant', 'content': texto_completo})

        except Exception as e:
            self.get_logger().error(f'Erro no LLM: {e}')
            self._publicar_sentenca("Falha no sistema de comunicação. Repita.")

    def _publicar_sentenca(self, sentenca: str):
        payload = {
            'respostas': [sentenca],
            'streaming': False
        }
        out = String()
        out.data = json.dumps(payload, ensure_ascii=False)
        self.pub.publish(out)

def main(args=None):
    rclpy.init(args=args)
    node = LLMNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()