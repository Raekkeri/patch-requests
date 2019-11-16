from setuptools import find_packages, setup

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='patch-requests',
    zip_safe=False,
    version='0.2.0',
    description=('Simple patching of `requests` calls'),
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[],
    keywords=['requests', 'tests', 'mock', 'patch'],
    author='Teemu Husso',
    author_email='teemu.husso@gmail.com',
    url='https://github.com/Raekkeri/patch-requests',
    py_modules=['patch_requests'],
    install_requires=['setuptools'],
)
