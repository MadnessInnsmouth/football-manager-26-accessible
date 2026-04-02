cmake_minimum_required(VERSION 3.16)
project(fm_backend LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(fm_backend SHARED
    src/api.cpp
    src/match_engine.cpp
    src/club_systems.cpp
    src/persistence.cpp
)

target_include_directories(fm_backend PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party
)

target_compile_definitions(fm_backend PRIVATE FM_ENGINE_BUILD)

set_target_properties(fm_backend PROPERTIES
    OUTPUT_NAME "fm_backend"
)
