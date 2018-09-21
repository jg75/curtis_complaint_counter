"""Setuptools for curtis_complaint_counter."""

from setuptools import setup

install_requires = ["boto3==1.9.8"]

tests_require = install_requires + ["pytest==3.3.1"]

setup(
    name="curtis_complaint_counter",
    version="0.0.0",
    setup_requires=[],
    tests_require=tests_require,
    entry_points={
        'console_scripts': [
            'deploy=deploy:main'
        ],
    },
)
