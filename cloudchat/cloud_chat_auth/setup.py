from setuptools import setup, find_packages

setup(
    name="cloud-chat-karuna",   # unique name on PyPI
    version="0.1.0",
    author="karuna More",
    author_email="morekarunasr@gmail.com",
    description="Django authentication utilities for cloud chat apps",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Django>=3.2"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: Django",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)