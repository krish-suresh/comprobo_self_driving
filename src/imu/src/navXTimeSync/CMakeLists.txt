cmake_minimum_required (VERSION 3.5)
project (NavXTimeStamp)
add_definitions(-std=c++11 -Wall -Wextra -Wno-switch)

FIND_PACKAGE (Threads REQUIRED)



file(GLOB SOURCES
	"*.h"
	"*.cpp"
)

include_directories(".")

add_library(NavXTimeStamp ${SOURCES})

target_link_libraries(NavXTimeStamp ${CMAKE_THREAD_LIBS_INIT})
#target_compile_features(NavXTimeStamp PRIVATE cxx_range_for)

