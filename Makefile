CC = g++

# Include paths
CDEFINES = -I/opt/homebrew/lib/python3.11/site-packages/pybind11/include
CDEFINES += -I/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11/include/python3.11
# Note: You had this include path twice; one is enough unless you have a specific reason

# Source files
SOURCES = Dispatcher.cpp Mode.cpp precomp.cpp SpeedSample.cpp bindings.cpp
OBJECTS = $(SOURCES:.cpp=.o)

# Name for Python shared library
PYMODULE = magicXorMiner.so

# Detect OS
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    # Linker flags for macOS
    LDFLAGS = -framework OpenCL \
              -L/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11/lib \
              -lpython3.11 \
              -ldl \
              -framework CoreFoundation
    # Compiler flags
    CFLAGS = -c -std=c++11 -Wall -O2 -fPIC
else
    # Linker flags for Linux (adjust as needed)
    LDFLAGS = -s -lOpenCL -mcmodel=large
    # Compiler flags for Linux
    CFLAGS = -c -std=c++11 -Wall -O2 -mcmodel=large -fPIC
endif

# Default target
all: $(PYMODULE)

# Link the shared library
$(PYMODULE): $(OBJECTS)
	$(CC) -shared $(OBJECTS) $(LDFLAGS) -o $@

# Compile source files to object files
%.o: %.cpp
	$(CC) $(CFLAGS) $(CDEFINES) $< -o $@

# Clean up
clean:
	rm -rf *.o $(PYMODULE)

.PHONY: all clean