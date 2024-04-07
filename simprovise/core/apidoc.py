#===============================================================================
# MODULE apidoc
#
# Copyright (C) 2014-2017 Howard Klein - All Rights Reserved
#
# Implements decorators and an event handler to be used in conjunction with
# Sphinx autodoc to generate API documentation.
#
# The apidoc and apidocskip decorators should be used in simulator source
# code:
#    @apidoc:     Used to decorate all classes that should be included in the
#                 API documentation
#
#    @apiskipdoc: Used to decorate methods/functions that should NOT be included
#                 in the API documentation. Needed for module-level functions
#                 (which otherwise are always included) and methods belonging
#                 to classes that are marked (via @apidoc decorator) for
#                 inclusion in the documentation.
#===============================================================================
import os, inspect

# generating_docs should be set to True before starting Sphinx.
# The make/makefile scripts should set the SIM_GEN_APIDOC environment variable.
generating_docs = os.getenv('SIM_GEN_APIDOC')
if generating_docs:
    print('API Doc generation enabled...')

# List of fully-qualified names (i.e., including module names) of classes to
# be included in the API documentation. Populated via @apidoc decorator
documented_classes = []

# Set if module names, specifying the modules to be included in the API
# documentation.
documented_modules = set()

# List of fully-qualified unctions/method names, specifying the functions/
# methods that are NOT to be included in the API documentation.
functions_to_skip = []

def qualified_name(obj):
    """
    Return the name of the object qualified with module (and class, if
    a function or property with a __qualname__ attribute)
    """
    if isinstance(obj, property):
        # for properties, get the fget function from the property
        # That's the object that has __module__ and __qualname__ attributes
        obj = obj.fget
    try:
        name = obj.__qualname__
    except AttributeError:
        name = obj.__name__
    return obj.__module__ + '.' + name

def apidoc(cls):
    """
    Decorate classes which are to be documented by Sphinx autodoc.
    Also adds the class's module to the list of modules to be documented.
    """
    if generating_docs:
        documented_classes.append(qualified_name(cls))
        documented_modules.add(cls.__module__)
    return cls

def apidocskip(func):
    """
    Decorate functions or methods which are NOT to be documented by
    Sphinx autodoc.
    """
    if generating_docs:
        print("skipping function/method:", qualified_name(func))
        functions_to_skip.append(qualified_name(func))
    return func

def docskip(app, what, name, obj, skip, options):
    """
    Sphinx autodoc-skip-member handler. Should be registered in the Sphinx
    conf.py via:

         def setup(app):
             app.connect('autodoc-skip-member', apidoc.docskip)
    """
    #print('=========', name)
    if inspect.ismodule(obj):
        return obj.__name__ not in documented_modules
    elif inspect.isclass(obj):
        return qualified_name(obj) not in documented_classes
    elif inspect.isfunction(obj) or inspect.ismethod(obj) or isinstance(obj, property):
        if qualified_name(obj) in functions_to_skip:
            return True
        else:
            return skip
    else:
        return skip