import setuptools

VERSION = "0.0.11"

with open("Readme.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

print("hi")

setuptools.setup(
    name="krummstiel",
    version=VERSION,
    author="Yoshtec",
    author_email="yoshtec@gmail.com",
    description="Backup multiple iOS (iPhone/iPad) devices regularly",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yoshtec/krummstiel",
    entry_points={"console_scripts": ["krummstiel = krummstiel.krummstiel:cli"]},
    packages=setuptools.find_packages(),
    install_requires=["click", "click-default-group"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
    ],
    keywords="ios, backup, photo backup, iphone, ipad",
    python_requires=">=3.5",
)
