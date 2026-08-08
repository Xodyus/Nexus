// Realistic Score Engine
//
// Rotten Tomatoes' tomatometer is a binary fresh/rotten percentage, which
// overstates quality (a lukewarm 6/10 review still counts as "fresh"), and
// both the tomatometer and audience score are noisy when the review count
// is low or can be skewed by review-bombing / early hype. This engine takes
// the raw scraped numbers and produces a "realistic score" that:
//
//   1. Shrinks each score toward a neutral prior in proportion to how few
//      reviews back it up (Bayesian shrinkage) - a 98% score from 12
//      reviews is trusted far less than a 98% score from 400 reviews.
//   2. Applies a "controversy penalty" when critics and audience disagree
//      sharply, since a big gap means neither number is fully trustworthy
//      on its own.
//
// Usage: score_engine <input.json> <output.json>
//
// Input schema (produced by scraper/normalize.py):
//   { "slug": str, "tomatometer_score": number, "average_critic_score": number,
//     "audience_score": number, "critic_review_count": number,
//     "audience_review_count": number }
//
// average_critic_score is the mean of critics' own numeric scores (see
// scraper/reviews_scraper.py) rather than RT's binary fresh/rotten percentage
// - it's what actually gets shrunk and blended below. It falls back to
// tomatometer_score in normalize.py when no reviews had an explicit score,
// so this engine doesn't need to know the difference.

#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
#include <cmath>
#include <algorithm>

using json = nlohmann::json;

namespace {

constexpr double kPrior = 60.0;        // "average movie" baseline out of 100
constexpr double kPriorWeight = 20.0;  // treat the prior as ~20 reviews of skepticism
constexpr double kMaxControversyPenalty = 15.0;

// Pulls rawScore toward kPrior when `count` (review volume) is small, and
// trusts rawScore more as count grows.
double Shrink(double rawScore, double count) {
    if (count + kPriorWeight <= 0.0) return kPrior;
    return (rawScore * count + kPrior * kPriorWeight) / (count + kPriorWeight);
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: score_engine <input.json> <output.json>\n";
        return 1;
    }

    std::ifstream in(argv[1]);
    if (!in) {
        std::cerr << "error: cannot open input file " << argv[1] << "\n";
        return 1;
    }

    json input;
    try {
        in >> input;
    } catch (const json::parse_error& e) {
        std::cerr << "error: invalid JSON - " << e.what() << "\n";
        return 1;
    }

    const double tomatometer = input.value("tomatometer_score", 0.0);
    const double averageCriticScore = input.value("average_critic_score", tomatometer);
    const double audienceScore = input.value("audience_score", 0.0);
    const double criticCount = input.value("critic_review_count", 0.0);
    const double audienceCount = input.value("audience_review_count", 0.0);

    const double stableCritic = Shrink(averageCriticScore, criticCount);
    const double stableAudience = Shrink(audienceScore, audienceCount);

    const double gap = std::abs(stableCritic - stableAudience);
    const double controversyPenalty = std::min(gap * 0.25, kMaxControversyPenalty);

    double realistic = (stableCritic * 0.5 + stableAudience * 0.5) - controversyPenalty;
    realistic = std::clamp(realistic, 0.0, 100.0);

    json output;
    output["slug"] = input.value("slug", "");
    output["inputs"] = {
        {"tomatometer_score", tomatometer},
        {"average_critic_score", averageCriticScore},
        {"audience_score", audienceScore},
        {"critic_review_count", criticCount},
        {"audience_review_count", audienceCount},
    };
    output["stabilized"] = {
        {"critic", stableCritic},
        {"audience", stableAudience},
    };
    output["controversy_penalty"] = controversyPenalty;
    output["realistic_score"] = realistic;

    std::ofstream out(argv[2]);
    out << output.dump(2);

    std::cout << "realistic_score=" << realistic << "\n";
    return 0;
}
