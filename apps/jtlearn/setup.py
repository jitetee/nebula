from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Single source of truth for version
from jtlearn import __version__

setup(
    name="jtlearn",
    version=__version__,
    author="KashSight Platform",
    author_email="kashsight@gmail.com",
    description="JSON-Powered Educational Learning System — offline quizzes, notes, flashcards, tutorials, and AI chat",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kashsight/kslearn",
    license="Proprietary — KashSight Platform",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Education",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Education",
        "Topic :: Education :: Computer Aided Instruction (CAI)",
        "Topic :: Education :: Testing",
    ],
    keywords="education quiz learning terminal offline ai flashcard tutorial",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "click>=8.0",
        "rich>=13.0",
    ],
    entry_points={
        "console_scripts": [
            "jtlearn=jtlearn.cli:main",
            "ksl=jtlearn.cli:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/kashsight/kslearn/issues",
        "Source": "https://github.com/kashsight/kslearn",
        "Documentation": "https://github.com/kashsight/kslearn/blob/main/README.md",
    },
)
