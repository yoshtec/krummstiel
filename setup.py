import setuptools

with open("Readme.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="krummstiel",
    version="0.0.8",
    author="Yoshtec",
    author_email="yoshtec@gmail.com",
    description="Backup multiple iOS (iPhone/iPad) devices regularly",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yoshtec/krummstiel",
    entry_points={
        "console_scripts": [
            "krummstiel = krummstiel.krummstiel:main"
        ]
    },
    packages=setuptools.find_packages(),
    install_requires=['click'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
    ],
    keywords="ios, backup, photo backup, iphone, ipad",
    python_requires='>=3.5',
)
