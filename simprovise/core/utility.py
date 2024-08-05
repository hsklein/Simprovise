#===============================================================================
# MODULE utility
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines SimUtility class, which defines a collection of utility functions as
# static methods.
#
# This program is free software: you can redistribute it and/or modify it under 
# the terms of the GNU General Public License as published by the Free Software 
# Foundation, either version 3 of the License, or (at your option) any later 
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#===============================================================================
__all__ = ['SimUtility']
import inspect
import sys
import os
import importlib
import pkgutil
import glob
#import py_compile

# Will eventually be needed by loadModuleFromFile() see note
#import types
#import importlib.util
import urllib, urllib.request, urllib.parse

from simprovise.core import SimError
from simprovise.core.simlogging import SimLogging

logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "SimUtilityError"

class SimUtility(object):
    """
    Implements a namespace containing miscellaneous utility methods.
    """
    @staticmethod
    def getClass(qualifiedClassName):
        """
        Static method that imports and retrieve the class specified by a class name
        (qualified by module and/or package)
        """

        # The class name should, at a minimum, be qualified by a module name
        classNameComponents = qualifiedClassName.rsplit(".", 1)
        component0 = classNameComponents[0]
        if len(classNameComponents) < 2 or len(component0) == 0 or component0.isspace():
            raise SimError(_ERROR_NAME, "getClass error; className ({0}) must also include a module name", qualifiedClassName)

        # The class name itself should be non blank
        classComponent = classNameComponents[1]
        if len(classComponent) == 0 or classComponent.isspace():
            raise SimError(_ERROR_NAME, "getClass error; className ({0}) - class name is blank", qualifiedClassName)

        moduleSpec, className = classNameComponents

        try:
            mod = importlib.import_module(moduleSpec)
        except:
            raise SimError(_ERROR_NAME, "getClass error; unable to import {0}: package/module not found", qualifiedClassName)

        cls = getattr(mod, className, None)
        if not cls:
            raise SimError(_ERROR_NAME, "Class {0} not found", qualifiedClassName)
        if not inspect.isclass(cls):
            raise SimError(_ERROR_NAME, "Class {0} is not a class", qualifiedClassName)

        return cls

    @staticmethod
    def loadModule(moduleName, *, reload=False):
        """
        Imports the module (or package) as specified by passed (qualified)
        name. If the module has been previously imported AND the passed
        reload flag is True, then reload the module. (Useful for the package
        manager and SimElementRegistry, which might need to re-execute
        simelement decorators)
        """
        alreadyLoaded = moduleName in sys.modules
        try:
            if not alreadyLoaded:
                logger.info("loadModule importing module %s...", moduleName)
                module = importlib.import_module(moduleName)
            elif alreadyLoaded and reload:
                logger.info("loadModule reloading module %s...", moduleName)
                importlib.reload(sys.modules[moduleName])
                module = sys.modules[moduleName]
        except:
            raise SimError(_ERROR_NAME, "getClass error; unable to import {0}: package/module not found", moduleName)

        return module

    @staticmethod
    def getModuleNames(packageName):
        """
        Static method that imports and retrieve the class specified by a class name
        (qualified by module and/or package)
        """
        try:
            pkg = importlib.import_module(packageName)
        except:
            raise SimError(_ERROR_NAME, "getModuleNames error; unable to import {0}: package not found", packageName)

        path = pkg.__path__
        prefix = packageName + '.'
        print(path)
        modNames = [name for i, name, f in pkgutil.iter_modules(path, prefix)]
        return modNames

    @staticmethod
    def load_module_from_file(filepath, moduleName):
        """
        Loads the specified python script file, assigning it the passed module
        name (regardless of the filename).  Returns the module.

        The code comes directly from a python documentation recipe for
        importing a source file directly:
        https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly 
        """
        # Python 3.3 code. Deprecated in Python 3.4
        #loader = importlib.machinery.SourceFileLoader(moduleName, filepath)
        #exec(loader.get_code(loader.name))
        #module = loader.load_module()
        
        # The code below is from the following recipe:
        # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly     
        spec = importlib.util.spec_from_file_location(moduleName, filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[moduleName] = module
        spec.loader.exec_module(module)
        
        return module

    @staticmethod
    def getPackageName(dirpath):
        """
        If the passed directory path is a Python package (i.e. has an
        __init__ script, with .py* file extension), returns the full package
        name (including parent packages, if any)
        """
        assert os.path.isdir(dirpath), "Passed path is not a directory"

        # Check for existence of __init__.py* via glob() - since file can
        # have several possible extensions (.py, .pyc, .pyo)
        initPathGlob = os.path.join(dirpath, '__init__.py*')
        if glob.glob(initPathGlob):
            parentDir, packageName = os.path.split(dirpath)
            parentPackageName = SimUtility.getPackageName(parentDir)
            if parentPackageName:
                return ".".join([parentPackageName, packageName])
            else:
                return packageName
        else:
            return None

    @staticmethod
    def getModuleNameFromScript(scriptPath):
        """
        Returns the module name (i.e. filename) for a passed script path,
        qualified with a package identifier (if the script file is in
        a package, as indicated by the presence of an __init__.py file).

        The package identifier will include ancestor package names, if any.
        """
        assert os.path.isfile(scriptPath), "Passed path is not a file"
        scriptDir, basename = os.path.split(os.path.abspath(scriptPath))
        moduleName, ext = os.path.splitext(basename) # pylint: disable=unused-variable
        assert moduleName, "File (module) name not found"
        packageName = SimUtility.getPackageName(scriptDir)
        if packageName:
            moduleName = packageName + '.' + moduleName
        return moduleName

    @staticmethod
    def isUrl(urlorpath):
        """
        Returns True if the passed candidate URL specifies either the 'file'
        schema (starts with 'file:///') or specifies a network location
        (starts with '//'). Returns False otherwise.
        Note that this does NOT validate the URL in any way.
        """
        parsedURL = urllib.parse.urlparse(urlorpath)
        return parsedURL.path and (parsedURL.scheme == 'file' or
                                   parsedURL.netloc != '')

    @staticmethod
    def abspathToFileURL(abspath):
        """
        Convert a passed absolute path to a file URL
        """
        assert os.path.isabs(abspath), "Relative path passed to Simutility.abspathToFileURL()"
        # Convert abspath into an URL, and then add the 'file' schema to
        # the URL before returning it.
        urlwithoutschema = urllib.request.pathname2url(abspath)
        urlwithschema = urllib.parse.urljoin('file:', urlwithoutschema)
        return urlwithschema


