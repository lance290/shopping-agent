# Test configuration
# Uncomment to use GoogleTest:
# find_package(GTest REQUIRED)
# 
# add_executable(test_health test_health.cpp)
# target_link_libraries(test_health PRIVATE GTest::gtest_main)
# 
# add_test(NAME HealthTest COMMAND test_health)

# Simple test without external framework
add_executable(test_basic test_basic.cpp)
add_test(NAME BasicTest COMMAND test_basic)
