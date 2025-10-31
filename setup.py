from pathlib import Path

from setuptools import find_packages, setup


BASE_DIR = Path(__file__).resolve().parent
README_PATH = BASE_DIR / "README.md"
LONG_DESCRIPTION = README_PATH.read_text(encoding="utf-8") if README_PATH.exists() else ""


setup(
    name="nats-client-py",
    version="0.3.3",
    description="NATS utilities for Python microservices with request/reply and pub/sub helpers.",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=["nats-py==2.11.0"],
)
