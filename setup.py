from setuptools import setup, find_packages

import hcron

setup(
    name='hcron',
    version='0.17.2',
    author='John Marshall',
    author_email='John.Marshall@ec.gc.ca',
    packages=find_packages(),
    url='https://bitbucket.org/hcron/hcron',
    license='GPLv2',
    description='Hcron event scheduling tool',
    entry_points={
        'console_scripts': [
            'hcron-conv = hcron.hcron_conv:main',
            'hcron-event = hcron.hcron_even:main',
            'hcron-info = hcron.hcron_info:main',
            'hcron-reload = hcron.hcron_reload:main'
        ],
    },
)

