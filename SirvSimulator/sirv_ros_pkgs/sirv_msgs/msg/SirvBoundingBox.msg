# Copyright (c) 2025 Laboratory of Robotics, Intelligent and Complex Systems (RobSIC) at the Universidade Federal
# de Itajubá (UNIFEI), Campus of Itabira.
#
# This work is licensed under the terms of XXX license.
# Author: Giovani Bernardes Vitor

uint8 utype					# Object label number (Building = 1; Vehicles = 10; Pedestrians = 4; ... ObjectLabel.h)
geometry_msgs/Vector3 location        	    # Center of the BoundingBox in local space
geometry_msgs/Vector3 extent      	        # Half the size of the BoundingBox in local space
geometry_msgs/Vector3 rotation		      	# Rotation of the BoundingBox in local space
#string classname                            # The class name of the object

