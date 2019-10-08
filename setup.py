from setuptools import setup

setup(
    name="redforester",
    version="0.1.7",
    description="Async RedForester API module for Python 3.7+",
    url="https://github.com/ichega/redforester",
    author="Pavel Katskov",
    author_email="pasha_kackov@mail.ru",
    license="MIT",
    packages=[
        "redforester"
    ],
    install_requires=[
        "aiohttp",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 3 - Alpha"
    ]
)

