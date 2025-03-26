from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import sys
import os
import pybind11

# Get OpenCL include path - customize this based on your system
def get_opencl_include_path():
    if sys.platform == 'darwin':  # macOS
        return '/System/Library/Frameworks/OpenCL.framework/Headers'
    elif sys.platform == 'win32':  # Windows
        # Try to find CUDA or AMD SDK paths
        potential_paths = [
            'C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.0/include',
            'C:/Program Files (x86)/AMD APP SDK/3.0/include',
        ]
        for path in potential_paths:
            if os.path.exists(path):
                return path
        return None
    else:  # Linux and others
        return '/usr/include/CL'  # Default Linux path

# Get OpenCL library path
def get_opencl_lib_path():
    if sys.platform == 'darwin':  # macOS
        return []  # Framework is automatically included
    elif sys.platform == 'win32':  # Windows
        return ['OpenCL']
    else:  # Linux and others
        return ['OpenCL']

# Determine include and library paths
opencl_include = get_opencl_include_path()
opencl_libs = get_opencl_lib_path()

# Define the extension module
ext_modules = [
    Extension(
        'profanity2',
        [
            'profanity2_python.cpp',
            'profanity2_wrapper.cpp',
            'Dispatcher.cpp',
            'Mode.cpp',
            'SpeedSample.cpp',
            'precomp.cpp'
        ],
        include_dirs=[
            pybind11.get_include(),
            opencl_include,
            '.'  # Include current directory
        ],
        libraries=opencl_libs,
        language='c++'
    ),
]

# Custom build command
class BuildExt(build_ext):
    def build_extensions(self):
        # Add compiler-specific options
        c_opts = []
        l_opts = []
        
        if sys.platform == 'darwin':
            c_opts += ['-stdlib=libc++', '-mmacosx-version-min=10.9']
            l_opts += ['-framework', 'OpenCL']
        
        # Set the appropriate C++ standard
        ct = self.compiler.compiler_type
        if ct == 'unix':
            c_opts.append('-std=c++11')
        
        for ext in self.extensions:
            ext.extra_compile_args = c_opts
            ext.extra_link_args = l_opts
        
        build_ext.build_extensions(self)

setup(
    name='profanity2',
    version='0.1.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='Python bindings for Profanity2 Ethereum vanity address generator',
    long_description='',
    ext_modules=ext_modules,
    cmdclass={'build_ext': BuildExt},
    zip_safe=False,
    python_requires='>=3.6',
)