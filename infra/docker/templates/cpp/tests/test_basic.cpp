/**
 * Basic test without external framework
 * This ensures CTest has at least one test to run
 */
#include <iostream>
#include <cassert>

int main() {
    // Simple sanity check
    assert(1 + 1 == 2);
    assert(true);
    
    std::cout << "Basic tests passed!" << std::endl;
    
    return 0;
}
