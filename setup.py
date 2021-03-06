from setuptools import find_packages, setup

setup(
    name='postpython',
    packages=find_packages(exclude=['tests*']),
    version='0.2.1',
    description='A library to use postman collection in python.',
    author='Bardia Heydari nejad, Kirill Golubev',
    author_email='bardia.heydarinejad@gmail.com, ff.kirill@gmail.com',
    url='https://github.com/ffkirill/postpython.git',
    keywords=['postman', 'rest', 'api'],  # arbitrary keywords
    install_requires=[
        'requests',
    ],
    classifiers=[],
)
