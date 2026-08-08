// Minimal, dependency-free test harness for scoring.hpp - a handful of
// known input/output pairs don't need a full framework (Catch2/GoogleTest)
// pulled in via FetchContent just to check them.
#include "../src/scoring.hpp"

#include <cmath>
#include <iostream>
#include <string>

namespace {

int g_failures = 0;

void ExpectNear(double actual, double expected, double tolerance, const std::string& label) {
    if (std::abs(actual - expected) > tolerance) {
        std::cerr << "FAIL " << label << ": expected " << expected << ", got " << actual << "\n";
        ++g_failures;
    } else {
        std::cout << "ok   " << label << "\n";
    }
}

}  // namespace

int main() {
    using scoring::ControversyPenalty;
    using scoring::kPrior;
    using scoring::Shrink;

    ExpectNear(Shrink(98.0, 0.0), kPrior, 0.01,
               "Shrink: zero reviews collapses fully to the prior");

    ExpectNear(Shrink(98.0, 100000.0), 98.0, 0.05,
               "Shrink: huge sample stays close to the raw score");

    // count == kPriorWeight means raw score and prior get equal weight.
    ExpectNear(Shrink(90.0, 20.0), 75.0, 0.01,
               "Shrink: count == priorWeight lands halfway to the prior");

    ExpectNear(ControversyPenalty(80.0, 80.0), 0.0, 0.01,
               "ControversyPenalty: no gap, no penalty");

    ExpectNear(ControversyPenalty(90.0, 50.0), 10.0, 0.01,
               "ControversyPenalty: scales with the gap");

    ExpectNear(ControversyPenalty(100.0, 0.0), scoring::kMaxControversyPenalty, 0.01,
               "ControversyPenalty: capped at kMaxControversyPenalty");

    if (g_failures > 0) {
        std::cerr << g_failures << " test(s) failed\n";
        return 1;
    }
    std::cout << "all tests passed\n";
    return 0;
}
