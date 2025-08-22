#!/usr/bin/env python3
"""
Setup configuration for Helios Print-On-Demand Automation System
Makes the helios package installable for proper import path resolution
"""

from setuptools import setup, find_packages

setup(
    name="helios",
    version="1.0.0",
    description="AI-Powered Print-On-Demand Automation System",
    author="Helios Team",
    packages=find_packages(),
    python_requires=">=3.13",
    install_requires=[
        # Core dependencies are defined in requirements.txt
        # This setup.py is primarily for package structure
    ],
    include_package_data=True,
    package_data={
        "helios": ["*.py", "**/*.py"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
    ],
)
