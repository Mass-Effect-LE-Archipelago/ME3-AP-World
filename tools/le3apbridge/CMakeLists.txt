cmake_minimum_required(VERSION 3.27)
project(LE3ArchipelagoBridge LANGUAGES CXX)
option(LE3AP_DELIVERY_DEV "Enable restricted development-only seed binding and delivery" OFF)
option(LE3AP_CAREER_TRACE "Enable read-only new-career script observation" OFF)
if(LE3AP_DELIVERY_DEV AND LE3AP_CAREER_TRACE)
    message(FATAL_ERROR "Career tracing and development writes are separate profiles")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The upstream tree remains an unmodified dependency checkout.
add_subdirectory(../vendor/LExASIs ${CMAKE_BINARY_DIR}/sdk)
set(LEASI_COMPILE_DEFINITIONS SPDLOG_ACTIVE_LEVEL=0)
set(LEASI_COMPILE_OPTIONS /W4 /WX /permissive /wd4121 /wd4127 /wd4702)
asi_target(APBridge SHARED GAMES LE3
    SOURCES Bridge.cpp
    VLINKS Common LESDK)
target_include_directories(APBridge-LE3 PRIVATE ../vendor/LExASIs)
target_compile_definitions(APBridge-LE3 PRIVATE NOMINMAX _CRT_SECURE_NO_WARNINGS)
target_compile_definitions(APBridge-LE3 PRIVATE LE3AP_DELIVERY_DEV=$<BOOL:${LE3AP_DELIVERY_DEV}>)
target_compile_definitions(APBridge-LE3 PRIVATE LE3AP_CAREER_TRACE=$<BOOL:${LE3AP_CAREER_TRACE}>)
set_target_properties(APBridge-LE3 PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

add_executable(DeliveryTests tests/DeliveryTests.cpp)
target_compile_options(DeliveryTests PRIVATE /W4 /WX)
add_executable(CareerTraceTests tests/CareerTraceTests.cpp)
target_compile_options(CareerTraceTests PRIVATE /W4 /WX)
