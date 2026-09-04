#!/usr/bin/env python3
# '/resposta_rasa' (JSON NLU) → Ollama (streaming) → publica cada sentença
import json
import re
import threading
import ollama
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

MODELO_LLM    = 'llama3.2:1b'
MAX_HISTORICO = 1

SYSTEM_PROMPT = """Você é a central de comando (CCO) falando no rádio com o operador de equipamento/caminhão de mina, Sua função é ajudar e auxiliar o motorista.

Regras:
- Fale em português brasileiro natural e profissional.
- Formule apenas uma ou duas frases diretas e objetivas.
- Priorize a segurança e a integridade da operação acima de tudo.
- Sempre dê uma resposta que ajude com medidas de segurança do contexto da mineração.
- Não autorize nada, apenas informe o que o motorista deve fazer nessa situação, com base nas medidas de segurança.
- Responda APENAS com a fala que será transmitida no rádio. Não adicione comentários, explicações, aspas ou notas.
- Use linguagem simples e jargões de rádio apropriados (ex: "Positivo", "Na escuta", "Câmbio", "QAP", "Copiado").
- O texto gerado irá direto para um sintetizador de voz (TTS). Não use formatações especiais ou emojis.
- Em atividades perigosas informe a melhor medida de segurança para o motorista.
- Em caso de perigo em que a permanência do motoria na cabine atente contra a segurança dele, peça para ele evacuar imediatamente.

Exemplos do padrão esperado:

Ação: Ordene parada por falha.
Resposta: Copiado. Pare o equipamento imediatamente, aplique o freio de estacionamento e desligue o motor. A manutenção já foi acionada, mantenha-se seguro na cabine.
"""

GUIA_DE_ACOES = {

    'saudacao_radio'                : 'Responda brevemente que a CCO está em QAP (na escuta) e pronta para apoiar.',
    'solicitar_ultrapassagem'       : 'Oriente o operador a fazer contato de rádio com o veículo à frente e aguardar permissão antes de ultrapassar.',
    'informar_veiculo_leve_proximo' : 'Alerta: Oriente o operador a não se aproximar a menos de 10 metros do veículo leve.',
    'informar_parada_abrupta_frente': 'Oriente o operador a manter distância segura, selecionar neutro e aplicar o freio de estacionamento.',
    'informar_falha_mecanica_eletrica': 'Ordene a parada total, aplicação do freio de estacionamento e desligamento do motor. Confirme que a manutenção será enviada.',
    'informar_falha_freio_direcao'  : 'Falha Critica: Ordene a parada imediata, freio de estacionamento e desligamento do motor. Confirme envio de resgate urgente.',
    'informar_superaquecimento'     : 'Oriente a parar, selecionar Neutro e aumentar o RPM acima de 1200 por mais de 5 segundos para resfriamento.',
    'informar_emergencia_incendio'  : 'Comando Critico: Ordene parada total e saia do veículo, freio de estacionamento, corte do motore e acionamento do sistema de supressão de incêndio.',
    'informar_baixa_visibilidade_poeira': 'Oriente a parar, engatar neutro e aplicar freio de estacionamento devido à poeira perigosa.',
    'informar_emergencia_area_radio': 'Protocolo de Emergência: Ordene veículo parado, freio de estacionamento, neutro e silêncio no rádio até liberação.',
    'informar_problema_mecanico'    : 'Ordene a parada total, aplicação do freio de estacionamento e desligamento do motor. Confirme que a manutenção será enviada.',
    'informar_falha_critica'        : 'Falha Critica: Ordene a parada imediata, freio de estacionamento e desligamento do motor. Confirme envio de resgate urgente.',
    'informar_emergencia'           : 'Protocolo de Emergência: Ordene veículo parado, freio de estacionamento, neutro e silêncio no rádio até liberação.',
    'informar_condicao_via'         : 'Oriente o operador a reduzir velocidade e manter distância segura. Registre a condição da via.',
    'informar_status_operacional'   : 'Confirme o status recebido e oriente o operador sobre o próximo passo.',
    'confirmar_entendimento'        : 'Confirme brevemente que a CCO recebeu.',
}


