CC = g++

# Include paths
CDEFINES = -I/usr/include/python3.11
CDEFINES += -I/usr/local/lib/python3.11/dist-packages/pybind11/include
# Note: You had this include path twice; one is enough unless you have a specific reason

# Source files
SOURCES = Dispatcher.cpp Mode.cpp precomp.cpp SpeedSample.cpp bindings.cpp
OBJECTS = $(SOURCES:.cpp=.o)

# Name for Python shared library
PYMODULE = magicXorMiner.so

# Detect OS
UNAME_S := $(shell uname -s)

# Linker flags for Linux (adjust as needed)
LDFLAGS = -shared -lOpenCL
# Compiler flags for Linux
CFLAGS = -c -std=c++11 -Wall -O2 -fPIC

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