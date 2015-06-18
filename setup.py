from setuptools import setup

setup(
    name='django-sugar',
    version='0.5',
    license='BSD',
    description='Curated collection of all the sweet Django helpers/utilities \
        developers create, and sometimes recreate too often.',
    author='Kevin Fricovsky',
    author_email='kfricovsky@gmail.com',
    url='http://github.com/montylounge/django-sugar',
    packages=[
        'sugar',
        'sugar.admin',
        'sugar.cache',
        'sugar.forms',
        'sugar.management',
        'sugar.management.commands',
        'sugar.middleware',
        'sugar.templatetags',
        'sugar.utils',
        'sugar.views',
        'sugar.widgets',
    ],
    classifiers=[
        'Development Status :: 2 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    test_suite = "test_project.runtests.runtests"
)

