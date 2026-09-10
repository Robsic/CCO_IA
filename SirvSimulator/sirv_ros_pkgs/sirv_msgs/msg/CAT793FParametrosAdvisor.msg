# The message to sirv_parametros_advisor of the CAT793F

std_msgs/Header header           # CAT793F panel buttons state at this time


float32 target  	

# Advisor:                                                                                                         
float32 systemvoltage 	# 11.2V

# Freio:
float32 braketemperature                              
float32 tempet                              
float32 tempdd                               
float32 tempdt                               
float32 tempoleoeixodif
float32 pressbombfreio
float32 velbomb                          
float32 temparcabine                        
float32 tempardctcabine                     
float32 temparcasol                         
float32 proleo_et                          
float32 proleo_dt
float32 pressacumsec                     
float32 pressacumserv
float32 velventliq
float32 rotrodatrasle
float32 rotrodatrasld
float32 presslubdif 
string solembrcomp
string filtroarreffreio
string estadofiltrofreio
string estadoderivfiltro
string estadofreioserv

# Chassi:
float32 presslubauto
float32 angulobascula                        
float32 fuellevel                         
float32 pressoleoacu                         
float32 tempfludir                           
float32 pressoleobombadir
char 	comandomarcha
string posescadaacesso
string posalavlevant
string niveloleotanque
string estadosaidaguincho
string filtrodrenocarter
string filtrotelaguincho
float32 systemairpressure
 
# Transmissão:
float32 torquetemperature
float32 totalhrs
float32 tempoleotrans
float32 distance
float32 rotentr
float32 rotacaotransm
string filtroleoconvtorque
string filtrotelaconvtorque
string filtrooleocrgtrans
string estadoniveloleotrans
char	limitgear

# Motor:
float32 rotdesejada
float32 temparambiente
float32 pressaoatmosferica                   
float32 pressarcarter                       
float32 pressabssdarref                     
float32 coolanttemperature
float32 fatorcarga
float32 pressdifoleo                        
float32 pressaoleomtr                         
float32 pressaoleomtrabs                     
float32 tempoleomtr
float32 redpotmotor                            
float32 tempescape_le                       
float32 tempescape_ld                        
float32 pressabssdbmtrc
float32 taxaconsumo                         
float32 pressdifiltro                       
float32 presscomb                           
float32 admbombcomb                          
float32 presscremalheiracomb                 
float32 tempcremalheiracomb                  
float32 tempcomb                            
float32 presscoletoradm1
float32 presscoletoradm2                                 
float32 tempcoletoradm2                   
float32 tempcoletadm
float32 restrfiltropeak                        
float32 entrcmpturbo
string nivelarref
string niveloleomtr
string estadofiltrocomb
string nivelsepcombagua
string deslignivelsolo 
float32 presscombnfiltr

# VIMS:
float32 payload             # 252T
float32 distpercarregado                     
float32 tempviagem                           
float32 contotalcarga                        
float32 tempopercurso
float32 derivpicoarm                       
float32 passopicoarm                         
float32 inclpico                             
float32 pressaoesteio_de                   
float32 pressaoesteio_te                  
float32 pressaoesteio_dd                   
float32 pressaoesteio_td                    
float32 restricao_fltr_1
float32 restricao_fltr_2
float32 restricao_fltr_3
float32 restricao_fltr_4
