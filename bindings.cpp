#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>
#include <vector>
#include "magicXorLauncher.cpp"

namespace py = pybind11;

PYBIND11_MODULE(magicXorMiner, m) {
    std::cout << "Initializing profanity2 module" << std::endl;
    m.doc() = "Python binding for the profanity2 magicxor mode";
    
    m.def("runMagicXor", &runMagicXor,
          py::arg("strPublicKey"),
          py::arg("strMagicXorDifficulty"),
          py::arg("mineContract") = false,
          py::arg("worksizeLocal") = 64,
          py::arg("worksizeMax") = 0,
          py::arg("inverseSize") = 255,
          py::arg("inverseMultiple") = 16384,
          py::arg("bNoCache") = false,
          py::arg("vDeviceSkipIndex") = std::vector<size_t>(),
          "Executes the custom magicxor kernel and returns the magicxor result string");
}