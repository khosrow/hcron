from setuptools import setup

import hcron

setup(
    name='hcron',
    # version=hcron.__version__,
    author='John Marshall',
    author_email='John.Marshall@ec.gc.ca',
    packages=['hcron'],
    url='https://bitbucket.org/hcron/hcron',
    license='GPLv2',
    description='Hcron event scheduling tool',
    entry_points={
        'console_scripts': [
            'hcron-conv = hcron.hcron-conv:main',
            'hcron-event = hcron.hcron-even:main',
            'hcron-info = hcron.hcron-info:main',
            'hcron-reload = hcron.hcron-reload:main'
        ],
    },
)
