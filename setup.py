#!/usr/bin/env python3
"""
Setup configuration for Helios Autonomous Store
"""
from setuptools import setup, find_packages

setup(
    name="helios",
    version="0.2.0",
    description="Helios Autonomous Store - AI-Powered E-commerce Platform",
    author="Helios Team",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        # Core dependencies are in requirements.txt
    ],
    entry_points={
        "console_scripts": [
            "helios-orchestrator=start_orchestrator:main",
            "helios-ai-agents=start_ai_agents:main",
        ],
    },
)