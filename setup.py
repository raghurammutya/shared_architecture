from setuptools import setup, find_packages

setup(
    name="shared-architecture",
    version="0.5.0",  # ✅ Fixed: use plain version string
    description="A shared Python library for backend microservices, including models, utilities, and configurations.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Raghuram Mutya",
    author_email="raghu.mutya@gmail.com",
    url="https://github.com/raghurammutya/shared_architecture",
    packages=find_packages(include=["shared_architecture", "shared_architecture.*"]),
    include_package_data=True,
    install_requires=[
        "SQLAlchemy>=1.4",
        "psycopg2-binary>=2.9",
        "redis>=4.0",
        "pika>=1.3",
        "requests>=2.25",
        "pytest>=7.0",
        "pydantic>=1.10",
        "circuitbreaker>=1.3",
    ],
    python_requires=">=3.8",
    keywords="shared library microservices architecture configuration utilities",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License"
    ],
)
