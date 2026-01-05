#!/usr/bin/env python3
"""
Setup script for Veterans Verification CLI.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="veterans-verify-cli",
    version="2.0.0",
    author="Veterans CLI",
    description="CLI tool for ChatGPT Plus US Veterans verification via SheerID",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ThanhNguyxn/SheerID-Verification-Tool",
    packages=find_packages(),
    package_dir={"": "."},
    py_modules=["main"],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "httpx>=0.27.0",
        "cloudscraper>=1.2.71",
        "rich>=13.7.0",
        "click>=8.1.7",
        "aiohttp>=3.9.0",
        "python-dateutil>=2.8.2",
        "pydantic>=2.5.0",
    ],
    extras_require={
        "socks": ["PySocks>=1.7.1"],
    },
    entry_points={
        "console_scripts": [
            "veterans-verify=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Utilities",
    ],
    keywords="veterans verification sheerid chatgpt cli",
)
