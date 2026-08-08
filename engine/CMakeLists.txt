cmake_minimum_required(VERSION 3.15)
project(rt_score_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)
FetchContent_MakeAvailable(json)

add_executable(score_engine src/score_engine.cpp)
target_link_libraries(score_engine PRIVATE nlohmann_json::nlohmann_json)

enable_testing()
add_executable(score_engine_tests tests/test_score_engine.cpp)
add_test(NAME score_engine_tests COMMAND score_engine_tests)
