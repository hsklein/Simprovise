#===============================================================================
# MODULE simtrace
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines simulation event tracing functions and related classes/data
#
# This program is free software: you can redistribute it and/or modify it under 
# the terms of the GNU General Public License as published by the Free Software 
# Foundation, either version 3 of the License, or (at your option) any later 
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#==============================================================================
from collections import namedtuple
from enum import Enum
import inspect, sys, os
from simprovise.core.apidoc import apidoc, apidocskip
import simprovise.core.configuration as simconfig
from simprovise.core import SimError
from simprovise.core.simclock import SimClock
from simprovise.core.simlogging import SimLogging

logger = SimLogging.get_logger(__name__)
 
_ERROR_NAME = "Trace Error"
_DEFAULT_FMT_WIDTH = 20
_ACTION_FMT_WIDTH = 9
_CLOCKTIME_FMT_WIDTH = 10
_TRACE_SUFFIX = '_trace'

class TraceType(Enum):
    """
    The supported types of event tracing:
    TABLE - writes a formatted table of events/column values to stdout
    CSV   - writes the same data to a CSV file (with the same filename
            as the model script)
            
    TODO: Support for additional trace types and/or pluggable/configurable
         trace types facilitating functions such as animation.
    """
    TABLE = 0
    CSV = 1
        
class Action(Enum):
    """
    Enumeration of the actions that can be traced via :func:`trace_event`
    The basic events are:
    
    <entity> MOVE_TO <location>
    <resource> MOVE_TO <location>     (for moveable resources)
    <entity> ACQUIRING <resource(s)>  (resources have been requested)
    <entity> ACQUIRED <resource(s)>  (resources have been acquired/assigned)
    <entity> RELEASE <resource(s)>
    <resource> DOWN
    <resource> UP
    
    """
    MOVE_TO = 'Move-to'
    ACQUIRING = 'Acquiring'
    ACQUIRED = 'Acquired'
    RELEASE = 'Release'
    DOWN = 'Down'
    UP = 'Up'
     
# Set enabled, trace type, max events and trace output destination
# via configuration 
_trace_enabled = simconfig.get_trace_enabled()
if _trace_enabled: logger.info("Event Tracing enabled")
else: logger.info("Event Tracing disabled")

_trace_type = TraceType.TABLE
if simconfig.get_tracetype() == 'csv':
    trace_type = TraceType.CSV
if _trace_enabled:
    logger.info("Event Trace Type: %s", _trace_type)

# If not None/zero, Cut trace off at this many events
_trace_max_events = simconfig.get_trace_maxevents()
if _trace_enabled:
    logger.info("Maximum number of events to trace: %d", _trace_max_events)

# If the configuration specifies that trace be written to stdout, set
# the trace file to that. Otherwise, it will get set/opened by initialize()
_trace_file = None
if simconfig.get_trace_destination() == 'stdout':
    _trace_file = sys.stdout
if _trace_enabled:
    logger.info("Trace output destination: %s", simconfig.get_trace_destination())
     
_trace_initialized = False
_trace_event_count = 0
_object_fmt_width = _DEFAULT_FMT_WIDTH
_argument_fmt_width = _DEFAULT_FMT_WIDTH
_trace_columns = []

# TraceType-specific functions, set by initialize()
_header_func = None
_write_event_func = None

@apidocskip
def trace(func):
    """
    Decorator for trace_event() and other model-called tracing functions,
    returning a no-op function instead if tracing is disabled.
    """
    def no_op(*args, **kwargs):
         pass
    if _trace_enabled:
        return func
    else:
        return no_op
     
    
