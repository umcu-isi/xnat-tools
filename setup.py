import setuptools

setuptools.setup(
    name="xnat-tools",
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
    extras_require={},
    entry_points={
        'console_scripts': [
            'xnat-batch=xnat_tools.batch_process:batch_process_from_config',
            'xnat-metadata=xnat_tools.get_metadata:get_metadata_from_config']}
)
