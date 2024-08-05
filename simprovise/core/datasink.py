#===============================================================================
# MODULE datasink
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the DataSink abstract base class and the NullDataSink concrete
# subclass.
#
# You should have received a copy of the GNU General Public License along with 
# this program. If not, see <https://www.gnu.org/licenses/>.
#
# Various classes in the datacollector module (SimDataCollector subclasses)
# direct simulation output data values into datasink objects, which "absorb"
# output data for a single simulation dataset.  (Each dataset generally
# corresponds to a single measure on a single simulation object.)
#
# The DataSink class defines the following abstract methods:
#
#     put(value): typically adds a new output to the dataset
#     flush():    typically flushes transient data (e.g. to disk, when using
#                 an output database)
#
#    initialize_batch(batchnum): performs initialization tasks at the start of
#                                a new batch within a simulation run
#    finalize_batch(batchnum):   performs any needed cleanup tasks at the end of
#                                a batch within a simulation run
#
# The NullDataSink implements all of these methods as no-ops, along with a
# datasetID property that returns None.  The datacollector objects with
# datasink attributes use NullDataSink instances as the default value for those
# attributes.  "Real" datasink classes are defined in the output Database
# package, and replace the default null datasinks at run time.  These output
# database datasinks implement this interface, and more.  We've decided to
# rely on duck-typing here rather than an abstract interface.
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
from abc import ABCMeta, abstractmethod, abstractproperty

class DataSink(metaclass=ABCMeta):
    """
    A single :class:`~.simelement.SimElement` measurement is defined,
    collected, and has it's values directed to their final resting place
    via a triplet of :class:`~.datacollector.SimDataCollector`,
    :class:`~.datacollector.Dataset` and :class:`DataSink` objects.
    
    :class:`DataSink` is an abstract base class defining the DataSink interface.
    The central method is :meth:`put`, which data collectors call for each
    collected value.
    
    Datasinks in effect "absorb" dataset values; datasinks may write those
    values to a database, hold them for summarization, or simply eat them,
    as is the case with :class:`NullDataSink`. (That is one  way to turn
    off data collection for a specific single dataset.)
    """
    
    @abstractproperty
    def dataset_id(self):
        pass
    
    @abstractmethod
    def put(self, value):
        """
        Adds a new value to the :class:`.datacollector.Dataset`
        
        :param value: The value to add to the dataset.
        :type value:  The type/class of the dataset value, as defined by
                      :attr:`~.datacollector.Dataset.valuetype`
                      
        """
        pass

    @abstractmethod
    def flush(self):
        """
        Typically flushes transient data, e.g. to disk for an output database.
        """
        pass

    @abstractmethod
    def initialize_batch(self, batchnum):
        """
        Performs initialization tasks at the start of a new batch within a
        simulation run.
        """
        pass

    @abstractmethod
    def finalize_batch(self, batchnum):
        """
        Performs any needed cleanup tasks at the end of a new batch within a
        simulation run.
        """
        pass    
    
class NullDataSink(DataSink):
    "Implements the DataSink interface with no-ops"
    
    @property
    def dataset_id(self):
        return None

    def put(self, value):
        pass

    def flush(self):
        pass

    def initialize_batch(self, batchnum):
        pass

    def finalize_batch(self, batchnum):
        pass