def initialize(modelscript_filename=None):
    """
    Initialize the trace (if tracing is enabled)
    
    Sets the header and write_event functions based on the TraceType.
    
    If the TraceType involves writing to an output file (both TABLE and
    CSV) AND the trace_file has not yet been specified (via
    :func:`set_trace_stdout`), open a new output file based on the
    passed modelscript filename, using an extension based on the
    trace type ('txt' for TABLE, 'csv' for CSV). If the modelscript
    filename is not specified, the output goes to stdout regardless.
    
    :param modelscript_filename: The filename of the model python script
    :type modelscript_filename:  `str`
    
    """
    if not _trace_enabled:
        return
    
    global _trace_file
    global _header_func
    global _write_event_func
    global _trace_initialized
    
    if _trace_initialized:
        return

    trace_ext = None

    if _trace_type == TraceType.TABLE:
        _header_func = _write_trace_table_header
        _write_event_func = _write_trace_event_to_table
        trace_ext = ".txt"
        
    elif _trace_type == TraceType.CSV:
        _header_func = _write_trace_csv_header
        _write_event_func = _write_trace_event_to_csv
        trace_ext = ".csv"
         
    if trace_ext and _trace_file is None:
        # The tracetype involves writing to a file, and it hasn't already been
        # set (presumably to stdout)
        if modelscript_filename:
            base = os.path.splitext(os.path.basename(modelscript_filename))[0]
            trace_filename = base + _TRACE_SUFFIX + trace_ext
            try:
                _trace_file = open(trace_filename, 'w')
            except Exception as e:
                logger.fatal("Error opening trace file: %s: %s",
                             trace_filename, e)
                raise SimError(_ERROR_NAME, "Unable to open trace file") from e
        else:
            # No modelscript filename, so write to stdout
            _trace_file = sys.stdout
         
    _trace_initialized = True
                       
def finalize():
    """
    Cleanup the trace if trace is enabled. For csv files, close the file.
    """
    if not _trace_enabled:
        return
    
    global _trace_file
    if _trace_file and _trace_file is not sys.stdout and _trace_file is not sys.stderr:
        logger.info("closing trace file...")
        _trace_file.close()
    _trace_file = None
    
class Column(namedtuple('Column', ['colname', 'element', 'elementname', 'property', 'propertyname'])):
    """
    NamedTuple defining an optional column in the event trace output table.
    An optional column is a simulation element property value shown along with
    the event data for each traced event.
    
    :param colname:       The column header for the event trace output table,
                          or None if the default is to be used
    :type colname:        `str`
    
    :param element:       The simulation element object whose property values 
                          are to be dsiplayed in this column
    :type element:        :class:`~.simelement.SimElement`
    
    :param elementname:   The name of the simulation element - it's `element_id`
    :type elementname:    `str`
    
    :param property:      The simulation element property whose values are to
                          be shown in the column
    :type property:       `property` object
    
    :param propertyname:  The name of the property
    :type propertyname:   `str`

    """
    __slots__ = ()
    
    def name(self):
        """
        Returns the column header name to be used for this Column;
        either the supplied colname value of the object/property name
        by default.
        """
        if self.colname is None:
            return "{0}:{1}".format(self.elementname, self.propertyname)
        else:
            return self.colname
   
    def value(self):
        """
        Returns the current simulation element property value
        """
        return self.property.fget(self.element)
    
    def __str__(self):
        return "{0}: {1:8}".format(self.name(), self.value())


@apidoc
def add_trace_column(element, propertyname, colname=None):
    """
    Add a column to the event trace output table. Each column is a property
    value for a specified simulation element.
    
   :param element:      The simulation element object owning the property
                        values to be shown in the colname
   :type element:       :class:`~.simelement.SimElement`
    
   :param propertyname: The name of the property whose values are to be
                        shown in the column. 
   :type propertyname:  `str`
   
   :param colname:      The table column heading. Defaults to
                        element_id.propertyname. 
   :type colname:       `str`
    
    """
    prop = [p for name, p in inspect.getmembers(element.__class__)
            if name == propertyname][0]
    col = Column(colname, element, element.element_id, prop, propertyname)
    _trace_columns.append(col)



class Event(namedtuple('Event', ['simtime', 'object', 'action', 'arguments'],
                       defaults=[0, None, None, ''])):
    """
    NamedTuple defining a simulation event to be traced/written to the event
    trace output table.
    
    :param simtime:   The simulated time that the event took place
    :type simtime:    :class:`~.simtime.SimTime`
    
    :param object:    The simulation object that is the focus of this
                      event, typically an entity or resource
    :type object:     :class:`~.entity.SimEntity` or :class:`~.resource.SimResource`
    
    :param action:    The action that is the focus of this event
    :type action:     :class:`Action`
    
    :param arguments: An iterable of zero or more objects also defining the event
    :type arguments:  An iterable of simulation objects

    """
    __slots__ = ()
    def arguments_to_str(self):
        """
        Format and return the arguments value as a string
        """
        argstr = ''
        n_arguments = len(self.arguments)
        if n_arguments == 1:
            argstr = self.arguments[0]
        elif n_arguments > 1:
            argset = set(self.arguments)
            for arg in argset:
                count = self.arguments.count(arg)
                if count == 1:
                    argstr += "{0} ".format(arg)
                else:
                    argstr += "{0} ({1}) ".format(arg, count)
        return argstr
    
    def __str__(self):
        """
        Output the event formatted for the non-csv event trace output source
        """               
        estr = "{0:{w0}.2f} {1!s:{w1}} {2:{w2}} {3!s:{w3}}"
        return estr.format(self.simtime, self.object, self.action.value,
                           self.arguments_to_str(), 
                           w0=_CLOCKTIME_FMT_WIDTH, 
                           w1=_object_fmt_width,
                           w2=_ACTION_FMT_WIDTH,
                           w3=_argument_fmt_width)

