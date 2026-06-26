# CCO-IA — Central de Comando Inteligente para Mineração 

> Sistema de comunicação por voz em tempo real para operadores de equipamentos pesados de mineração, utilizando reconhecimento de fala offline, NLU com Rasa e geração de resposta via LLM local (Ollama).

---

## 📋 Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Fluxo de Comunicação (Tópicos ROS 2)](#fluxo-de-comunicação-ros-2)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração do Rasa](#configuração-do-rasa)
- [Execução](#execução)
- [Intenções Suportadas](#intenções-suportadas)
- [Estrutura dos Arquivos](#estrutura-dos-arquivos)
- [Variáveis e Parâmetros Configuráveis](#variáveis-e-parâmetros-configuráveis)
- [Troubleshooting](#troubleshooting)

---

## Visão Geral

O **CCO-IA** é um sistema embarcado de assistência inteligente à operação de caminhões de mineração. Ele funciona como uma **Central de Comando Operacional (CCO) virtual**, capaz de:

1. **Escutar** o motorista via rádio (PTT — Push-to-Talk)
2. **Reconhecer** a fala offline, sem conexão com internet
3. **Classificar** a intenção e extrair entidades relevantes (local, componente, carga, etc.)
4. **Gerar** uma resposta natural e profissional via LLM local
5. **Falar** a resposta ao motorista usando síntese de voz neural offline

Todo o processamento ocorre **100% localmente**, sem nenhuma dependência de serviços em nuvem.

---

## Arquitetura do Sistema

```
[Microfone / Rádio PTT]
        │
        ▼
  ┌─────────────┐     /fala_reconhecida      ┌─────────────┐
  │  No_Vosk.py │ ──────────────────────────▶│ No_Rasa.py  │
  │  (Vosk STT) │                            │ (Rasa NLU)  │
  └─────────────┘                            └─────────────┘
                                                    │
                                         /resposta_rasa (JSON NLU)
                                                    │
                                                    ▼
                                          ┌──────────────────┐
                                          │   No_LLM.py      │
                                          │ (Ollama / LLama) │
                                          └──────────────────┘
                                                    │
                                          /resposta_bot (sentenças)
                                                    │
                                                    ▼
                                          ┌──────────────────┐
                                          │   No_Fala.py     │
                                          │  (Silero TTS)    │
                                          └──────────────────┘
                                                    │
                                                    ▼
                                            [Alto-falante]
```

O sistema é composto por **4 nós ROS 2** independentes que se comunicam exclusivamente via tópicos:

| Nó | Arquivo | Função |
|---|---|---|
| `vosk_node` | `No_Vosk.py` | Reconhecimento de voz (Speech-to-Text) com controle PTT |
| `rasa_node` | `No_Rasa.py` | Classificação de intenção e extração de entidades (NLU) |
| `llm_node` | `No_LLM.py` | Geração de resposta contextualizada via Ollama (streaming) |
| `fala_node` | `No_Fala.py` | Síntese de voz neural offline (Text-to-Speech) |

---

## Fluxo de Comunicação ROS 2

| Tópico | Tipo | Publicado por | Consumido por | Conteúdo |
|---|---|---|---|---|
| `/botao_acionado` | `Int8` | Hardware externo | `vosk_node` | `1` = PTT pressionado, `0` = solto |
| `/fala_reconhecida` | `String` | `vosk_node` | `rasa_node` | Texto transcrito da fala |
| `/resposta_rasa` | `String` | `rasa_node` | `llm_node` | JSON com intenção, confiança e entidades |
| `/resposta_bot` | `String` | `llm_node` | `fala_node` | JSON com sentenças geradas (streaming) |

### Exemplo de payload `/resposta_rasa`

```json
{
  "texto_original": "temperatura do motor muito alta",
  "intencao": "informar_problema_mecanico",
  "confianca": 0.9731,
  "entidades": [
    { "entidade": "componente", "valor": "motor" }
  ]
}
```

### Exemplo de payload `/resposta_bot`

```json
{
  "respostas": ["A oficina foi notificada sobre o superaquecimento do motor."],
  "streaming": false
}
```

---

## Pré-requisitos

### Sistema Operacional
- Ubuntu 24.04 (testado)
- ROS 2 Jazzy

### ⚠️ Dois ambientes Python separados

O projeto usa **dois intérpretes Python distintos** por incompatibilidade de dependências:

| Ambiente | Versão | Usado por |
|---|---|---|
| **venv Rasa** | Python **3.10** | servidor Rasa NLU |
| **Sistema / ROS 2** | Python **3.12** | `No_Rasa.py`, `No_Vosk.py`, `No_LLM.py`, `No_Fala.py` |

> O Rasa e suas dependências (spaCy, TensorFlow) exigem Python 3.10. Os demais nós rodam no Python 3.12 do sistema junto ao ROS 2.

### Modelos e ferramentas externas

| Componente | Ambiente | Instalação |
|---|---|---|
| **Vosk** (STT) | Python 3.12 | `pip install vosk` + baixar modelo (ver abaixo) |
| **Rasa** (NLU) | Python 3.10 (venv) | `pip install rasa` |
| **spaCy** (pipeline Rasa) | Python 3.10 (venv) | `pip install spacy && python -m spacy download pt_core_news_sm` |
| **Ollama** (LLM) | Python 3.12 | Instale em [ollama.com](https://ollama.com) e rode `ollama pull llama3.2:1b` |
| **Silero TTS** | Python 3.12 | Baixado automaticamente pelo PyTorch Hub na primeira execução |

---

## Instalação

### 1. Clone o repositório e configure o ambiente ROS 2

```bash
cd ~/ros2_ws/src
git clone <url-do-repositorio> cco_ia
cd ~/ros2_ws
colcon build --packages-select cco_ia
source install/setup.bash
```

### 2. Instale as dependências no Python 3.12 (sistema)

Essas dependências são para os nós Vosk, LLM e Fala:

```bash
pip3.12 install torch torchaudio sounddevice vosk requests ollama
```

### 3. Crie o ambiente virtual Python 3.10 para o Rasa

```bash
# Crie e ative o venv
python3.10 -m venv ~/rasa_env
source ~/rasa_env/bin/activate

# Instale o Rasa e o modelo de linguagem
pip install rasa
pip install spacy
python -m spacy download pt_core_news_sm

deactivate
```

### 4. Baixe o modelo Vosk

```bash
cd ~/ros2_ws/src/cco_ia
wget https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip
unzip vosk-model-small-pt-0.3.zip
```

### 5. Configure o Ollama e baixe o modelo LLM

```bash
# Instale o Ollama (seguir instruções em ollama.com)
ollama pull llama3.2:1b
```

---

## Configuração do Rasa

Os arquivos de configuração Rasa estão na raiz do projeto:

| Arquivo | Propósito |
|---|---|
| `config.yml` | Pipeline NLU (spaCy + DIET + FallbackClassifier com threshold 0.8) |
| `domain.yml` | Intenções, entidades e slots reconhecidos |
| `nlu.yml` | Exemplos de treinamento para cada intenção |
| `endpoints.yml` | Endpoints externos (action server, tracker store) |
| `credentials.yml` | Canais de comunicação do Rasa |

### Treinar e iniciar o servidor Rasa NLU

O Rasa deve ser executado **sempre dentro do venv Python 3.10**:

```bash
cd ~/ros2_ws/src/cco_ia

# Ative o ambiente virtual do Rasa
source ~/rasa_env/bin/activate

# Treinar o modelo (necessário após qualquer alteração no nlu.yml)
rasa train

# Iniciar o servidor NLU na porta 5005
rasa run --enable-api --port 5005

# Deixe este terminal aberto — o servidor precisa ficar rodando
```

> O nó `No_Rasa.py` consome a API REST em `http://localhost:5005/model/parse`.

---

## Execução

#### Terminal 1 — Servidor Rasa NLU (Python 3.10 — venv)

```bash
cd ~/cco_ia
source rasa_env/bin/activate
rasa run --enable-api
```

> Deixe este terminal aberto. O servidor precisa ficar rodando enquanto os nós estiverem ativos.

#### Terminal 2 — Todos os nós do sistema (Python 3.12 — ROS 2 Jazzy)

```bash
cd ~/cco_ia
source /opt/ros/jazzy/setup.bash
python3 No_Vosk.py &
python3 No_Rasa.py &
python3 No_LLM.py &
python3 No_Fala.py &
wait
```

> O `&` executa cada nó em background. O `wait` mantém o terminal aberto e aguarda todos os processos. Para encerrar tudo, pressione `Ctrl+C`.

Ou utilize um arquivo `launch` para subir tudo de uma vez:

```python
# launch/cco_ia.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(package='cco_ia', executable='vosk_node'),
        Node(package='cco_ia', executable='rasa_node'),
        Node(package='cco_ia', executable='llm_node'),
        Node(package='cco_ia', executable='fala_node'),
    ])
```

```bash
ros2 launch cco_ia cco_ia.launch.py
```

---

## Intenções Suportadas

O modelo Rasa foi treinado para reconhecer as seguintes intenções do motorista:

| Intenção | Exemplos de fala | Ação da CCO |
|---|---|---|
| `saudacao_radio` | "QAP", "CCO na escuta?", "rádio teste" | Confirma presença na escuta |
| `confirmar_entendimento` | "copiado", "afirmativo", "entendido central" | Acusa recebimento |
| `informar_emergencia` | "emergência emergência", "tombamento na rampa" | Ordena parada e protocolo de segurança |
| `informar_emergencia_incendio` | "fogo no motor", "princípio de incêndio" | Protocolo de combate a incêndio |
| `solicitar_basculamento` | "permissão para bascular no britador 1" | Autoriza deslocamento ao ponto de descarga |
| `solicitar_carregamento` | "vazio, indo para a escavadeira 5" | Informa destino de carga |
| `informar_falha_critica` | "perdi o freio", "falha na direção" | Ordena parada imediata |
| `informar_problema_mecanico` | "pneu dianteiro furou", "temperatura do motor alta" | Notifica equipe de manutenção |
| `informar_status_operacional` | "caminhão cheio", "iniciando turno" | Registra status |
| `solicitar_ultrapassagem` | "posso passar o caminhão parado?" | Autoriza ou nega ultrapassagem |
| `informar_condicao_via` | "excesso de poeira, visibilidade ruim" | Registra condição da via |

### Entidades extraídas

| Entidade | Exemplos |
|---|---|
| `local` | britador 1, escavadeira 5, frente de lavra, pilha de estéril |
| `componente` | motor, pneu, suspensão, bateria, filtro de combustível |
| `carga` | minério, carvão |
| `status_carga` | cheio, vazio |
| `veiculo` | caminhão, motoniveladora, veículo leve |

---

## Estrutura dos Arquivos

```
cco_ia/
├── No_Vosk.py          # Nó STT — Vosk com controle PTT agressivo
├── No_Rasa.py          # Nó NLU — cliente da API Rasa
├── No_LLM.py           # Nó LLM — streaming via Ollama
├── No_Fala.py          # Nó TTS — Silero neural offline
├── config.yml          # Pipeline de NLU do Rasa
├── domain.yml          # Domínio: intenções, entidades, slots
├── endpoints.yml       # Endpoints externos Rasa
├── credentials.yml     # Canais do Rasa
├── README.md
└── data/
    └── nlu.yml         # Dados de treinamento NLU
```

---

## Variáveis e Parâmetros Configuráveis

### `No_Vosk.py`

| Variável | Padrão | Descrição |
|---|---|---|
| `_SAMPLE_RATE` | `16000` | Taxa de amostragem do microfone (Hz) |
| `_BLOCK_SIZE` | `4000` | Tamanho do bloco de áudio por callback |

### `No_Rasa.py`

| Variável | Padrão | Descrição |
|---|---|---|
| `URL_NLU` | `http://localhost:5005/model/parse` | Endpoint da API Rasa NLU |
| `TIMEOUT_S` | `5` | Timeout das requisições HTTP (segundos) |

### `No_LLM.py`

| Variável | Padrão | Descrição |
|---|---|---|
| `MODELO_LLM` | `llama3.2:1b` | Modelo Ollama utilizado |
| `MAX_HISTORICO` | `2` | Turnos de histórico de conversa mantidos |

### `No_Fala.py`

| Variável | Padrão | Descrição |
|---|---|---|
| `ARQUIVO_AUDIO` | `/home/giovanna/Downloads/IA/piper_voices/fala.wav` | Caminho para salvar o `.wav` gerado |
| `CONFIANCA_MINIMA` | `0.70` | Confiança mínima do NLU para sintetizar fala |

### `config.yml` (Rasa)

| Parâmetro | Valor | Descrição |
|---|---|---|
| `FallbackClassifier.threshold` | `0.8` | Confiança mínima para aceitar uma intenção |
| `DIETClassifier.epochs` | `100` | Épocas de treinamento do classificador |

---

## Troubleshooting

**Rasa não responde / timeout**
> Verifique se o servidor Rasa está rodando: `curl http://localhost:5005/status`

**Vosk não reconhece fala**
> Confirme que o diretório `vosk-model-small-pt-0.3/` existe no diretório de trabalho onde o nó é executado.

**Silero não carrega o modelo**
> Na primeira execução, o modelo é baixado pelo PyTorch Hub (~60 MB). Certifique-se de ter acesso à internet nessa etapa. Nas execuções seguintes funciona offline (cache em `~/.cache/torch/hub`).

**Nenhum áudio no alto-falante**
> Verifique o dispositivo de saída padrão com `python -c "import sounddevice as sd; print(sd.query_devices())"` e ajuste conforme necessário.

**LLM lento na primeira resposta**
> O Ollama carrega o modelo na primeira chamada. Use `keep_alive=-1` (já configurado) para manter o modelo em memória e eliminar esse delay nas próximas interações.

---

## Licença

Este projeto foi desenvolvido para uso interno em operações de mineração. Consulte a equipe responsável para informações sobre licenciamento e distribuição.
