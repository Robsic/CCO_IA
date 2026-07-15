# CCO-IA — Central de Comando Inteligente para Mineração

> Sistema de comunicação por voz em tempo real para operadores de equipamentos pesados de mineração, utilizando reconhecimento de fala offline, NLU com Rasa (com validação ativa de coerência) e geração de resposta via LLM local (Ollama) e síntese de voz neural via Piper TTS.

---

## 📋 Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Fluxo de Comunicação (Tópicos ROS 2)](#fluxo-de-comunicação-ros-2)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração do Rasa](#configuração-do-rasa)
- [Execução e Testes](#execução-e-testes)
- [Intenções e Entidades Suportadas](#intenções-e-entidades-suportadas)
- [Exemplos de Testes e Eventos Cadastrados](#exemplos-de-testes-e-eventos-cadastrados)
- [Estrutura dos Arquivos](#estrutura-dos-arquivos)
- [Variáveis e Parâmetros Configuráveis](#variáveis-e-parâmetros-configuráveis)
- [Troubleshooting](#troubleshooting)
- [Licença](#licença)

---

## Visão Geral

O **CCO-IA** é um sistema embarcado de assistência inteligente à operação de caminhões de mineração. Ele funciona como uma **Central de Comando Operacional (CCO) virtual**, capaz de:

1. **Escutar** o motorista via rádio (PTT — Push-to-Talk) e associar a fala ao evento ativo no simulador.
2. **Reconhecer** a fala offline, sem qualquer dependência de conexão com a internet.
3. **Classificar** a intenção, verificar a **coerência** com o evento atual do sistema e extrair entidades relevantes (local, componente, carga, etc.).
4. **Gerar** uma resposta natural e profissional via LLM local caso a intenção seja condizente com a situação operacional.
5. **Falar** a resposta contextualizada (ou um alerta sonoro de erro de coerência) ao motorista usando síntese de voz neural offline (Piper TTS).

Todo o processamento ocorre **100% localmente**, garantindo baixa latência e total autonomia em áreas remotas de mineração.

---

## Arquitetura do Sistema

A arquitetura valida a coerência da fala logo no nó do Rasa. Se o relato do operador não fizer sentido com o evento ativo do simulador, o sistema pula a etapa do LLM e envia uma mensagem de erro estruturada diretamente para o nó de fala.

```text
[Microfone / Rádio PTT]      [Supervisório / eventos]
        │                           │
        ▼                           ▼
  ┌───────────────────────────────────┐
  │            No_Vosk.py             │
  │ (Vosk STT: Captura Voz + Evento)  │
  └───────────────────────────────────┘
                  │
          /fala_reconhecida 
        (Texto + ID do Evento)
                  │
                  ▼
  ┌───────────────────────────────────┐
  │            No_Rasa.py             │
  │    (Rasa NLU: Valida Coerência)   │
  └───────────────────────────────────┘
          │                   │
    Coerente (Sim)      Incoerente (Não)
          │                   │
          ▼                   │
   /resposta_rasa             │
    (JSON NLU)                │
          │                   │
          ▼                   │
  ┌───────────────┐           │
  │   No_LLM.py   │           │
  │  (Ollama LLM) │           │
  └───────────────┘           │
          │                   │
          ▼                   ▼
   /resposta_bot <────────────┘
     (Sentenças / Mensagem de Erro)
          │
          ▼
  ┌───────────────┐
  │  No_Fala.py   │
  │  (Piper TTS)  │
  └───────────────┘
          │
          ▼
   [Alto-falante]


```

O sistema é composto por **4 nós ROS 2** independentes que se comunicam exclusivamente via tópicos:

| Nó | Arquivo | Função |
| --- | --- | --- |
| `vosk_node` | `No_Vosk.py` | Reconhecimento de voz (Speech-to-Text) com controle PTT e integração de eventos. |
| `rasa_node` | `No_Rasa.py` | Classificação de intenção, extração de entidades e verificação de coerência entre rádio e simulador. |
| `llm_node` | `No_LLM.py` | Geração de resposta contextualizada via Ollama (acionado apenas para eventos coerentes). |
| `fala_node` | `No_Fala.py` | Síntese de voz neural offline (Text-to-Speech) utilizando Piper TTS. |

---

## Fluxo de Comunicação ROS 2

| Tópico | Tipo | Publicado por | Consumido por | Conteúdo |
| --- | --- | --- | --- | --- |
| `/botao_acionado` | `std_msgs/msg/Int8` | Hardware externo | `vosk_node` | `1` = PTT pressionado, `0` = solto |
| `/eventos` | `std_msgs/msg/String` | Sistema Externo | `vosk_node` | JSON com dados do evento ativo no simulador |
| `/fala_reconhecida` | `std_msgs/msg/String` | `vosk_node` | `rasa_node` | Texto transcrito da fala e o ID do evento atual |
| `/resposta_rasa` | `std_msgs/msg/String` | `rasa_node` | `llm_node` | JSON com intenção, confiança, entidades e validação do evento |
| `/resposta_bot` | `std_msgs/msg/String` | `llm_node` / `rasa_node` | `fala_node` | JSON com as sentenças geradas ou mensagem direta de erro |

### Exemplo de payload `/resposta_rasa` (Fluxo Coerente)

```json
{
  "texto_original": "temperatura do motor muito alta",
  "intencao": "informar_problema_mecanico",
  "confianca": 0.9731,
  "entidades": [
    { "entidade": "componente", "valor": "motor" }
  ],
  "id_evento_ativo": 35,
  "coerente": true
}


```

### Exemplo de payload `/resposta_bot`

```json
{
  "respostas": ["A central CCO copiou a sua mensagem. Por favor, estacione em local seguro, desligue o motor e aguarde a equipe de manutenção."],
  "streaming": false
}


```

---

## Pré-requisitos

### Sistema Operacional

* Ubuntu 24.04 (testado e homologado)
* ROS 2 Jazzy Jalisco

### ⚠️ Dois ambientes Python separados

Devido a severas incompatibilidades de dependências de bibliotecas de IA, o projeto exige dois ambientes de execução distintos:

| Ambiente | Versão | Usado por |
| --- | --- | --- |
| **venv Rasa** | Python **3.10** | Servidor de backend do Rasa NLU |
| **Sistema / ROS 2** | Python **3.12** | `No_Rasa.py`, `No_Vosk.py`, `No_LLM.py`, `No_Fala.py` |

> *Nota: O Rasa e suas dependências internas (como spaCy e TensorFlow) exigem estritamente o Python 3.10. Os nós do ecossistema ROS 2 rodam nativamente no Python 3.12 do sistema.*

### Modelos e ferramentas externas

| Componente | Ambiente | Instalação |
| --- | --- | --- |
| **Vosk** (STT) | Python 3.12 | `pip install vosk` + baixar modelo acústico em português |
| **Rasa** (NLU) | Python 3.10 (venv) | `pip install rasa` |
| **spaCy** (pipeline Rasa) | Python 3.10 (venv) | `pip install spacy && python -m spacy download pt_core_news_sm` |
| **Ollama** (LLM) | Python 3.12 | Instalar via terminal e executar `ollama pull llama3.2:1b` |
| **Piper TTS** | Python 3.12 | Baixar o executável e o modelo `.onnx` correspondente ao pt-BR offline |

---

## Instalação

### 1. Configurar o diretório base do projeto

```bash
mkdir -p ~/cco_ia
cd ~/cco_ia
# Clone ou mova os arquivos do repositório para esta pasta


```

### 2. Instalar dependências no Python 3.12 (Sistema/ROS 2)

Estas bibliotecas darão suporte aos nós do Vosk, do cliente Rasa, do Ollama e do Piper:

```bash
pip3 install torch torchaudio sounddevice vosk requests ollama


```

### 3. Criar e configurar o Ambiente Virtual (Python 3.10) para o Rasa

```bash
# Cria o venv apontando para o interpretador Python 3.10
python3.10 -m venv rasa_env
source rasa_env/bin/activate

# Instala o Rasa, o spaCy e o modelo de linguagem do português
pip install --upgrade pip
pip install rasa
pip install spacy
python -m spacy download pt_core_news_sm

deactivate


```

### 4. Baixar o Modelo Acústico Offline do Vosk

```bash
cd ~/cco_ia
wget [https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip](https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip)
unzip vosk-model-small-pt-0.3.zip


```

### 5. Instalar o Ollama e baixar o Modelo LLM

Siga o guia de instalação oficial em [ollama.com](https://ollama.com) e depois execute no seu terminal:

```bash
ollama pull llama3.2:1b


```

### 6. Configurar as vozes do Piper TTS

Baixe os arquivos de modelo de voz `.onnx` e o respectivo `.onnx.json` para português do repositório oficial do Piper e aponte o diretório no arquivo `No_Fala.py` (Exemplo padrão: `/home/giovanna/Downloads/IA/piper_voices/`).

---

## Configuração do Rasa

Os arquivos estruturais do Rasa estão localizados na raiz do projeto:

| Arquivo | Propósito |
| --- | --- |
| `config.yml` | Configuração da pipeline de NLU (spaCy + DIETClassifier + FallbackClassifier com threshold 0.8) |
| `domain.yml` | Registro das intenções (`intents`), entidades (`entities`) e slots mapeados |
| `data/nlu.yml` | Massa de dados e frases de exemplo utilizadas para o treinamento da IA |
| `endpoints.yml` | Definição de endpoints externos adicionais (action server, etc.) |
| `credentials.yml` | Configuração de canais adicionais de entrada/saída |

### Treinar o Modelo Rasa NLU

Sempre que fizer alterações nos exemplos contidos em `data/nlu.yml`, você deve treinar novamente a rede do Rasa. Lembre-se de fazer isso **dentro do ambiente virtual**:

```bash
cd ~/cco_ia
source rasa_env/bin/activate
rasa train
deactivate


```

---

## Execução e Testes

Antes de iniciar qualquer teste, é fundamental garantir que não existam processos antigos travando o microfone, as portas ou a memória.

#### Passo 0 — Limpar processos em background

Abra o terminal e force a parada de qualquer processo Python concorrente que tenha ficado aberto sem você saber:

```bash
pkill -f python3


```

#### Terminal 1 — Iniciar Servidor Rasa NLU (Python 3.10 — venv)

```bash
cd ~/cco_ia
source rasa_env/bin/activate
rasa run --enable-api


```

> *Deixe este terminal aberto. O servidor precisa estar ativo para responder às requisições HTTP.*

#### Terminal 2 — Inicializar os Nós ROS 2 (Python 3.12 — ROS 2 Jazzy)

```bash
cd ~/cco_ia
source /opt/ros/jazzy/setup.bash
python3 No_Vosk.py &
python3 No_Rasa.py &
python3 No_LLM.py &
python3 No_Fala.py &
wait


```

> *O caractere `&` joga a execução de cada nó para o background e o comando `wait` segura o terminal ativo. Pressione `Ctrl+C` para encerrar todos de uma vez.*

#### Terminal 3 — Simular o acionamento do Rádio (Botão PTT) e Simulação de Eventos

Para validar o fluxo, envie um evento ativo para o sistema e simule os comandos do botão de rádio, execute um comando por vez:

```bash
cd ~/cco_ia
source /opt/ros/jazzy/setup.bash

# 1. Simula a ocorrência de um evento do supervisório
ros2 topic pub --once /eventos std_msgs/msg/String "{data: '{\"id\": 00, \"nome\": \"Nome do evento\"}'}"

# 2. Pressiona o botão PTT (Inicia captação de áudio pelo microfone)
ros2 topic pub --once /botao_acionado std_msgs/msg/Int8 "{data: 1}"

# 3. [Fale ao microfone neste momento]

# 4. Solta o botão PTT (Envia o áudio gravado para a pipeline de análise)
ros2 topic pub --once /botao_acionado std_msgs/msg/Int8 "{data: 0}"


```

Abaixo estão exemplos prontos com **eventos habilitados** para testar o sistema:

**Exemplo A: Testando o evento "Fogo no Motor" (ID 35)**

```bash
# 1. Ativa o evento no sistema
ros2 topic pub --once /eventos std_msgs/msg/String "{data: '{\"id\": 35, \"nome\": \"Fogo no motor\"}'}"

# 2. Pressiona o botão PTT (Inicia captação de áudio)
ros2 topic pub --once /botao_acionado std_msgs/msg/Int8 "{data: 1}"

# 3. ---> FALE NO MICROFONE: "CCO, emergência, fogo no motor!" <---

# 4. Solta o botão PTT (Envia o áudio gravado para análise)
ros2 topic pub --once /botao_acionado std_msgs/msg/Int8 "{data: 0}"


```

**Exemplo B: Testando o evento "Falha na Direção" (ID 27)**

```bash
# 1. Ativa o evento no sistema
ros2 topic pub --once /eventos std_msgs/msg/String "{data: '{\"id\": 27, \"nome\": \"Falha na direção\"}'}"

# 2. Pressiona o botão PTT
ros2 topic pub --once /botao_acionado std_msgs/msg/Int8 "{data: 1}"

# 3. ---> FALE NO MICROFONE: "Central, perdi a direção do caminhão." <---

# 4. Solta o botão PTT
ros2 topic pub --once /botao_acionado std_msgs/msg/Int8 "{data: 0}"


```

**Exemplo C: Testando o evento "Nível de combustível baixo" (ID 10)**

```bash
# 1. Ativa o evento no sistema
ros2 topic pub --once /eventos std_msgs/msg/String "{data: '{\"id\": 10, \"nome\": \"Nível de combustível baixo\"}'}"

# 2. Pressiona o botão PTT
ros2 topic pub --once /botao_acionado std_msgs/msg/Int8 "{data: 1}"

# 3. ---> FALE NO MICROFONE: "Estou ficando sem diesel na rampa." <---

# 4. Solta o botão PTT
ros2 topic pub --once /botao_acionado std_msgs/msg/Int8 "{data: 0}"


```

---

## Intenções e Entidades Suportadas

### 1. Intenções Mapeadas (Rasa NLU)

O modelo foi treinado para identificar com precisão as seguintes intenções contidas na fala dos motoristas:

| Intenção | Exemplos de fala | Ação da CCO |
| --- | --- | --- |
| `saudacao_radio` | "QAP", "CCO na escuta?", "rádio teste" | Confirma a presença na escuta |
| `confirmar_entendimento` | "copiado", "afirmativo", "entendido central" | Acusa o recebimento de ordens |
| `informar_emergencia` | "emergência emergência", "tombamento na rampa" | Ordena a parada imediata e aciona protocolos |
| `informar_emergencia_incendio` | "fogo no motor", "princípio de incêndio" | Aciona o protocolo de combate a incêndios |
| `solicitar_basculamento` | "permissão para bascular no britador 1" | Autoriza ou nega o deslocamento à área de descarga |
| `solicitar_carregamento` | "vazio, indo para a escavadeira 5" | Registra o destino para nova carga |
| `informar_falha_critica` | "perdi o freio", "falha na direção" | Emite alertas críticos de parada imediata |
| `informar_problema_mecanico` | "pneu dianteiro furou", "temperatura do motor alta" | Abre ordem de serviço automotiva e notifica a manutenção |
| `informar_status_operacional` | "caminhão cheio", "iniciando turno" | Atualiza o status do veículo no sistema de despacho |
| `solicitar_ultrapassagem` | "posso passar o caminhão parado?" | Autoriza ou nega a manobra na pista |
| `informar_condicao_via` | "excesso de poeira, visibilidade ruim" | Registra o estado da infraestrutura das pistas |

### 2. Entidades Extraídas

| Entidade | Exemplos Mapeados |
| --- | --- |
| `local` | britador 1, escavadeira 5, frente de lavra, pilha de estéril |
| `componente` | motor, pneu, suspensão, bateria, freio, direção, filtro |
| `carga` | minério, carvão, estéril |
| `status_carga` | cheio, vazio, meia carga |
| `veiculo` | caminhão, motoniveladora, escavadeira, veículo leve |

---

## Exemplos de Testes e Eventos Cadastrados

Abaixo estão listados os eventos cadastrados no aplicativo supervisório e consumidos pelo sistema para validar a coerência da fala do operador.

*Ative um evento marcado como **Sim** no supervisório para validar respostas end-to-end corretas (LLM), ou um evento incompatível/desabilitado para testar o desvio e geração automática do alerta de erro do nó de NLU.*

| ID | Nome do Evento | Estímulo no Simulador | Critério de Resposta Esperada | Habilitado |
| --- | --- | --- | --- | --- |
| **0** | Falha no sistema de carga da bateria | O indicador de falha do sistema de carga da bateria está aceso. | Pare a máquina. Aplique o freio de estacionamento. Desligue o motor. Peça assistência pelo rádio. | **Sim** |
| **1** | Falha de freio | O sistema de mensagens exibe aviso de pressão de ar do retardador. | Pare a máquina. Use retardador para desacelerar, aplique freio de estacionamento e peça ajuda. | **Não** |
| **3** | Pára-brisas quebrado | O pára-brisas dianteiro fica gravemente danificado quando atingido por projétil. | Pare a máquina completamente. Desligue o motor. Aplique o freio de estacionamento. Peça assistência. | **Não** |
| **4** | Nível do líquido de arrefecimento baixo | O sistema de mensagens exibe o aviso de nível de líquido de arrefecimento baixo. | Pare a máquina completamente. Selecione "Park/Estacionamento". Peça assistência pelo rádio. | **Não** |
| **6** | Rádio comunica incidente de emergência | Incidente de emergência não visível transmitido pelo rádio. | Pare a máquina, aplique freio e mantenha rádio em silêncio. | **Não** |
| **7** | Falha do motor | O sistema de mensagens exibe um erro de controle do motor. | Pare a máquina completamente. Aplique o freio de estacionamento. Peça assistência pelo rádio. | **Não** |
| **8** | Nível de óleo do motor baixo | O sistema de mensagens exibe um aviso de nível baixo de óleo do motor. | Pare a máquina completamente. Aplique o freio de estacionamento. Desligue o motor. Peça assistência. | **Não** |
| **9** | Filtro de combustível obstruído | O sistema de mensagens exibe um aviso de obstrução do filtro de combustível. | Faça uma chamada de serviço pelo rádio. | **Não** |
| **10** | Nível de combustível baixo | Aviso de nível baixo de combustível. Medidor na zona baixa. | Pare a máquina completamente, aplique freio e peça ajuda. | **Sim** |
| **24** | *[Mapeado no CCO-IA]* | *Referente à falha crítica ou mecânica na simulação.* | *Ação de parada ou comunicação via rádio.* | **-** |
| **25** | *[Mapeado no CCO-IA]* | *Referente à falha mecânica na simulação.* | *Ação de comunicação via rádio.* | **-** |
| **26** | *[Mapeado no CCO-IA]* | *Referente à falha crítica na simulação.* | *Ação de parada imediata e comunicação.* | **-** |
| **27** | Falha na direção | O caminhão não responde ao comando da direção. | Pare a máquina completamente, aplique freio de estacionamento e comunique. | **Sim** |
| **28** | Tensão do sistema alta | Sistema de mensagens exibe aviso de alta tensão. | Pare a máquina, desligue o motor e peça assistência. | **Sim** |
| **29** | Tensão do sistema baixa | Sistema de mensagens exibe aviso de baixa tensão. | Pare a máquina, desligue o motor e peça assistência. | **Sim** |
| **31** | *[Mapeado no CCO-IA]* | *Evento logístico/climático suportado pelo NLU.* | *Reportar situação via rádio.* | **-** |
| **32** | Parada abrupta do caminhão à frente | Caminhão à frente para abruptamente e comunica emergência. | Pare rapidamente, mantenha distância segura e responda via rádio. | **Não** |
| **35** | Fogo no motor | Fogo e fumaça visíveis do compartimento do motor. | Pare a máquina, ative supressão de incêndio, desligue o motor e comunique. | **Sim** |
| **36** | *[Mapeado no CCO-IA]* | *Evento logístico/climático suportado pelo NLU.* | *Reportar situação via rádio.* | **-** |
| **37** | Fogo na roda | Fogo e fumaça visíveis da roda dianteira esquerda. | Pare a máquina, aplique freio, desligue o motor e peça assistência. | **Sim** |
| **39** | *[Mapeado no CCO-IA]* | *Evento logístico/climático suportado pelo NLU.* | *Reportar situação via rádio.* | **-** |
| **40** | Poeira | Visibilidade reduzida devido ao excesso de poeira na área. | Pare a máquina, desligue o motor e informe a situação usando o rádio. | **Não** |
| **41** | *[Mapeado no CCO-IA]* | *Evento logístico/climático suportado pelo NLU.* | *Reportar situação via rádio.* | **-** |
| **42** | *[Mapeado no CCO-IA]* | *Evento logístico/climático suportado pelo NLU.* | *Reportar situação via rádio.* | **-** |
| **44** | *[Mapeado no CCO-IA]* | *Evento de logística na via suportado pelo NLU.* | *Coordenação segura via rádio.* | **-** |
| **45** | Ultrapassando motoniveladora | Uma motoniveladora CAT 24M aparece à frente do operador. | Faça contato por rádio com a motoniveladora. Peça permissão para ultrapassar. | **Não** |
| **46** | Ultrapassando um nivelador | Um nivelador aparece à frente do operador. | Faça contato por rádio com o nivelador. Peça permissão para ultrapassar. | **Não** |
| **47** | Ultrapassar um veículo leve | Um veículo leve aparece à frente do operador. | Faça contato por rádio com o veículo leve. Peça permissão para ultrapassar. | **Não** |
| **49** | Pneu traseiro furado | Operador percebe um pneu furado no retrovisor esquerdo. | Pare a máquina, selecione neutro, aplique freio, desligue o motor e use rádio. | **Não** |
| **52** | Veículo leve no despejo | Veículo leve aparece nos espelhos ao dar ré na carga. | Use o rádio. Não aproxime a menos de 10 m do veículo leve. | **Não** |
| **53** | Poeira excessiva | Poeira perigosa vindo de caminhão à frente prejudica a visão. | Aumente a distância e faça contato visual/via rádio. | **Não** |

---

## Estrutura dos Arquivos

```text
cco_ia/
├── No_Vosk.py          # Nó STT — Captura voz, escuta evento e gerencia botões PTT
├── No_Rasa.py          # Nó NLU — Cliente HTTP Rasa e validador lógico de coerência
├── No_LLM.py           # Nó LLM — Conexão local e geração via Ollama 
├── No_Fala.py          # Nó TTS — Gerador de áudio neural offline utilizando Piper
├── config.yml          # Arquivo de Pipeline NLU do Rasa
├── domain.yml          # Arquivo de Domínio (intenções, entidades e slots)
├── endpoints.yml       # Configuração de rotas de comunicação externa do Rasa
├── credentials.yml     # Configuração de credenciais de canais do Rasa
├── README.md           # Documentação técnica do sistema
└── data/
    └── nlu.yml         # Base de dados de treinamento do motor NLU


```

---

## Variáveis e Parâmetros Configuráveis

### `No_Vosk.py`

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `_SAMPLE_RATE` | `16000` | Taxa de amostragem padrão de captação do microfone (Hz) |
| `_BLOCK_SIZE` | `4000` | Tamanho do bloco de buffers de áudio processados por callback |

### `No_Rasa.py`

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `URL_NLU` | `http://localhost:5005/model/parse` | Rota da API REST exposta pelo servidor local Rasa NLU |
| `TIMEOUT_S` | `5` | Tempo limite padrão de espera das requisições HTTP (segundos) |

### `No_LLM.py`

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `MODELO_LLM` | `llama3.2:1b` | Identificador do modelo local instanciado no Ollama |
| `MAX_HISTORICO` | `2` | Número máximo de turnos da conversa retidos na memória recente |

### `No_Fala.py`

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `ARQUIVO_AUDIO` | `/home/giovanna/Downloads/IA/piper_voices/fala.wav` | Diretório e nome do arquivo `.wav` temporário gerado para síntese |
| `CONFIANCA_MINIMA` | `0.70` | Índice mínimo aceitável de confiança NLU para acionar a voz |

### `config.yml` (Configurações internas do Rasa)

| Parâmetro | Valor | Descrição |
| --- | --- | --- |
| `FallbackClassifier.threshold` | `0.8` | Confiança matemática mínima para aceitar e prosseguir com uma intenção |
| `DIETClassifier.epochs` | `100` | Número de épocas configuradas para o treinamento do classificador |

---

## Troubleshooting

**O Rasa não responde / Ocorreu Timeout no Nó**

> Certifique-se de que o servidor do Rasa foi ativado na porta correta através do terminal correspondente. Valide o status executando: `curl http://localhost:5005/status` no seu console.

**O Vosk não reconhece nenhuma fala ou apresenta erros de carregamento**

> Confirme se a pasta descompactada com o modelo acústico `vosk-model-small-pt-0.3/` está localizada exatamente na raiz do mesmo diretório de trabalho onde o nó python é chamado.

**O Piper TTS não carrega a voz ou apresenta falha de arquivo**

> Verifique se os arquivos binários `.onnx` e os arquivos de configuração de metadados `.onnx.json` da voz em pt-BR selecionada estão com as permissões de leitura corretas e no caminho exato apontado por `ARQUIVO_AUDIO` no nó `No_Fala.py`.

**Não há saída de áudio nos alto-falantes/fones após a síntese**

> Verifique a lista de hardware e o ID do seu dispositivo de saída executando no console: `python3 -c "import sounddevice as sd; print(sd.query_devices())"`. Certifique-se de definir o dispositivo correto nas chamadas da biblioteca.

**A primeira resposta gerada pelo LLM apresenta lentidão severa**

> O Ollama faz o carregamento sob demanda do modelo para a memória RAM/VRAM na primeira chamada. O parâmetro `keep_alive=-1` já está adicionado nas configurações padrão para manter o modelo persistido na memória após a primeira chamada, eliminando totalmente este gargalo nas interações subsequentes.

---

## Licença

Este projeto foi desenvolvido de forma exclusiva para uso interno e embarcado em operações e frotas de mineração. Consulte a equipe e engenharia responsável para obter detalhes adicionais sobre políticas de distribuição e licenciamento de softwares corporativos.

```

```
