// Pure scoring math, split out of score_engine.cpp so engine/tests/
// can exercise Shrink() and ControversyPenalty() directly with known
// input/output pairs instead of only black-box testing the whole binary.
#pragma once

#include <algorithm>
#include <cmath>

namespace scoring {

constexpr double kPrior = 60.0;        // "average movie" baseline out of 100
constexpr double kPriorWeight = 20.0;  // treat the prior as ~20 reviews of skepticism
constexpr double kMaxControversyPenalty = 15.0;

// Pulls rawScore toward kPrior when `count` (review volume) is small, and
// trusts rawScore more as count grows.
inline double Shrink(double rawScore, double count) {
    if (count + kPriorWeight <= 0.0) return kPrior;
    return (rawScore * count + kPrior * kPriorWeight) / (count + kPriorWeight);
}

// Points deducted when two (already-shrunk) scores disagree sharply -
// scales with the gap between them, capped at kMaxControversyPenalty.
inline double ControversyPenalty(double a, double b) {
    const double gap = std::abs(a - b);
    return std::min(gap * 0.25, kMaxControversyPenalty);
}

}  // namespace scoring
