cmake_minimum_required(VERSION 3.5)

project(sirv_msgs)

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

#set(LLVM_INCLUDE "${PROJECT_SOURCE_DIR}/../sirv_dev/3rd/llvm-9.0-install/include")
#set(LLVM_LIBPATH "${PROJECT_SOURCE_DIR}/../sirv_dev/3rd/llvm-9.0-install/lib")


#set(CMAKE_CXX_FLAGS "-fPIC -std=c++14 -pthread -I${LLVM_INCLUDE} -Wl,-L${LLVM_LIBPATH}")
set(CMAKE_CXX_FLAGS "-fPIC -std=c++14 -pthread -frtti")

#set(CMAKE_CXX_FLAGS "-fPIC -std=c++14 -pthread ")

#set(CMAKE_CXX_FLAGS "-std=c++14 -stdlib=libc++")
#set(CMAKE_EXE_LINKER_FLAGS "-stdlib=libc++ -lc++abi")

find_package(ament_cmake REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(diagnostic_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

set(msg_files
  msg/CAT793FInstrumentCluster.msg
  msg/CAT793FVehicleControl.msg
  msg/CAT793FPanelControl.msg  
  msg/CAT793FErrors.msg
  msg/CAT793FSingleEvent.msg
  msg/CAT793FEvents.msg
  msg/SirvWeatherParameters.msg
  msg/SirvActorAttribute.msg
  msg/SirvActorDefinition.msg
  msg/SirvVehicleLightState.msg
  msg/SirvVehicleSoundState.msg
  msg/SirvVehicleEffectsState.msg
  msg/SirvVehicleControl.msg
  msg/SirvVehicleTelemetry.msg
  msg/CAT793FParametrosAdvisor.msg
  msg/SirvSimulationConfig.msg
  msg/SirvActorDescription.msg
  msg/SirvActorAttributeValue.msg
  msg/SirvVehiclePhysicsControl.msg
  msg/SirvBoundingBox.msg
)

set(srv_files
  srv/DestroyObject.srv
  srv/SpawnObject.srv
  srv/SpawnObjectWithParent.srv
  srv/GetBlueprints.srv
  srv/GetAllLevelBBs.srv
  srv/SetViewTarget.srv
  srv/SetVehicleLightState.srv
  srv/SetVehicleSoundState.srv
  srv/SetVehicleEffectsState.srv
  srv/GetVehicleTelemetry.srv
  srv/GetWeatherParameters.srv
  srv/SetWeatherParameters.srv
  srv/SimulationConfig.srv
  srv/SetVehiclePhysicsControl.srv
  srv/GetVehiclePhysicsControl.srv
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  ${srv_files}
  
  DEPENDENCIES builtin_interfaces std_msgs diagnostic_msgs geometry_msgs
  ADD_LINTER_TESTS
)

#file(GLOB llvmlibs
#      "${LLVM_LIBPATH}/lib*.so"
#      )
      
#target_link_libraries(${PROJECT_NAME} ${llvmlibs})

# PROPERTIES
#set_target_properties(${PROJECT_NAME} PROPERTIES DEBUG_POSTFIX "_d")




ament_export_dependencies(rosidl_default_runtime)
ament_package()
