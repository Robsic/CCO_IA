#!/usr/bin/env bash

source ~/.bashrc

source /home/giovani/codigos/ros2_foxy/install/setup.bash
source /home/giovani/codigos/SIRV-Simulator/install/setup.bash

export ROS_DOMAIN_ID=25
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=/home/giovani/codigos/SIRV-Simulator/install/sirv_ros/config/cyclonedds.xml 
export UE5_ROOT=/home/giovani/codigos/UnrealEngine-5.0.3-release

echo "Iniciando o Simulador SIRV UE5..."

ros2 launch sirv_cat793fsim UE5_simulation_launch.py &
#/home/giovani/SirvDeploy/Linux/SirvUE5.sh &
P1=$!

echo "Simulador SIRV UE5 inicializado..."
echo "Iniciando o SIRV CATSIM793F..."

ros2 launch sirv_cat793fsim CAT793F_simulation_launch.py
P2=$!

wait $P1 $P2


