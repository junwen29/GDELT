from distutils.core import setup

setup(name='GDELTApp',
      version='1.0',
      description='GDELT event parser',
      author='Jun Wen ',
      author_email='tsang.jw@csit.gov.sg', requires=['beautifulsoup4', 'goose3', 'numpy', 'requests',
                                                     'schedule']
      )
