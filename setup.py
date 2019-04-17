from setuptools import setup

setup(
    name="rfapi",
    version="0.0.1",
    description="Async RedForester API module for Python 3.6+",
    url="https://github.com/ichega/rfapi/",
    author="Pavel Katskov",
    author_email="pasha_kackov@mail.ru",
    license="MIT",
    packages=[
        "aiohttp",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 3 - Alpha"
    ]
)