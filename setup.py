from setuptools import find_packages, setup


setup(
    name="nats-client-py",
    version="0.3.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=["nats-py==2.11.0"],
)
