#!/usr/bin/env python3
# '/resposta_rasa' (JSON NLU) → Ollama → publica UMA ÚNICA resposta em '/resposta_bot'
import json
import threading
import ollama
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

MODELO_LLM = 'llama3.2:1b'
MAX_HISTORICO = 1  # Reduzido para 1 para evitar que ele se confunda com o passado em emergências

# Prompt super limpo e direto, sem exemplos que possam confundir o modelo
SYSTEM_PROMPT = """Você é a central de comando (CCO) falando no rádio com o motorista do equipamento.
Regras:
- Fale em português brasileiro natural.
- Seja extremamente conciso. Use no máximo duas frases curtas.
- Responda APENAS com a fala que será transmitida no rádio. Não adicione comentários, explicações ou notas."""

# O Python decide o que o LLM deve fazer, escondendo o nome técnico da intenção
GUIA_DE_ACOES = {
    'solicitar_basculamento': 'Autorize o deslocamento para o local de basculamento informado.',
    'solicitar_carregamento': 'Autorize o deslocamento para o local de carregamento informado.',
    'informar_emergencia': 'Ordene a parada imediata do equipamento e o acionamento do protocolo de segurança.',
    'informar_emergencia_incendio': 'Ordene a evacuação, a parada do equipamento e o acionamento do protocolo contra incêndios.',
    'informar_falha_critica': 'Ordene a parada imediata do equipamento para evitar acidentes.',
    'informar_problema_mecanico': 'Avise que a manutenção/oficina já foi notificada sobre o problema.',
    'saudacao_radio': 'Responda brevemente que a CCO está na escuta e pronta para apoiar.',
    'solicitar_abastecimento': 'Autorize o deslocamento do equipamento até o posto de combustível.',
    'informar_condicao_climatica': 'Agradeça a informação e oriente que o motorista tenha atenção redobrada na via.',
    'solicitar_apoio_pista': 'Confirme que o equipamento de apoio solicitado já está a caminho.'
}

class LLMNode(Node):
    def __init__(self):
        super().__init__('llm_node')
        self._historico = []
        self._lock = threading.Lock()
        self._processando = False 
        
        self.pub = self.create_publisher(String, '/resposta_bot', 10)
        self.create_subscription(String, '/resposta_rasa', self._cb, 10)

        self.get_logger().info(f'Nó Ollama iniciado ({MODELO_LLM}). Aguardando em /resposta_rasa...')

    def _cb(self, msg: String):
        with self._lock:
            if self._processando:
                self.get_logger().warn('Mensagem ignorada: o LLM já está gerando uma resposta.')
                return
            self._processando = True  

        try:
            dados = json.loads(msg.data)
            texto_original = dados.get('texto_original', '')
            intencao = dados.get('intencao', '')
            entidades = dados.get('entidades', [])
            
            threading.Thread(
                target=self._gerar_resposta,
                args=(texto_original, intencao, entidades),
                daemon=True,
            ).start()
            
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON inválido: {e}')
            with self._lock:
                self._processando = False

    def _gerar_resposta(self, texto_original, intencao, entidades):
        try:
            ents_str = ', '.join(f"{e.get('valor')}" for e in entidades) if entidades else "nenhum detalhe específico"
            
            # Pega a instrução mastigada em português, sem nomes técnicos
            instrucao_cco = GUIA_DE_ACOES.get(intencao, 'Responda ao que o motorista disse de forma breve.')

            # O prompt de usuário agora dá uma ordem claríssima do que fazer
            prompt_llm = (
                f"O motorista informou: '{texto_original}' (Detalhes: {ents_str})\n"
                f"Sua tarefa: {instrucao_cco}\n"
                "Escreva agora a sua resposta para o rádio:"
            )

            with self._lock:
                self._historico.append({'role': 'user', 'content': prompt_llm})
                if len(self._historico) > MAX_HISTORICO * 2:
                    self._historico[:] = self._historico[-(MAX_HISTORICO * 2):]
                historico_snapshot = list(self._historico)

            resposta = ollama.chat(
                model=MODELO_LLM,
                messages=[{'role': 'system', 'content': SYSTEM_PROMPT}, *historico_snapshot],
                stream=False,
                keep_alive=-1,
                options={
                    'num_gpu': 0,
                    'temperature': 0.1,  
                    'num_predict': 80, 
                    'num_ctx': 512,
                    'stop': ['\n', 'Motorista:', 'CCO:', 'Sua tarefa:'] # Para na primeira quebra de linha
                }
            )

            texto_completo = resposta.get('message', {}).get('content', '').replace('"', '').strip()

            if texto_completo:
                self.get_logger().info(f'[LLM] Resposta gerada: "{texto_completo}"')
                with self._lock:
                    self._historico.append({'role': 'assistant', 'content': texto_completo})
                self._publicar_resposta(texto_completo)
            else:
                self.get_logger().warn('[LLM] Resposta vazia.')

        except Exception as e:
            self.get_logger().error(f'Erro ao consultar o LLM: {e}')
        
        finally:
            with self._lock:
                self._processando = False

    def _publicar_resposta(self, texto: str):
        payload = {'respostas': [texto], 'streaming': False}
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
