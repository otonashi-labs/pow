#include "MagicXorMiner.hpp"
#include "Mode.hpp"
#include "Dispatcher.hpp"
#include <sstream>

MagicXorMiner::MagicXorMiner(const std::string &seedPublicKey,
                             const std::string &difficulty,
                             size_t inverseSize,
                             size_t inverseMultiple,
                             size_t worksizeLocal,
                             size_t worksizeMax,
                             bool noCache)
    : seedPublicKey_(seedPublicKey), difficulty_(difficulty),
      inverseSize_(inverseSize), inverseMultiple_(inverseMultiple),
      worksizeLocal_(worksizeLocal), worksizeMax_(worksizeMax),
      noCache_(noCache) {}

std::string MagicXorMiner::run() {
    try {
        Mode mode = Mode::magicXor(difficulty_);

        // Set target as address (you can change if you implemented contracts)
        mode.target = ADDRESS;

        // Get OpenCL devices
        auto devices = getAllDevices();
        if (devices.empty()) {
            throw std::runtime_error("No OpenCL devices found");
        }

        // Initialize OpenCL context
        cl_int errorCode;
        auto context = clCreateContext(NULL, devices.size(), devices.data(), NULL, NULL, &errorCode);
        if (errorCode != CL_SUCCESS) throw std::runtime_error("Error creating OpenCL context");

        // Compile kernel
        const std::string keccakSource = readFile("keccak.cl");
        const std::string vanitySource = readFile("profanity.cl");
        const char *sources[] = {keccakSource.c_str(), vanitySource.c_str()};
        auto program = clCreateProgramWithSource(context, 2, sources, NULL, &errorCode);
        if (errorCode != CL_SUCCESS) throw std::runtime_error("Error creating OpenCL program");

        std::ostringstream buildOpts;
        buildOpts << "-D PROFANITY_INVERSE_SIZE=" << inverseSize_
                  << " -D PROFANITY_MAX_SCORE=" << PROFANITY_MAX_SCORE;
        errorCode = clBuildProgram(program, devices.size(), devices.data(), buildOpts.str().c_str(), NULL, NULL);
        if (errorCode != CL_SUCCESS) throw std::runtime_error("Error building OpenCL program");

        // Create and run dispatcher
        Dispatcher dispatcher(context, program, mode,
                              worksizeMax_ == 0 ? inverseSize_ * inverseMultiple_ : worksizeMax_,
                              inverseSize_, inverseMultiple_, 1, seedPublicKey_);

        for (auto &device : devices) {
            dispatcher.addDevice(device, worksizeLocal_, 0);
        }

        dispatcher.run();

        clReleaseProgram(program);
        clReleaseContext(context);

        // Assuming you modified handleResult to terminate on first found:
        // dispatcher.run() prints result directly to stdout currently.
        // You can modify Dispatcher to return found key instead.
        
        // For simplicity, let's assume you modified Dispatcher to store found privateKey:
        // e.g., dispatcher.getFoundPrivateKey()
        return dispatcher.getFoundPrivateKey();  // You must implement this getter
    } catch (std::exception &e) {
        return std::string("error: ") + e.what();
    }
}