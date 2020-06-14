from setuptools import setup
with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="redforester",
    version="0.1.8",
    description="Async RedForester API module for Python 3.7+",
    long_description=long_description,
    long_description_content_type="text/markdown",
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
    ],
    python_requires='>=3.7',

)

