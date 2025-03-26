#pragma once

#include "Dispatcher.hpp"
#include "Mode.hpp"
#include <string>

class MagicXorMiner {
public:
    MagicXorMiner(const std::string &seedPublicKey,
                  const std::string &difficulty,
                  size_t inverseSize = 255,
                  size_t inverseMultiple = 16384,
                  size_t worksizeLocal = 64,
                  size_t worksizeMax = 0,
                  bool noCache = false);

    // Run the miner and return the found private key (or empty if none)
    std::string run();

private:
    std::string seedPublicKey_;
    std::string difficulty_;
    size_t inverseSize_;
    size_t inverseMultiple_;
    size_t worksizeLocal_;
    size_t worksizeMax_;
    bool noCache_;
};