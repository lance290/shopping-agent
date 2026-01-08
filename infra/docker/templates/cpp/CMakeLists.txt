# Modern CMake configuration for C++ HTTP service
cmake_minimum_required(VERSION 3.20)
project(CppService VERSION 1.0.0 LANGUAGES CXX)

# C++ Standard
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Output directories
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# Find packages (provided by Conan)
find_package(httplib REQUIRED)
find_package(nlohmann_json REQUIRED)

# Main executable
add_executable(app
    src/main.cpp
    src/health.cpp
)

target_link_libraries(app
    PRIVATE
    httplib::httplib
    nlohmann_json::nlohmann_json
)

target_include_directories(app
    PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Compiler warnings
target_compile_options(app PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall -Wextra -Wpedantic>
    $<$<CXX_COMPILER_ID:MSVC>:/W4>
)

# Enable testing
enable_testing()

# Add tests subdirectory
add_subdirectory(tests)