class LLMNode(Node):
    def __init__(self):
        super().__init__('llm_node')
        self._historico   = []
        self._lock        = threading.Lock()
        self._processando = False

        self.pub = self.create_publisher(String, '/resposta_bot', 10)
        self.create_subscription(String, '/resposta_rasa', self._cb, 10)
        self.get_logger().info(f'No Ollama iniciado ({MODELO_LLM}). Aguardando em /resposta_rasa...')

    def _cb(self, msg: String):
        with self._lock:
            if self._processando:
                self.get_logger().warn('Mensagem ignorada: LLM ja esta gerando uma resposta.')
                return
            self._processando = True

        try:
            dados          = json.loads(msg.data)
            texto_original = dados.get('texto_original', '')
            intencao       = dados.get('intencao', '')
            entidades      = dados.get('entidades', [])
            evento         = dados.get('evento', {})

            threading.Thread(
                target=self._gerar_resposta,
                args=(texto_original, intencao, entidades, evento),
                daemon=True,
            ).start()

        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON invalido: {e}')
            with self._lock:
                self._processando = False

    def _gerar_resposta(self, texto_original: str, intencao: str, entidades: list, evento: dict):
        try:
            ents_str     = ', '.join(f"{e.get('valor')}" for e in entidades) if entidades else 'nenhum detalhe especifico'
            instrucao    = GUIA_DE_ACOES.get(intencao, 'Responda ao que o motorista disse de forma breve.')
            contexto_evento = self._montar_contexto_evento(evento)

            prompt_llm = (
                f"{contexto_evento}"
                f"O motorista informou: '{texto_original}' (Detalhes: {ents_str})\n"
                f"Sua tarefa: {instrucao}\n"
                "Escreva agora a sua resposta para o radio:"
            )

            with self._lock:
                self._historico.append({'role': 'user', 'content': prompt_llm})
                if len(self._historico) > MAX_HISTORICO * 2:
                    self._historico[:] = self._historico[-(MAX_HISTORICO * 2):]
                historico_snapshot = list(self._historico)

            stream = ollama.chat(
                model=MODELO_LLM,
                messages=[{'role': 'system', 'content': SYSTEM_PROMPT}, *historico_snapshot],
                stream=True,
                keep_alive=-1,
                options={
                    # 'num_gpu' removido: sem esse limite, o Ollama usa a GPU
                    # automaticamente quando disponível (senão cai para CPU).
                    'temperature': 0.1,
                    'num_predict': 48,
                    'num_ctx'    : 512,
                    'stop'       : ['\n', 'Motorista:', 'CCO:', 'Sua tarefa:']
                }
            )

            texto_completo = self._processar_stream(stream)

            if texto_completo:
                with self._lock:
                    self._historico.append({'role': 'assistant', 'content': texto_completo})
            else:
                self.get_logger().warn('[LLM] Resposta vazia.')

        except Exception as e:
            self.get_logger().error(f'Erro ao consultar o LLM: {e}')
        finally:
            with self._lock:
                self._processando = False

    def _processar_stream(self, stream) -> str:
        """Consome os tokens do Ollama e publica cada sentença assim que ela
        é fechada (., ! ou ?), em vez de esperar a resposta completa.
        Retorna o texto integral acumulado, para manter o histórico."""
        buffer = ''
        texto_completo = ''

        for chunk in stream:
            pedaco = chunk.get('message', {}).get('content', '')
            if not pedaco:
                continue
            buffer += pedaco

            while True:
                fim = re.search(r'[.!?]', buffer)
                if not fim:
                    break
                sentenca = buffer[:fim.end()].replace('"', '').strip()
                buffer = buffer[fim.end():]
                if sentenca:
                    self.get_logger().info(f'[LLM] Sentenca (streaming): "{sentenca}"')
                    texto_completo = f'{texto_completo} {sentenca}'.strip()
                    self._publicar_resposta(sentenca, streaming=True)

        restante = buffer.replace('"', '').strip()
        if restante:
            self.get_logger().info(f'[LLM] Sentenca final: "{restante}"')
            texto_completo = f'{texto_completo} {restante}'.strip()
            self._publicar_resposta(restante, streaming=True)

        return texto_completo

    def _montar_contexto_evento(self, evento: dict) -> str:
        if not evento:
            return ''
        return (
            f"Contexto do evento ativo na simulacao:\n"
            f"- Evento: {evento.get('Nome', '')}\n"
            f"- Situacao: {evento.get('Estimulo', '')}\n"
            f"- Criterios esperados: {evento.get('Criterios', '')}\n\n"
        )

    def _publicar_resposta(self, texto: str, streaming: bool = False):
        payload  = {'respostas': [texto], 'streaming': streaming}
        out      = String()
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
