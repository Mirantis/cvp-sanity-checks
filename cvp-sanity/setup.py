# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def get_requirements_list(requirements):
    all_requirements = read(requirements)
    return all_requirements

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='cvp-sanity',
    version='0.1',
    description='set of tests for MCP verification',
    long_description=readme,
    author='Mirantis',
    license=license,
    install_requires=get_requirements_list('./requirements.txt'),
    packages=find_packages(exclude=('tests', 'docs'))
)
