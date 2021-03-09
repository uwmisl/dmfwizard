from setuptools import setup, find_packages

setup(
    name="dmfwizard",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'dmfwizard=dmfwizard.script.dmfwizard:main',
        ],
    },
    install_requires=[
        'click',
        'numpy',
        'shapely',
        'ezdxf',
    ],
    extras_require={
        'testing': [
            'pytest',
        ],
    },
    package_data={
    }
)
