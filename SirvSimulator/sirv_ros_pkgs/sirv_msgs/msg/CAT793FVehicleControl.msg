# The message to control the main movements of the CAT793F

std_msgs/Header header                # CAT793F vehicle control state at this time

float32 steeringwheel		# Range: -1.0 (left) a  1.0 (right)
float32 throttle	        # Range: 0.0 - 1.0
float32 brake                    # Range: 0.0 - 1.0
float32 emergencybrake 		# Range: 0.0 - 1.0 
float32 brakeretarder      	# Range: 0.0 - 1.0 
int8 transmission             	# Range: [1,2,D,N,R,P] 
int8 hoist                    	# Control the tipper of the truck (Range: [F - floating, U - up, D - down, S - shake])
