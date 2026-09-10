# The message to control the start simulation from supervirosy system

std_msgs/Header header           # Simulation config at this time

#geral, opcoes e requisitos

string condutor
int8 idsitio
int8 idmaquina
string proposito
bool prompt
string luz
bool farois
bool radio
int8 volumeradio
string clima
string corneblina
string corpoeira

int32 tempoviagemtotal

bool   ordemtestes # true: ordem padrão, false: aleatorio
bool[] teste_freio # 0.alarme ré, 1.Alarme de re com falha, 2.freio auxiliar, 3.freio estacionamento, 4.freio serviço, 5. freio retarder, 6.TCS/AETA 


#condicao de operacao - indice=area_id areas de carregamento e descarregamento
string[] ar    #Visão Clara, Neblina e Poeira  
int8[] tracao  # valor de 0 a 100% 
int8[] resistencia # valor de 0 a 100%


# rota para treinamento:  posicao 0: inicio, posicao 1: final
int8[] rota



#cargas - trafego dentro da rota
int8[] carga_id_maquinas # identificador da maquina na rota especifica
int8[] carga_q_maquinas  # quantidade de máquinas na rota especifica


#eventos - indice=evento_id
int8[] evento_id # lista de eventos ativos
int8[] entrada
int8[] pontos1
float32[] area_x
float32[] area_y
float32[] area_r

#assistentes - indice=assistente_id
bool[] assistentes 

#benchmarks - indice=benchmark_id
bool[] benchmark
int8[] benchmark_meta

#erros - indice=erro_id
int8[] error_id
int8[] error_pontos

