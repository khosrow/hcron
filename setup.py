from setuptools import setup, find_packages

import hcron

setup(
    name='hcron',
    version='0.18',
    author='John Marshall',
    author_email='John.Marshall@ec.gc.ca',
    packages=find_packages(),
    url='https://bitbucket.org/hcron/hcron',
    license='GPLv2',
    description='Hcron event scheduling tool',
    entry_points={
        'console_scripts': [
            'hcron-conv = hcron.scripts.hcron_conv:main',
            'hcron-event = hcron.scripts.hcron_event:main',
            'hcron-info = hcron.scripts.hcron_info:main',
            'hcron-reload = hcron.scripts.hcron_reload:main',
            'hcron-scheduler = hcron.scripts.hcron_scheduler:main'
        ],
    },
)

