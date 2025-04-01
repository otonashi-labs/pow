#!/usr/bin/env bash
#
# find_mac_includes.sh
#
# Example script that tries to locate:
# 1) pybind11/include
# 2) Python.framework or standard Python include dirs
# 3) Library dirs (for LDFLAGS) 
#
# Usage:
#   chmod +x find_mac_includes.sh
#   ./find_mac_includes.sh [python_executable]
#
# Example:
#   ./find_mac_includes.sh python3.11
#

# Let user override Python executable (default to 'python3')
PYBIN="${1:-python3}"

echo "Using Python executable: $PYBIN"
echo

echo "==> Locating pybind11 include path..."
PYBIND11_INCLUDE=$($PYBIN -c "import pybind11; print(pybind11.get_include())" 2>/dev/null)
if [ $? -ne 0 ] || [ -z "$PYBIND11_INCLUDE" ]; then
  echo "[WARNING] Could not find pybind11 via \`$PYBIN\`. You may need to install it:"
  echo "         pip install pybind11"
  PYBIND11_INCLUDE="/path/to/pybind11/include"
fi
echo "PYBIND11_INCLUDE = $PYBIND11_INCLUDE"
echo

echo "==> Locating Python include path via sysconfig..."
PYTHON_INCLUDE=$($PYBIN -c "import sysconfig; print(sysconfig.get_paths().get('include',''))" 2>/dev/null)
if [ -z "$PYTHON_INCLUDE" ]; then
  echo "[WARNING] Could not auto-detect Python include path via sysconfig."
  echo "          Setting a placeholder path; edit as needed."
  PYTHON_INCLUDE="/path/to/Python.framework/Versions/3.X/include/python3.X"
fi
echo "PYTHON_INCLUDE   = $PYTHON_INCLUDE"
echo

echo "==> Locating Python library path (for LDFLAGS) via sysconfig..."
PYTHON_LIBDIR=$($PYBIN -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR') or '')" 2>/dev/null)
if [ -z "$PYTHON_LIBDIR" ]; then
  echo "[WARNING] Could not auto-detect Python LIBDIR via sysconfig."
  echo "          Setting a placeholder path; edit as needed."
  PYTHON_LIBDIR="/path/to/Python.framework/Versions/3.X/lib"
fi
echo "PYTHON_LIBDIR    = $PYTHON_LIBDIR"
echo

# Attempt to find which python version so we can link correctly:
PYTHON_VERSION=$($PYBIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
if [ -z "$PYTHON_VERSION" ]; then
  PYTHON_VERSION="3.11"  # fallback, adjust as needed
fi

echo "Determined Python version (major.minor) = $PYTHON_VERSION"
echo

# Construct sample Makefile variables from these paths:
echo "Suggested Makefile snippet:"
echo
echo "CDEFINES = -I$PYBIND11_INCLUDE -I$PYTHON_INCLUDE"
echo "LDFLAGS  = -framework OpenCL \\"
echo "           -L$PYTHON_LIBDIR \\"
echo "           -lpython$PYTHON_VERSION"
echo
echo "[NOTE] If your Python is built as a framework, you may also need additional flags."
echo "[NOTE] Verify the exact library name is correct (e.g. '-lpython3.11')."
