from setuptools import setup, find_packages

setup(
    name="inventory-manager-nci",
    version="1.0.0",
    author="Uday Kiran Reddy Dodda",
    author_email="uday@example.com",
    description="Smart Inventory Management System - A Python library for inventory operations",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
