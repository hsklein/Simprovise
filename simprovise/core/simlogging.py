#===============================================================================
# MODULE simlogging
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Sets up / configures Python logging, and provides access via static methods
# in a SimLogging class.
#===============================================================================
__all__ = ['SimLogging']

import logging, os
from simprovise.core.apidoc import apidoc, apidocskip

_BASE_LOGGER_NAME = __name__.rsplit('.')[0]

# Create the base logger for the library
_baseLogger = logging.getLogger(_BASE_LOGGER_NAME)
_baseLogger.setLevel(logging.INFO)

# Note vis-a-vis the UI
# This stream handler is (by default) directed to stderr.  The SimUI application
# (which starts up after this module is loaded and the below code executes)
# then redirects stderr to the UI.  The logging output from this handler does not,
# however, go to the UI - it continues going to the console.  Probably because
# it assigns the underlying destination of stderr before stderr is redirected.
# The solution is addHandler() below, which creates a new StreamHandler.  Whether
# that new handler is directed to stderr/stdout or explicitly to the UI output window,
# log messages handled by it go to the UI as intended.

_ch = logging.StreamHandler()
_formatter = logging.Formatter('%(name)s %(levelname)s:\t%(lineno)d\t%(message)s')
_ch.setFormatter(_formatter)
_baseLogger.addHandler(_ch)

# Determine if logging is to be completely disabled via environment variable
_DISABLE_LOGGING_ENV_NAME = _BASE_LOGGER_NAME + '_DISABLE_LOGGING'
_useNullLogger = False
           
if os.getenv(_DISABLE_LOGGING_ENV_NAME):
    _useNullLogger = True
    _baseLogger.info("SimLogging disabled")
else:
    _baseLogger.info("SimLogging initialized")
   

# TODO add ability to specify debug level via environment variable or other 
# configuration

@apidocskip
class NullLogger(object):
    """
    A Null object that can be used in place of a logging.logger if we
    want to disable logging in a more performant way.
    
    Note that we'd have to specify a flag to use this logger right about
    here in the module; any sort of set() method on SimLogger wouldn't
    work - most modules get their loggers right when they are imported,
    so swapping in a NullLogger via a SimLogging.setNullLogger() would
    have no effect unless we could be certain that it were called before
    importing anything that might (directly or indirectly) import
    SimLogger. And if core.__init__.py imports anything, those loggers
    are going to be created as soon as the calling script imports the
    simlogging module.
    
    Lifted from Python Essential Reference, 4th Edition (Beazley), p. 369
    """
    def __init__(self, *args, **kwargs): pass
    def __call__(self, *args, **kwargs): return self
    def __getattribute__(self, name): return self
    def __setattr__(self, name, value): pass
    def __delattr__(self, name): pass
    

@apidoc
class SimLogging(object):
    """
    A collection of convenience methods (all static methods) for accessing
    and configuring standard Python logging.
    """
    
    @staticmethod
    def get_logger(name, level=logging.NOTSET):
        """
        Create and optionally set the level for a new logger. Typically usage is:

            logger = SimLogging.getLogger(__name__)
            
        For modules within this package, that name will start with the base
        logger name so we use it directly. For other code, the base logger
        name is prepended so that all SimLogger-supplied loggers are below
        it in the hierarchy; SimLogging should never directly access the root
        logger.
        
        Note that if _useNullLogger is set, this just returns a NullLogger
        instance regardless of other parameter values.
            
        :param name:    Name of the logger, typically the name of the module
                        in which the logger is created
        :type name:     str               
        :param level:   logging level (DEBUG, INFO, WARN, etc.) as defined by
                        standard library logging module. Defaults to
                        logging.NOTSET
        :type level:    int
        
        :return:        logger or NullLogger instance 
        :rtype:         logging.logger
        """
        if _useNullLogger:
            return NullLogger()
        
        if name.rsplit('.')[0] != _BASE_LOGGER_NAME:
            name = _BASE_LOGGER_NAME + '.' + name
            
        logger = logging.getLogger(name)
        logger.setLevel(level)
        return logger

    @staticmethod
    def set_level(lvl, name=None):
        """
        Static method that sets a logger's logging level to a passed
        level (as defined by the standard library logging module). The
        passed name specifies the logger who's level should be set; if
        name is omitted/None, base logger's level is set.

        :param lvl: Numeric logging level. See standard library logging
                    module documentation for details.
        :type lvl:  int
        :param name: logger name (package or module) or None (default)
        :type name:  str or None
                
        """
        if name is None:
            name = _BASE_LOGGER_NAME
            
        assert name.rsplit('.')[0] == _BASE_LOGGER_NAME, "Non-application log name passed to setLevel()"
        
        logging.getLogger(name).setLevel(lvl)

    @staticmethod
    def get_level(name=None):
        """
        Return the level of a logger specified by name. If name
        is none, returns the level of the base logger.
        
        :param name: logger name (package or module) or None (default)
        :type name:  str or None
        
        :return:        logging level
        :rtype:         int
       
        """
        if name is None:
            name = _BASE_LOGGER_NAME
        return logging.getLogger(name).getEffectiveLevel()

    @apidocskip
    @staticmethod
    def add_handler(dest):
        """
        Add a StreamHandler directed to the passed destination. Can be used
        by a UI to direct log messages to an output window (instead or in
        addition to the console). For example, this could be used to direct
        logging output to a Qt Widget derived from a QtGui.QPlainTextEdit.

        :param dest: A destination object (e.g. a Qt Widget) that can
                     handle the logging output
        :type dest:  object
        
        """
        hdlr = logging.StreamHandler(dest)
        hdlr.setFormatter(_formatter)
        _baseLogger.addHandler(hdlr)

