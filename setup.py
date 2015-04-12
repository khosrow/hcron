from setuptools import setup

import hcron

setup(
    name='hcron',
    # version=dscp.__version__,
    # author=dscp.__author__,
    author_email='John.Marshall@ec.gc.ca',
    packages=['hcron'],
    url='https://bitbucket.org/hcron/hcron',
    license='COPYRIGHT',
    # description=hcron.__doc__.rstrip(),
    entry_points={
        'console_scripts': [
            'hcron-conv = hcron.hcron-conv:main',
            'hcron-event = hcron.hcron-even:main',
            'hcron-info = hcron.hcron-info:main',
            'hcron-reload = hcron.hcron-reload:main'
        ],
    },
)
