import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.dirname(__file__), 'qmpy', 'VERSION.txt')) as fr:
    version = fr.read().strip()

setup(
    name='qmpy',
    version=version,
    author='The OQMD Development Team',
    author_email='oqmd.questions@gmail.com',
    license='LICENSE.txt',
    classifiers=["Programming Language :: Python :: 3.7"],
    packages=find_packages(),
    scripts=['bin/oqmd', 'bin/qmpy'],
    url='http://pypi.python.org/pypi/qmpy',
    description='Suite of computational materials science tools',
    include_package_data=True,
    long_description=open('README.md').read(),
    install_requires=[
        "Django == 2.2",
        "PuLP",
        "numpy",
        "scipy",
        "mysqlclient",
        "matplotlib",
        "networkx",
        "pytest",
        "python-memcached",
        "ase",
        "django-extensions > 2.2.5",
        "lxml",
        "spglib > 1.10",
        "PyCifRW >= 4.3",
        "pexpect",
        "pyparsing",
        "PyYAML",
        "scikit-learn",
        "bokeh",
        "djangorestframework > 3.10.0",
        "djangorestframework-xml",
        "djangorestframework-yaml",
        "djangorestframework-queryfields",
        "djangorestframework-filters",
        "django-crispy-forms",
        "lark-parser",
        "requests",
        "pygraphviz"
    ],
)
