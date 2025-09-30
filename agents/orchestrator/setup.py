from setuptools import setup, find_packages

setup(
    name="agent-platform-shared",
    version="1.0.0",
    description="Shared modules for the agent platform",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn>=0.25.0",
        "pydantic>=2.10.0",
        "openai>=1.40.0",
        "httpx>=0.28.0",
        "google-adk>=1.15.1",
    ],
    python_requires=">=3.8",
)
