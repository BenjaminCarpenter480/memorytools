from setuptools import setup, find_packages


# with open('README.rst') as f:
#     readme = f.read()

# with open('LICENSE') as f:
#     license = f.read()

setup(
    name='memorytools',
    version='0.1.0',
    description='Tool for detection of memory leaks on running processes',
    long_description="Tool for detection of memory leaks on running processes",
    author='Benjamin Carpenter',
    author_email='bcarpenter480@gmail.com',
    url='https://github.com/BenjaminCarpenter480/memorytools',
    # license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    scripts=['memorytools/runner.py']
)
