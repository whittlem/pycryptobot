
from setuptools import setup, find_packages
from pycryptobot.core.version import get_version

VERSION = get_version()

f = open('README.md', 'r')
LONG_DESCRIPTION = f.read()
f.close()

setup(
    name='pycryptobot',
    version=VERSION,
    description='Crypto Bot',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author='Michael Whittle',
    author_email='john.doe@example.com',
    url=' https://github.com/whittlem/pycryptobot',
    license='Apache-2.0 License',
    packages=find_packages(exclude=['ez_setup', 'tests*']),
    package_data={'pycryptobot': ['templates/*']},
    include_package_data=True,
    entry_points="""
        [console_scripts]
        pycryptobot = pycryptobot.main:main
    """,
)
