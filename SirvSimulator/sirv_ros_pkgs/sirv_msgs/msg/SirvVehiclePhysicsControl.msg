# The message to get and set the main informations of physics control from a Vehicle into SIRV-UE5

#std::vector<geom::Vector2D> torque_curve
float32 max_rpm					# The vehicle  
float32 engine_rev_up_moi    				# The vehicle  
float32 damping_rate_full_throttle    		# The vehicle 
float32 damping_rate_zero_throttle_clutch_engaged     # The vehicle 
float32 damping_rate_zero_throttle_clutch_disengaged	# The vehicle 
bool    use_automatic_gears		    		# The vehicle 
float32 gear_change_time		    		# The vehicle 
float32 clutch_strength		    		# The vehicle 
float32 final_ratio			    		# The vehicle 
#vector<GearPhysicsControl> forward_gears
float32 mass
float32 drag_coefficient
geometry_msgs/Vector3 center_of_mass
#std::vector<geom::Vector2D> steering_curve
#std::vector<WheelPhysicsControl> wheels;
bool use_sweep_wheel_collision
    
