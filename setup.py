from setuptools import setup

setup(
    name="akbp",
    version="0.1.0",
    description="Reference CLI for the Agent Knowledge Base Protocol",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.9",
    py_modules=["akbp", "akbp_tool_server"],
    package_dir={"": "cli"},
    entry_points={
        "console_scripts": [
            "akbp=akbp:main",
            "akbp-tool-server=akbp_tool_server:main",
        ]
    },
)
