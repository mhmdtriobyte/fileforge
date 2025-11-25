"""Setup configuration for FileForge - Universal File Converter CLI."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fileforge",
    version="1.0.0",
    author="Mohammad Issa",
    author_email="mhmdtriobyte@gmail.com",
    description="Fast, offline universal file converter with a beautiful CLI interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mhmdtriobyte/fileforge",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Text Processing :: General",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=[
        "Pillow>=10.0.0",
        "pypdf>=3.0.0",
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "rich>=13.0.0",
        "click>=8.1.0",
        "tkinterdnd2>=0.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "fileforge=fileforge.cli:main",
            "fileforge-gui=fileforge.gui:main",
        ],
    },
    keywords="file converter image pdf csv json excel cli",
    project_urls={
        "Bug Reports": "https://github.com/mhmdtriobyte/fileforge/issues",
        "Source": "https://github.com/mhmdtriobyte/fileforge",
    },
)
