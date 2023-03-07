import setuptools

setuptools.setup(
    name="Xnat tools",
    version="0.1",
    author="Edwin Bennink",
    author_email="H.E.Bennink@umcutrecht.nl",
    description="Xnat tools for batch processing",
    packages=['xnat_tools'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Development Status :: 2 - Pre-Alpha"],
    python_requires='>=3.8.10',
    install_requires=[
        'click>=8.1.3',
        'xnat>=0.5.0'],
    extras_require={}
)
