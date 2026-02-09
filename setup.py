import setuptools

setuptools.setup(
    name='sanctions-pipeline',
    version='0.0.1',
    install_requires=[
        'apache-beam[gcp]',
        'requests',
        'google-auth'
    ],
    packages=setuptools.find_packages(),
)
