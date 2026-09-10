
# The message to control the main movements of a Vehicle into SIRV-UE5


uint8   id			# ID of the vehicle into environment simulation...
float32 steer			# Range: -1.0 (left) a  1.0 (right)
float32 throttle	        # Range: 0.0 - 1.0
float32 brake                  # Range: 0.0 - 1.0
float32 brakeretarder		# Range: 0.0 - 1.0
bool    handbrake 		# Range: True - false 
int8    gear	             	# Range: [-1 {Reverse-82}, 0{Neutral-78}, 1{Gear_1-49}, 2{Gear_2-50}, (3,4,5) {Drive - 68}, P-{parking-80}] 
int8    hoist                    # Control the tipper of the truck into SIRV_UE5 (Range: [0 - floating, 1 - up, 2 - down, 3 - shake])

    
