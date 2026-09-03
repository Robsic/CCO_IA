# CCO-IA — Central de Comando Inteligente para Mineração

> Sistema de comunicação por voz em tempo real para operadores de equipamentos pesados de mineração, utilizando reconhecimento de fala offline, NLU com Rasa, **validação cruzada com eventos do simulador (SirvSimulator)** e geração de resposta via LLM local (Ollama), com síntese de voz neural offline via **Piper**.

---

## 📋 Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Fluxo de Comunicação (Tópicos ROS 2)](#fluxo-de-comunicação-ros-2)
- [Validação de Eventos (Correlação Fala ↔ Simulador)](#validação-de-eventos-correlação-fala--simulador)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração do Rasa](#configuração-do-rasa)
- [Execução](#execução)
- [Testes Automatizados](#testes-automatizados)
- [Intenções Suportadas](#intenções-suportadas)
- [Estrutura dos Arquivos](#estrutura-dos-arquivos)
- [Variáveis e Parâmetros Configuráveis](#variáveis-e-parâmetros-configuráveis)
- [Troubleshooting](#troubleshooting)

---

## Visão Geral

O **CCO-IA** é um sistema embarcado de assistência inteligente à operação de caminhões de mineração. Ele funciona como uma **Central de Comando Operacional (CCO) virtual**, capaz de:

1. **Escutar** o motorista via rádio (PTT — Push-to-Talk)
2. **Reconhecer** a fala offline, sem conexão com internet
3. **Correlacionar** a fala com o evento ativo simulado no ambiente (SirvSimulator), descartando falas incoerentes com a situação
4. **Classificar** a intenção e extrair entidades relevantes (local, componente, carga, sintoma, etc.)
5. **Gerar** uma resposta natural, profissional e contextualizada via LLM local
6. **Falar** a resposta ao motorista usando síntese de voz neural offline

Todo o processamento ocorre **100% localmente**, sem nenhuma dependência de serviços em nuvem.

---

## Arquitetura do Sistema

```
[Microfone / Rádio PTT]                            [Simulador SirvSimulator]
        │                                                       │
        │ /botao_acionado                    /detected_events   │
        └──────────────────┐                 ┌────────────────────┘
                            ▼                 ▼
                     ┌─────────────────────────────┐
                     │          No_Vosk.py          │
                     │  Vosk STT + filtro de evento │
                     │  (whitelist EVENTOS_PERMITIDOS│
                     │   aplicada internamente)     │
                     └─────────────────────────────┘
                                    │
                       /fala_reconhecida (fala + evento)
                                    │
                                    ▼
                     ┌─────────────────────────────┐
                     │          No_Rasa.py          │
                     │  Rasa NLU + valida coerência │
                     │      fala ↔ evento ativo     │
                     └─────────────────────────────┘
                          │                     │
                     Coerente               Incoerente
                          │                     │
                          ▼                     │
                 /resposta_rasa                 │
               (JSON NLU + evento)               │
                          │                     │
                          ▼                     │
                 ┌─────────────────┐            │
                 │    No_LLM.py    │            │
                 │  Ollama, resposta            │
                 │  em streaming por sentença    │
                 └─────────────────┘            │
                          │                     │
                          ▼                     ▼
                     /resposta_bot  ◀────────────┘
              (1 sentença por vez, em streaming,
               ou 1 mensagem de erro se incoerente)
                          │
                          ▼
                 ┌─────────────────┐
                 │    No_Fala.py   │
                 │   Piper TTS     │
                 └─────────────────┘
                          │
                          ▼
                   [Alto-falante]
```

O sistema é composto por **4 nós ROS 2** independentes que se comunicam exclusivamente via tópicos:

| Nó | Arquivo | Função |
|---|---|---|
| `vosk_node` | `No_Vosk.py` | Reconhecimento de voz (Speech-to-Text) com controle PTT e captura do evento ativo do simulador |
| `rasa_node` | `No_Rasa.py` | Classificação de intenção, extração de entidades (NLU) e validação de coerência fala ↔ evento |
| `llm_node` | `No_LLM.py` | Geração de resposta contextualizada via Ollama, usando o evento ativo como contexto adicional do prompt |
| `fala_node` | `No_Fala.py` | Síntese de voz neural offline (Text-to-Speech) com **Piper** |

---

## Fluxo de Comunicação ROS 2

| Tópico | Tipo | Publicado por | Consumido por | Conteúdo |
|---|---|---|---|---|
| `/botao_acionado` | `Int8` | Hardware externo | `vosk_node` | `1` = PTT pressionado, `0` = solto |
| `/detected_events` | `sirv_msgs/CAT793FEvents` | Simulador (SirvSimulator) | `vosk_node` | Evento ativo simulado (código e status) |
| `/fala_reconhecida` | `String` (JSON) | `vosk_node` | `rasa_node` | Texto transcrito da fala + evento ativo no momento da fala |
| `/resposta_rasa` | `String` (JSON) | `rasa_node` | `llm_node` | Intenção, confiança, entidades e evento associado |
| `/resposta_bot` | `String` (JSON) | `llm_node` (ou `rasa_node`, em caso de erro de coerência) | `fala_node` | Sentenças geradas para o TTS (streaming) |

> Falas só são publicadas em `/fala_reconhecida` quando há um evento ativo reconhecido (`evento_ativo` não vazio) — ver [Validação de Eventos](#validação-de-eventos-correlação-fala--simulador).

### Exemplo de payload `/fala_reconhecida`

```json
{
  "fala": "temperatura do motor muito alta",
  "evento": { "id": 8, "status": "IN_PROGRESS", "Nome": "Evento CAT 8" }
}
```

### Exemplo de payload `/resposta_rasa`

```json
{
  "texto_original": "temperatura do motor muito alta",
  "intencao": "informar_problema_mecanico",
  "confianca": 0.9731,
  "entidades": [
    { "entidade": "componente", "valor": "motor" }
  ],
  "evento": { "id": 8, "status": "IN_PROGRESS", "Nome": "Evento CAT 8" }
}
```

### Exemplo de payload `/resposta_bot`

```json
{
  "respostas": ["A oficina foi notificada sobre o superaquecimento do motor."],
  "streaming": false
}
```

> Quando a intenção reconhecida não é compatível com o evento ativo, `rasa_node` publica diretamente em `/resposta_bot` uma resposta padrão de inconsistência (ex.: *"Sua fala não foi condizente com a realidade."*), sem passar pelo `llm_node`.

---

## Validação de Eventos (Correlação Fala ↔ Simulador)

Nesta versão, o sistema deixou de reagir apenas ao conteúdo da fala: ele **valida se o que o motorista disse é coerente com o evento simulado ativo no momento**, em duas camadas:

### 1. Filtro de eventos permitidos (`No_Vosk.py`)

O nó Vosk assina `/detected_events` (mensagens `sirv_msgs/msg/CAT793FEvents`) e mantém apenas o evento mais recente em `self.evento_ativo`. Eventos cujo `code` não esteja na whitelist `EVENTOS_PERMITIDOS` são descartados (evento ativo é limpo). **Se não houver evento ativo permitido no momento em que o PTT é solto, a fala não é publicada** em `/fala_reconhecida`.

### 2. Coerência intenção ↔ evento (`No_Rasa.py`)

Após a classificação NLU, o nó Rasa verifica se a `intencao` reconhecida está no conjunto de intenções esperadas para o `evento.id` ativo, de acordo com o dicionário `EVENTO_INTENCOES` (ex.: evento `35` = *fogo no motor* → espera `informar_emergencia_incendio` ou `informar_emergencia`; evento `44`–`47` = *ultrapassagem* → espera `solicitar_ultrapassagem`).

- Se a intenção **é** compatível com o evento → segue normalmente para `llm_node` via `/resposta_rasa`.
- Se a intenção **não é** compatível → o fluxo é interrompido e uma resposta de inconsistência é publicada direto em `/resposta_bot`, sem chamar o LLM.

> Essa dupla validação existe para o cenário de treinamento/simulação: garante que a resposta da CCO só é gerada quando a fala do operador realmente corresponde ao evento que está sendo simulado no CAT793F.

---

## Pré-requisitos

### Sistema Operacional
- Ubuntu 22.04 ou superior (testado)
- ROS 2 Jazzy (nós testados e executados sobre `/opt/ros/jazzy`)

### ⚠️ Dois ambientes Python separados

O projeto usa **dois intérpretes Python distintos** por incompatibilidade de dependências:

| Ambiente | Versão | Usado por |
|---|---|---|
| **venv Rasa** | Python **3.10** | `No_Rasa.py` (cliente HTTP) + servidor Rasa NLU |
| **Sistema / ROS 2** | Python **3.12** | `No_Vosk.py`, `No_LLM.py`, `No_Fala.py` |

> O Rasa e suas dependências (spaCy, TensorFlow) exigem Python 3.10. Os demais nós rodam no Python 3.12 do sistema junto ao ROS 2.

### Pacote ROS 2 externo

| Componente | Repositório | Uso |
|---|---|---|
| **sirv_msgs** | [SirvSimulator](https://github.com/) (workspace do simulador CAT793F) | Define a mensagem `CAT793FEvents`, consumida por `vosk_node` no tópico `/detected_events`. Precisa estar buildado e ter seu `install/setup.bash` sourceado antes de rodar os nós. |

### Modelos e ferramentas externas

| Componente | Ambiente | Instalação |
|---|---|---|
| **Vosk** (STT) | Python 3.12 | `pip install vosk` + baixar modelo (ver abaixo) |
| **Rasa** (NLU) | Python 3.10 (venv) | `pip install rasa` |
| **spaCy** (pipeline Rasa) | Python 3.10 (venv) | `pip install spacy && python -m spacy download pt_core_news_sm` |
| **Ollama** (LLM) | Python 3.12 | Instale em [ollama.com](https://ollama.com) e rode `ollama pull llama3.2:1b` |
| **Piper** (TTS) | Python 3.12 | `pip install piper-tts` + baixar modelo de voz `pt_BR-faber-medium` (ONNX) |

> A versão anterior usava Silero TTS (baixado via PyTorch Hub). Esta versão substitui o motor de voz por **Piper**, eliminando a dependência de `torch`/`torchaudio` nos nós.

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

### 2. Garanta que o pacote `sirv_msgs` está disponível

```bash
# Exemplo, ajuste o caminho conforme o seu workspace do simulador
cd ~/codigos/SirvSimulator
colcon build --packages-select sirv_msgs
source install/setup.bash
```

> Esse pacote precisa ser sourceado em **todo terminal** que for rodar `No_Vosk.py` ou `testar_eventos.sh`, pois define o tipo de mensagem `CAT793FEvents`.

### 3. Instale as dependências no Python 3.12 (sistema)

Essas dependências são para os nós Vosk, LLM e Fala:

```bash
pip3.12 install sounddevice vosk requests ollama piper-tts numpy
```

### 4. Crie o ambiente virtual Python 3.10 para o Rasa

```bash
# Crie e ative o venv
python3.10 -m venv ~/venvs/rasa_env
source ~/venvs/rasa_env/bin/activate

# Instale o Rasa e o modelo de linguagem
pip install rasa
pip install spacy
python -m spacy download pt_core_news_sm

deactivate
```

### 5. Baixe o modelo Vosk

```bash
cd ~/ros2_ws/src/cco_ia
wget https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip
unzip vosk-model-small-pt-0.3.zip
```

### 6. Baixe o modelo de voz Piper

```bash
mkdir -p ~/piper_voices && cd ~/piper_voices
# Baixe pt_BR-faber-medium.onnx e pt_BR-faber-medium.onnx.json
# (disponíveis em https://github.com/rhasspy/piper/releases ou huggingface.co/rhasspy/piper-voices)
```

> Ajuste `MODELO_ONNX`, `MODELO_CONFIG` e `ARQUIVO_AUDIO` em `No_Fala.py` para o caminho onde os arquivos foram salvos.

### 7. Configure o Ollama e baixe o modelo LLM

```bash
# Instale o Ollama (seguir instruções em ollama.com)
ollama pull llama3.2:1b
```

---

## Configuração do Rasa

Os arquivos de configuração Rasa estão na raiz do projeto:

| Arquivo | Propósito |
|---|---|
| `config.yml` | Pipeline NLU (spaCy + DIET + `ResponseSelector` + `FallbackClassifier` com threshold 0.8) |
| `domain.yml` | Intenções, entidades e slots reconhecidos |
| `data/nlu.yml` | Exemplos de treinamento para cada intenção |
| `endpoints.yml` | Endpoints externos (action server, tracker store) |
| `credentials.yml` | Canais de comunicação do Rasa |

### Treinar e iniciar o servidor Rasa NLU

O Rasa deve ser executado **sempre dentro do venv Python 3.10**:

```bash
cd ~/ros2_ws/src/cco_ia

# Ative o ambiente virtual do Rasa
source ~/venvs/rasa_env/bin/activate

# Treinar o modelo NLU (necessário após qualquer alteração em data/nlu.yml)
rasa train nlu

# Iniciar o servidor NLU na porta 5005
rasa run --enable-api --port 5005

# Deixe este terminal aberto — o servidor precisa ficar rodando
```

> O nó `No_Rasa.py` consome a API REST em `http://localhost:5005/model/parse`.

---

## Execução

#### Terminal 1 — Servidor Rasa NLU (Python 3.10 — venv)

```bash
cd ~/ros2_ws/src/cco_ia
source ~/venvs/rasa_env/bin/activate
rasa run --enable-api
```

> Deixe este terminal aberto. O servidor precisa ficar rodando enquanto os nós estiverem ativos.

#### Terminal 2 — Todos os nós do sistema (Python 3.12 — ROS 2 Jazzy)

```bash
cd ~/ros2_ws/src/cco_ia
source /opt/ros/jazzy/setup.bash
source ~/codigos/SirvSimulator/install/setup.bash   # necessário para sirv_msgs
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

## Testes Automatizados

O script `testar_eventos.sh` executa uma bateria automatizada cobrindo os eventos simulados suportados (whitelist de `EVENTOS_PERMITIDOS`). Para cada evento, o script:

1. Publica o evento em `/detected_events` no formato `sirv_msgs/msg/CAT793FEvents`;
2. Aciona o PTT (`/botao_acionado` = `1`) e aguarda ~7s para a fala do operador;
3. Solta o PTT (`/botao_acionado` = `0`), disparando o processamento da fala capturada;
4. Aguarda a resposta da CCO antes de seguir para o próximo evento.

```bash
cd ~/ros2_ws/src/cco_ia
source /opt/ros/jazzy/setup.bash
source ~/codigos/SirvSimulator/install/setup.bash
./testar_eventos.sh
```

> Requer que os 4 nós (`No_Vosk.py`, `No_Rasa.py`, `No_LLM.py`, `No_Fala.py`) e o servidor Rasa já estejam em execução em outros terminais. Durante a janela de 7 segundos de cada evento, fale algo coerente com o evento anunciado no terminal para validar o reconhecimento e a correlação fala↔evento.

---

## Intenções Suportadas

As intenções abaixo são as atualmente **permitidas** pelo sistema — cada uma corresponde a uma entrada em `GUIA_DE_ACOES` (`No_LLM.py`), que instrui o LLM sobre como a CCO deve agir ao recebê-la:

| Intenção | Exemplos de fala | Ação da CCO |
|---|---|---|
| `saudacao_radio` | "QAP", "CCO na escuta?", "rádio teste" | Responde brevemente que a CCO está em QAP (na escuta) e pronta para apoiar |
| `solicitar_ultrapassagem` | "posso passar o caminhão parado?" | Orienta o operador a fazer contato de rádio com o veículo à frente e aguardar permissão antes de ultrapassar |
| `informar_veiculo_leve_proximo` | "veículo leve muito próximo", "carro leve colado em mim" | Alerta: orienta o operador a não se aproximar a menos de 10 metros do veículo leve |
| `informar_parada_abrupta_frente` | "caminhão à frente parou de repente" | Orienta o operador a manter distância segura, selecionar neutro e aplicar o freio de estacionamento |
| `informar_falha_mecanica_eletrica` | "pane elétrica no painel", "falha mecânica geral" | Ordena a parada total, aplicação do freio de estacionamento e desligamento do motor; confirma envio da manutenção |
| `informar_falha_freio_direcao` | "perdi o freio", "falha na direção" | Falha crítica: ordena parada imediata, freio de estacionamento e desligamento do motor; confirma envio de resgate urgente |
| `informar_superaquecimento` | "motor superaquecendo", "temperatura do motor muito alta" | Orienta a parar, selecionar neutro e aumentar o RPM acima de 1200 por mais de 5 segundos para resfriamento |
| `informar_emergencia_incendio` | "fogo no motor", "princípio de incêndio" | Comando crítico: ordena parada total, freio de estacionamento, corte do motor e acionamento do sistema de supressão de incêndio |
| `informar_baixa_visibilidade_poeira` | "muita poeira, visibilidade ruim" | Orienta a parar, engatar neutro e aplicar freio de estacionamento devido à poeira perigosa |
| `informar_emergencia_area_radio` | "emergência na área, silêncio no rádio" | Protocolo de emergência: ordena veículo parado, freio de estacionamento, neutro e silêncio no rádio até liberação |
| `informar_problema_mecanico` | "pneu dianteiro furou", "temperatura do motor alta" | Ordena a parada total, aplicação do freio de estacionamento e desligamento do motor; confirma envio da manutenção |
| `informar_falha_critica` | "freio de serviço não responde" | Falha crítica: ordena parada imediata, freio de estacionamento e desligamento do motor; confirma envio de resgate urgente |
| `informar_emergencia` | "emergência emergência", "tombamento na rampa" | Protocolo de emergência: ordena veículo parado, freio de estacionamento, neutro e silêncio no rádio até liberação |
| `informar_condicao_via` | "excesso de poeira, visibilidade ruim" | Orienta o operador a reduzir velocidade e manter distância segura; registra a condição da via |
| `informar_status_operacional` | "caminhão cheio", "iniciando turno" | Confirma o status recebido e orienta o operador sobre o próximo passo |
| `confirmar_entendimento` | "copiado", "afirmativo", "entendido central" | Confirma brevemente que a CCO recebeu |

> Intenções fora dessa lista caem no fallback genérico do LLM (*"Responda ao que o motorista disse de forma breve"*), sem uma instrução dedicada em `GUIA_DE_ACOES`.

> ⚠️ **Atenção:** `informar_veiculo_leve_proximo`, `informar_parada_abrupta_frente`, `informar_falha_mecanica_eletrica`, `informar_falha_freio_direcao`, `informar_superaquecimento`, `informar_baixa_visibilidade_poeira` e `informar_emergencia_area_radio` ainda **não existem** em `domain.yml`/`data/nlu.yml` nem em `EVENTO_INTENCOES` (`No_Rasa.py`). Enquanto isso não for adicionado, o Rasa não conseguirá classificar a fala nessas intenções — elas precisam ser treinadas e mapeadas a eventos para funcionar de ponta a ponta. Da mesma forma, `solicitar_basculamento`, `solicitar_carregamento`, `solicitar_abastecimento`, `informar_condicao_climatica` e `solicitar_apoio_pista` continuam definidas em `domain.yml`/NLU, mas não têm mais uma entrada em `GUIA_DE_ACOES`.

> Cada intenção pode estar associada a um ou mais códigos de evento simulado através do dicionário `EVENTO_INTENCOES` em `No_Rasa.py` — ver [Validação de Eventos](#validação-de-eventos-correlação-fala--simulador).

### Entidades extraídas

| Entidade | Exemplos |
|---|---|
| `local` | britador 1, escavadeira 5, frente de lavra, pilha de estéril |
| `componente` | motor, pneu, suspensão, bateria, filtro de combustível |
| `carga` | minério, carvão |
| `status_carga` | cheio, vazio |
| `veiculo` | caminhão, motoniveladora, veículo leve, caminhão pipa |
| `id_equipamento` | zero cinco, caminhão 12 |
| `operador` | nome ou identificação do operador |
| `sintoma` | perdendo força, fervendo, batendo muito, chiado |
| `nivel_medida` | subiu demais, muito baixo |
| `condicao_ambiental` | chuva forte, neblina densa |
| `obstaculo_via` | poeira, buraco |
| `tempo` | agora, em 5 minutos |
| `prioridade` | emergência, urgente |

---

## Estrutura dos Arquivos

```
cco_ia/
├── No_Vosk.py          # Nó STT — Vosk com PTT + captura do evento ativo (/detected_events)
├── No_Rasa.py          # Nó NLU — cliente da API Rasa + validação de coerência fala↔evento
├── No_LLM.py           # Nó LLM — streaming via Ollama, com contexto do evento ativo
├── No_Fala.py          # Nó TTS — Piper neural offline
├── testar_eventos.sh   # Script de teste automatizado ponta a ponta por evento
├── config.yml          # Pipeline de NLU do Rasa
├── domain.yml          # Domínio: intenções, entidades, slots
├── data/nlu.yml         # Dados de treinamento NLU
├── endpoints.yml       # Endpoints externos Rasa
├── credentials.yml     # Canais do Rasa
└── README.md
```

---

## Variáveis e Parâmetros Configuráveis

### `No_Vosk.py`

| Variável | Padrão | Descrição |
|---|---|---|
| `_SAMPLE_RATE` | `16000` | Taxa de amostragem do microfone (Hz) |
| `_BLOCK_SIZE` | `4000` | Tamanho do bloco de áudio por callback |
| `EVENTOS_PERMITIDOS` | lista de 31 códigos | Whitelist de eventos do simulador aceitos como contexto válido |

### `No_Rasa.py`

| Variável | Padrão | Descrição |
|---|---|---|
| `URL_NLU` | `http://localhost:5005/model/parse` | Endpoint da API Rasa NLU |
| `TIMEOUT_S` | `30` | Timeout das requisições HTTP (segundos) |
| `DEBOUNCE_S` | `0.6` | Tempo de debounce antes de enviar a fala ao NLU, evitando disparos duplicados |
| `EVENTO_INTENCOES` | dicionário | Mapeia cada código de evento às intenções consideradas coerentes com ele |

### `No_LLM.py`

| Variável | Padrão | Descrição |
|---|---|---|
| `MODELO_LLM` | `llama3.2:1b` | Modelo Ollama utilizado |
| `MAX_HISTORICO` | `1` | Turnos de histórico de conversa mantidos |

### `No_Fala.py`

| Variável | Padrão | Descrição |
|---|---|---|
| `ARQUIVO_AUDIO` | `/home/vrmine-sim/piper_voices/fala.wav` | Caminho para salvar o `.wav` gerado |
| `MODELO_ONNX` | `/home/vrmine-sim/piper_voices/pt_BR-faber-medium.onnx` | Modelo de voz Piper |
| `MODELO_CONFIG` | `/home/vrmine-sim/piper_voices/pt_BR-faber-medium.onnx.json` | Configuração do modelo Piper |
| `CONFIANCA_MINIMA` | `0.80` | Confiança mínima do NLU para sintetizar fala |

### `config.yml` (Rasa)

| Parâmetro | Valor | Descrição |
|---|---|---|
| `FallbackClassifier.threshold` | `0.8` | Confiança mínima para aceitar uma intenção |
| `FallbackClassifier.ambiguity_threshold` | `0.1` | Diferença mínima de confiança entre a intenção top-1 e top-2 para evitar fallback por ambiguidade |
| `DIETClassifier.epochs` | `100` | Épocas de treinamento do classificador |
| `ResponseSelector.epochs` | `100` | Épocas de treinamento do seletor de respostas |

---

## Troubleshooting

**Rasa não responde / timeout**
> Verifique se o servidor Rasa está rodando: `curl http://localhost:5005/status`

**Vosk não reconhece fala**
> Confirme que o diretório `vosk-model-small-pt-0.3/` existe no diretório de trabalho onde o nó é executado.

**Nenhuma fala é publicada mesmo com o PTT solto**
> `No_Vosk.py` só publica em `/fala_reconhecida` se houver um evento ativo permitido em `/detected_events`. Confirme que o simulador está publicando eventos e que o código do evento está na whitelist `EVENTOS_PERMITIDOS`.

**A CCO sempre responde "Sua fala não foi condizente com a realidade"**
> A intenção reconhecida pelo Rasa não está no conjunto de intenções esperadas para o evento ativo (`EVENTO_INTENCOES` em `No_Rasa.py`). Confirme se a fala corresponde ao evento simulado ou ajuste o mapeamento.

**Erro `ModuleNotFoundError: sirv_msgs`**
> O workspace do simulador (SirvSimulator) não foi buildado ou seu `install/setup.bash` não foi sourceado antes de rodar `No_Vosk.py`.

**Piper não carrega o modelo**
> Confirme que os arquivos `.onnx` e `.onnx.json` existem nos caminhos definidos em `MODELO_ONNX` e `MODELO_CONFIG`, e que o pacote `piper-tts` está instalado no Python 3.12.

**Nenhum áudio no alto-falante**
> Verifique o dispositivo de saída padrão com `python -c "import sounddevice as sd; print(sd.query_devices())"` e ajuste conforme necessário.

**LLM lento na primeira resposta**
> O Ollama carrega o modelo na primeira chamada. Use `keep_alive=-1` (já configurado) para manter o modelo em memória e eliminar esse delay nas próximas interações.

---

## Licença

Este projeto foi desenvolvido para uso interno em operações de mineração. Consulte a equipe responsável para informações sobre licenciamento e distribuição.
