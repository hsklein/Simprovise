#===============================================================================
# MODULE mockqt
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines mock stand-ins for the Qt QObject and Signal objects, to be used
# in place of the real thing when client code is operating in an environment
# without PySide. Typically used as follows:
#
#    try:
#        from PySide.QtCore import QObject, Signal
#    except ImportError:
#        from mockqt import MockQObject as QObject
#        from mockqt import MockSignal as Signal
#===============================================================================

class MockQObject(object):
    """
    A mock stand-in for QObject (that does nothing). Intended for use by classes
    that emit and/or are connected to signals, but use no other QObject
    functionality. Does not actually provide dummy implementations for any
    QObject methods.
    """
    def __init__(self, parent=None):
        ""

class MockSignal(object):
    """
    A mock stand-in for a Qt Signal, that provides no-op emit() and connect()
    methods.
    """
    def __init__(*args):
        ""
        
    def connect(*args, **kwargs):
        pass

    def emit(*args, **kwargs):
        pass
