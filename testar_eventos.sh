#!/bin/bash

VERDE='\033[0;32m'
CIANO='\033[0;36m'
AMARELO='\033[1;33m'
RESET='\033[0m'

echo -e "${VERDE}[*] A iniciar bateria de testes completa para todos os eventos...${RESET}"

# Carregar o ambiente do ROS 2 e o pacote sirv_msgs
source /opt/ros/jazzy/setup.bash
source /home/vrmine-sim/codigos/SirvSimulator/install/setup.bash

# Lista ordenada com os 31 eventos
eventos=(
    "0:Falha no sistema de carga da bateria"
    "1:Falha de freio"
    "3:Pára-brisas quebrado"
    "4:Nível do líquido de arrefecimento baixo"
    "6:Rádio comunica incidente de emergência"
    "7:Falha do motor"
    "8:Nível de óleo do motor baixo"
    "9:Filtro de combustível obstruído"
    "10:Nível de combustível baixo"
    "24:Falha crítica/mecânica (Mapeado)"
    "25:Falha mecânica (Mapeado)"
    "26:Falha crítica (Mapeado)"
    "27:Falha na direção"
    "28:Tensão do sistema alta"
    "29:Tensão do sistema baixa"
    "31:Evento logístico/climático (Mapeado)"
    "32:Parada abrupta do caminhão à frente"
    "35:Fogo no motor"
    "36:Evento logístico/climático (Mapeado)"
    "37:Fogo na roda"
    "39:Evento logístico/climático (Mapeado)"
    "40:Poeira (Visibilidade reduzida)"
    "41:Evento logístico/climático (Mapeado)"
    "42:Evento logístico/climático (Mapeado)"
    "44:Evento de logística na via (Mapeado)"
    "45:Ultrapassando motoniveladora CAT"
    "46:Ultrapassando um nivelador"
    "47:Ultrapassar um veículo leve"
    "49:Pneu traseiro furado"
    "52:Veículo leve parado no local de despejo"
    "53:Poeira excessiva na frente"
)

# Iterar sobre a lista de eventos
for evento in "${eventos[@]}"; do
    IFS=':' read -r id nome <<< "$evento"

    echo -e "${CIANO} A TESTAR EVENTO: [$id] $nome ${RESET}"

    # 1. Publicar o evento usando o formato rigoroso da mensagem CAT793FEvents
    echo -e "${AMARELO}[1/3] A publicar evento $id no simulador (/detected_events)...${RESET}"
    
    # Estrutura YAML exigida pela nova mensagem do simulador
    MSG_YAML="{events: [{code: {data: $id}, status: {data: 'IN_PROGRESS'}}]}"
    ros2 topic pub --once /detected_events sirv_msgs/msg/CAT793FEvents "$MSG_YAML"
    
    sleep 2

    # 2. Pressionar o PTT e abrir o microfone
    echo -e "${AMARELO}[2/3] A pressionar PTT...${RESET}"
    ros2 topic pub --once /botao_acionado std_msgs/msg/Int8 "{data: 1}"
    
    echo -e "${VERDE}         Podes falar agora. (A aguardar 7 segundos...)${RESET}"
    sleep 7

    # 3. Soltar o PTT para enviar o áudio
    echo -e "${AMARELO}[3/3] A soltar PTT para processamento...${RESET}"
    ros2 topic pub --once /botao_acionado std_msgs/msg/Int8 "{data: 0}"
    
    echo -e "${VERDE}[✔] Ciclo do evento $id concluído. A processar resposta... (Pausa de 6s)${RESET}"
    
    sleep 6
done

echo -e "\n${VERDE}[✔] BATERIA DE TESTES CONCLUÍDA COM SUCESSO!${RESET}"