# Message to control the Dashboard of the CAT793F

std_msgs/Header header           	# CAT793F dashboard state at this time

uint8 fuellevel 			# Range: 0 - 100
uint8 torquetemperature			# Range: 0 - 100
uint8 tachometer			# Range: 0 - 100
uint8 coolanttemperature		# Range: 0 - 100
uint8 braketemperature			# Range: 0 - 100

uint8 chargingsystemindicator		# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 parkingindicator			# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 actionlightindicator		# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 transmissionfaultindicator 	# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 secondarysteeringindicator 	# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 enginefaultindicator		# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 throttlelockindicator		# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 steeringfaultindicator		# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]

uint8 machinesecuritysystemindicator	# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 lockoutindicator			# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 retarderindicator 		# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 tractioncontrolsystemindicator	# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 breackfaultindicator 		# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]
uint8 bodyupindicator			# Range: [0 - apagado, 1 - piscando lento, 2 - piscando rápido, 3 - acesso]

float32 distance
float32 speed

uint8 currentgear 			# Range: [1,2,3,4,5,N,R]

