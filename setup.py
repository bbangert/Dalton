__version__ = '0.1'

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()


setup(name='dalton',
      version=__version__,
      description="An httplib injection library for recording and playing back HTTP interactions.",
      long_description=README,
      classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Testing :: Traffic Generation",
      ], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='mechanize httplib crawling mock test',
      author='Ben Bangert',
      author_email='ben@groovie.org',
      url='https://github.com/bbangert/Dalton',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
