from setuptools import setup, find_packages

setup(
    name="ffdl-cli",
    version="1.0.0",
    description="Ultra-High Speed Multi-Part Parallel Acceleration Downloader for FuckingFast.co",
    packages=find_packages(),
    install_requires=[
        "rich>=13.0.0",
        "click>=8.0.0",
        "httpx>=0.25.0",
        "aiohttp>=3.9.0",
    ],
    entry_points={
        "console_scripts": [
            "ffdl=ffdl.cli:main",
        ],
    },
    python_requires=">=3.8",
)
