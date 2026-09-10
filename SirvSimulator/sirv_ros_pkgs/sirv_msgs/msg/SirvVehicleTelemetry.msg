# The message to get the main informations of telemetry from a Vehicle into SIRV-UE5

float32 speed					        # The vehicle speed (km/h)
float32 enginerpm	      			    # The vehicle engine RPM
int8    gear	             			# The state of the vehicle gear 
float32 tryposition              		# The position state of the try
float32 payload					        # The payload from CAT793F
float32 torque                          # The torque of the engine
float32 rollingresistance               # The rolling resistance
geometry_msgs/Vector3 position        	# The vehicle body position
geometry_msgs/Vector3 orientation      	# The vehicle body orientation
geometry_msgs/Vector3 acceleration      # The vehicle body acceleration
geometry_msgs/Vector3 angularvelocity	# the Angular velocity of the vehicle body 

    
