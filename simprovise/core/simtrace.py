#===============================================================================
# MODULE simtrace
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines simulation event tracing functions and related classes/data
#==============================================================================
from collections import namedtuple
from enum import Enum
import inspect
from simprovise.core import SimClock
from simprovise.core.apidoc import apidoc, apidocskip
 
_DEFAULT_FMT_WIDTH = 20
_ACTION_FMT_WIDTH = 9
_CLOCKTIME_FMT_WIDTH = 10

# TODO set this via configuration and/or environment variable
_trace_enabled = False

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
 

_trace_columns = []

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
    
class Action(Enum):
     """
     Enumeration of the actions that can be traced via :func:`trace_event`
     """
     MOVE_TO = 'Move-to'
     ACQUIRING = 'Acquiring'
     ACQUIRED = 'Acquired'
     RELEASE = 'Release'
     DOWN = 'Down'
     UP = 'Up'


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
     def __str__(self):
          """
          Output the event formatted for the non-csv event trace output source
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
               
          estr = "{0:{w0}.2f} {1!s:{w1}} {2:{w2}} {3!s:{w3}}"
          return estr.format(self.simtime, self.object, self.action.value, argstr, 
                             w0=_CLOCKTIME_FMT_WIDTH, 
                             w1=_object_fmt_width,
                             w2=_ACTION_FMT_WIDTH,
                             w3=_argument_fmt_width)

_trace_initialized = False
_object_fmt_width = _DEFAULT_FMT_WIDTH
_argument_fmt_width = _DEFAULT_FMT_WIDTH

def _set_fmt_widths():
     """
     Helper function to set the global event object and argument widths for
     trace event table formatting.
     """
     global _object_fmt_width
     global _argument_fmt_width
     from simprovise.core import SimModel
     
     entity_classes = [e.element_class for e in SimModel.model().entity_elements]
     _object_fmt_width = max([len(cls.__name__) for cls in entity_classes])  + 6
     _argument_fmt_width = max([len(element.element_id)
                                for element in SimModel.model().static_objects]) * 2 + 6

@trace
def trace_event(obj, action, arguments=''):
     """
     If tracing is enabled, write the passed object, action and argument(s) as a
     :class:`simtrace.Event` to the event trace output table. If this is the first
     event to be written, initialize format widths and the table headers first.
     
     TODO: Refactor for multiple tracing options. A csv file en liue of formatted
     standard output is the next obvious option. longer term, trace_event() should 
     be useable to pipe data to an animation process.
     
     :param obj:    The simulation object that is the focus of this
                       event, typically an entity or resource
     :type obj:     :class:`~.entity.SimEntity` or :class:`~.resource.SimResource`
     
     :param action:    The action that is the focus of this event
     :type action:     :class:`Action`
     
     :param arguments: An iterable of zero or more objects also defining the event.
                       Defaults to empty.
     :type arguments: An iterable of simulation objects
     
     """
     global _trace_initialized
     if not _trace_initialized:
          _set_fmt_widths()
          event_fmt_width = _object_fmt_width + _ACTION_FMT_WIDTH + _argument_fmt_width + 4
          table_width = event_fmt_width + _CLOCKTIME_FMT_WIDTH
          
          print("{0:>{width}}".format("Time", width=_CLOCKTIME_FMT_WIDTH), end='')
          print("{0:{width}}".format("", width=event_fmt_width), end="")
          for col in _trace_columns:
               print("{0}".format(col.name()), end=' ')
               table_width += len(col.name()) + 1
               
          print('\n{0:=^{w}}'.format('', w=table_width))
          _trace_initialized = True
      
     evt = Event(SimClock.now().to_scalar(), obj, action, arguments)
     print(evt, end=' ')
     for col in _trace_columns:
          colwidth = len(col.name()) + 1
          w1 = int(colwidth / 2)
          w2 = colwidth - w1
          print("{0:-{w1}}{1:{w2}}".format(col.value(), '', w1=w1, w2=w2), end=' ')
     print()
          
 
if __name__ == '__main__':
     from simprovise.core import (SimEntity, SimEntitySource, SimProcess,
                                  SimLocation, SimSimpleResource)
     import inspect
     
     source = SimEntitySource("MockSource")
     process = SimProcess()
     entity = SimEntity(source, process)
     loc = SimLocation("TestLocation")
     rsrc1 = SimSimpleResource("TestResource1", loc)
     rsrc2 = SimSimpleResource("TestResource2", loc)
     _set_fmt_widths()
     
     print(_object_fmt_width, _argument_fmt_width)
          
     add_trace_column(loc, 'current_population', 'Location Population')
     add_trace_column(loc, 'entries')
     trace_event(entity, Action.MOVE_TO, [loc])
     trace_event(entity, Action.ACQUIRED, (rsrc1, rsrc2))
     trace_event(entity, Action.ACQUIRED, (rsrc1, rsrc1))
     

     
     
    

