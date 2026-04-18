from setuptools import setup, find_packages

setup(
    name="winscript",
    version="2.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "winscript = winscript.cli:main"
        ]
    },
    install_requires=[
        "lark>=1.1",
        "websockets>=12.0",
        "pyyaml>=6.0",
        "fastmcp>=2.0",
    ],
)