def _set_fmt_widths():
    """
    Helper function to set the global event object and argument widths for
    trace event table formatting.
    """
    global _object_fmt_width
    global _argument_fmt_width
    from simprovise.core.model import SimModel
    
    entity_classes = [e.element_class for e in SimModel.model().entity_elements]
    _object_fmt_width = max([len(cls.__name__) for cls in entity_classes])  + 6
    _argument_fmt_width = max([len(element.element_id)
                               for element in SimModel.model().static_objects]) * 2 + 6

def trace_event(obj, action, arguments=''):
    """
    If tracing is enabled, write the passed object, action and argument(s) as a
    :class:`simtrace.Event` to the event trace output, either a formatted table
    or as comma separated values. If this is the first event to be written,
    write the table/file header first.
    
    TODO: More refactoring for multiple tracing options. trace_event() should 
    eventually be usable for other puposes, such asbe piping data to an
    animator.
    
    :param obj:    The simulation object that is the focus of this
                      event, typically an entity or resource
    :type obj:     :class:`~.entity.SimEntity` or :class:`~.resource.SimResource`
    
    :param action:    The action that is the focus of this event
    :type action:     :class:`Action`
    
    :param arguments: An iterable of zero or more objects also defining the event.
                      Defaults to empty.
    :type arguments: An iterable of simulation objects
    
    """
    if not _trace_enabled:
        return
    
    global _trace_event_count
    
    if _trace_max_events and _trace_event_count >= _trace_max_events:
        return
    
    _trace_event_count += 1
    if _trace_event_count == 1:
        _header_func()
     
    evt = Event(SimClock.now().to_scalar(), obj, action, arguments)
    _write_event_func(evt)

     
def _write_trace_table_header():
    """
    Write the formatted trace table  header row
    """
    _set_fmt_widths()
    event_fmt_width = _object_fmt_width + _ACTION_FMT_WIDTH + _argument_fmt_width + 4
    table_width = event_fmt_width + _CLOCKTIME_FMT_WIDTH
    
    print("{0:>{width}}".format("Time", width=_CLOCKTIME_FMT_WIDTH),
          end='', file=_trace_file)
    print("{0:{width}}".format("", width=event_fmt_width),
          end="", file=_trace_file)
    for col in _trace_columns:
         print("{0}".format(col.name()), end=' ', file=_trace_file)
         table_width += len(col.name()) + 1
         
    print('\n{0:=^{w}}'.format('', w=table_width), file=_trace_file)
     
def _write_trace_event_to_table(evt):
    """
    Write a passed trace event to the formatted table
    """
    print(evt, end=' ', file=_trace_file)
    for col in _trace_columns:
        colwidth = len(col.name()) + 1
        w1 = int(colwidth / 2)
        w2 = colwidth - w1
        print("{0:-{w1}}{1:{w2}}".format(col.value(), '', w1=w1, w2=w2),
              end=' ', file=_trace_file)
    print('', file=_trace_file)
     
     
def _write_trace_csv_header():
    """
    Write the csv column header row
    """
    print("Time", "Object", "Action", "Arguments",
          sep=',', end='', file=_trace_file)
    for col in _trace_columns:
         print('', col.name(), sep=',', end='', file=_trace_file)
    print('', file=_trace_file)
     
def _write_trace_event_to_csv(evt):
    """
    Write a passed trace event and columns as comma separated values
    """
    print(evt.simtime, evt.object, evt.action.value, evt.arguments_to_str(),
          sep=',', end='', file=_trace_file)
    
    for col in _trace_columns:
        print(',', col.value(), sep=' ', end='', file=_trace_file)
    print('', file=_trace_file)
          
 
#if __name__ == '__main__':

