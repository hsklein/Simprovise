#===============================================================================
# MODULE datacollector
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the Dataset and SimDataCollector class.
#===============================================================================
__all__ = ['SimDataCollector',
           'SimUnweightedDataCollector', 'SimTimeWeightedDataCollector']

from simprovise.core import (SimClock, simtime, SimLogging, SimError)
from simprovise.core.datasink import NullDataSink
from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "Sim DataCollector Error"

@apidoc
class Dataset(object):
    """
    Encapsulates a set of measurements (of a specific value) to be collected
    by the simulation.  Includes the element (the simulation object - resource,
    process or counter - being measured, the type of data being collected
    (e.g. Queue size), and the DataSink object that these measurement values
    should be directed into.  Also defines methods that tell the element to start
    or stop collecting data.

    Note:

        Core Datasets are instantiated by :class:`SimDataCollector` and should
        not be created directly by (or even accessed) client modeling code.

    See :class:`SimDataCollector` for a more complete description of
    interaction between data collectors, datasets and datasinks.
    """
    __slots__ = ('__element', '__dataCollector', '__name', '__valueType',
                 '__isTimeWeighted', '__isCollectingData', '__batchNumber',
                 '__datasink', '__timeUnit')

    def __init__(self, element, dataCollector, name, valueType, isTimeWeighted):
        # TODO all parameters should be non-null. registerDataset() should
        # raise if the dataset name is a duplicate
        # TODO timeunit is currently hardwired to seconds.  Other code 
        # (e.g dbDatasink)  still assumes data in seconds, so a fix for this 
        # cascades to a number of places
        self.__element = element
        self.__dataCollector = dataCollector
        self.__name = name
        self.__valueType = valueType
        self.__isTimeWeighted = isTimeWeighted
        self.__timeUnit = None
        self.__isCollectingData = True
        self.__batchNumber = None
        self.__datasink = NullDataSink()
        self.__dataCollector.datasink = self.__datasink
        self.__element.register_dataset(self)

    @property
    def element(self):
        """
        The simulation element (e.g. process, resource, counter) associated with this dataset
        """
        return self.__element

    @property
    def element_id(self):
        """
        The ID of the simulation element
        """
        return self.__element.element_id

    @property
    def name(self):
        """
        The name of this dataset
        """
        return self.__name

    @property
    def valuetype(self):
        """
        The type (int, float or SimTime) of the dataset's values.
        """
        return self.__valueType

    @property
    def is_time_weighted(self):
        """
        True if the dataset is collecting time series values - i.e., their
        analysis will weight them by time.  Typically applies to counters.
        """
        return self.__isTimeWeighted

    @property
    def timeunit(self):
        """
        dataset time unit. This should always be the same as the model
        base time unit; if it's not, that indicates that the base unit got
        changed after the dataset was created, which we want to avoid.
        (It might be recoverable if we haven't put any data values in yet,
        but better safe than sorry.)
        
        We lazily initialize, to allow models to 
        """
        if self.__timeUnit is None:
            self.__timeUnit = simtime.base_unit()
            
        assert self.__timeUnit == simtime.base_unit(), "Base Time Unit modified after dataset and owning object created"
        return self.__timeUnit

    #@timeunit.setter
    #def timeunit(self, val):
        #"""
        #TODO For now, everything assumes seconds, so raise if it's something
        #else
        #"""
        #if val is not SimTime.seconds:
            #raise SimError(_ERROR_NAME, "SimTime unit other than seconds not yet implemented")
        #self.__timeUnit = val

    @property
    def datasink(self):
        """The datasink that drains this dataset"""
        return self.__datasink

    @datasink.setter
    def datasink(self, newSink):
        oldSink = self.__datasink
        self.__datasink = newSink
        if self.__isCollectingData:
            self.__dataCollector.datasink = newSink
            if self.__batchNumber is not None:
                oldSink.finalize_batch(self.__batchNumber)
                newSink.initialize_batch(self.__batchNumber)

    @apidocskip
    def flush(self):
        if self.__isCollectingData:
            self.__dataCollector.datasink.flush()

    @apidocskip
    def initialize_batch(self, batchnum):
        """
        Should be invoked when starting a new batch within a simulation run.
        Updates the batch number and delegates to the datasink to perform
        sink-specific (typically database-specific) start-of-batch processing.
        """
        self.__batchNumber = batchnum
        if self.__isCollectingData:
            self.datasink.initialize_batch(batchnum)

    @apidocskip
    def finalize_batch(self, batchnum):
        """
        Should be invoked when completing a batch (or completing a simulation
        run) - and if not the last batch, before calling initializeBatch() on
        the next batch.

        Delegates to the datasink to perform sink-specific end-of-batch
        processing.
        """
        if batchnum != self.__batchNumber:
            errstr = "finalizeBatch({0}) called on dataset when current batch is {1}"
            raise SimError(_ERROR_NAME, errstr, batchnum, self.__batchNumber)
        if self.__isCollectingData:
            self.datasink.finalize_batch(batchnum)

    def start_data_collection(self):
        "Tell the datacollector to start collecting data by passing it the datasink"
        if not self.__isCollectingData:
            self.__isCollectingData = True
            self.__dataCollector.datasink = self.datasink
            self.datasink.initialize_batch(self.__batchNumber)

    def stop_data_collection(self):
        "Tell the datacollector to stop collecting data by passing it a null datasink"
        if self.__isCollectingData:
            self.__isCollectingData = False
            self.datasink.finalize_batch(self.__batchNumber)
            self.__dataCollector.datasink = NullDataSink()


class UnweightedAggregate(object):
    "Produces un (not time) weighted statistics for aggregated data"
    __slots__ = ('__mean', '__entries', '__datasink')

    def __init__(self):
        self.__mean = None
        self.__entries = None
        self.initialize()
        self.__datasink = NullDataSink()

    def initialize(self):
        self.__mean = 0
        self.__entries = 0

    def reset(self):
        "reset for a new set of statistics"
        self.initialize()

    def initial_min_max_value(self):
        "Value used to initialize Min and Max of owning data collector after initialization or reset"
        return None

    def setDataSink(self, datasink):
        self.__datasink = datasink

    @property
    def datasink(self):
        return self.__datasink

    def __iadd__(self, value):
        "increment for a nonweighted sum"
        # source: http://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
        # (algorithm reference is Knuth, Welford)
        # TODO - add variance, per meanAndVariance() below?
        self.__entries += 1
        mean = self.__mean
        delta = value - mean
        mean += delta/self.__entries
        self.__mean = mean
        self.__datasink.put(value)
        return self

    def mean(self):
        "Mean collected data value"
        if self.__entries > 0:
            return self.__mean
        else:
            return None


class TimeWeightedAggregate(object):
    "Produces time-weighted statistics for aggregated data"
    __slots__ = ('__sum', '__initialTime', '__currentTime',
                 '__currentValue', '__initialValue', '__datasink')

    def __init__(self):
        self.__sum = None
        self.__initialTime = None
        self.__currentTime = None
        self.__currentValue = None
        self.__initialValue = None
        self.__datasink = NullDataSink()
        self.initialize(0)

    def initialize(self, initialValue=0):
        self.__initialTime = SimClock.now()
        self.__currentTime = SimClock.now()
        if self.__currentValue == None:
            self.__currentValue = initialValue
        self.__sum = 0
        self.__initialValue = initialValue

    def reset(self):
        "reset for a new set of statistics, leaving the current value as-is"
        self.initialize(self.__currentValue)

    def initial_min_max_value(self):
        "Value used to initialize Min and Max of owning data collector after initialization or reset"
        return self.__initialValue

    def setDataSink(self, datasink):
        self.__datasink = datasink
        datasink.put(self.__currentValue)

    @property
    def datasink(self):
        return self.__datasink

    def __iadd__(self, other):
        "increment for a time-weighted sum"
        # TODO adapt weighted incremental algorithm, per reference above
        now = SimClock.now()
        if self.__currentValue == None:
            self.__initialTime = now
        elif now > self.__currentTime:
            timeDiff = now - self.__currentTime
            self.__sum += timeDiff.to_scalar() * self.__currentValue

        self.__currentValue = other
        self.__currentTime = now
        self.__datasink.put(other)

        return self

    def mean(self):
        "Mean collected data value"
        # first update the sum with the latest value and time
        self.__iadd__(self.__currentValue)

        #calculate and return time-weighted mean
        timeDiff = self.__currentTime - self.__initialTime
        if timeDiff > 0:
            return float(self.__sum) / float(timeDiff.to_scalar())
        else:
            return None

@apidoc
class SimDataCollector(object):
    """
    SimDataCollectors collect numeric data (including :class:`~.simtime.SimTime` data)
    during a simulation run. SimDataCollector works in tandem with
    :class:`Dataset`; SimDataCollector instances each have an associated
    dataset instance, which, coupled with a datasink object, are used to
    collect, store and eventually process simulation output data.

    Essentially, the roles are as follows:

      `SimDataCollector` provides the data collection interface to modeling
      objects such as processes and resources.

      `Datasets` encapsulate output metadata, while providing the interface to
      the output data collection subsystem.

      `Datasinks` provide the implementation of the output data collection
      subsystem. Plugging in different datasink types allows us to use a
      different data store, vary the amount/type of data collected, or to turn
      off data collection entirely for datasets we are not interested in.

    `SimDataCollector` is essentially an abstract base class; client code
    should instantiate one of its subclasses, either
    :class:`SimTimeWeightedDataCollector` or
    :class:`SimUnweightedDataCollector`.
    """
    __slots__ = ('__dataset', '__aggregate', '__entries', '__min', '__max')
    collectorList = []

    # Class methods
    @classmethod
    @apidocskip
    def reinitialize(cls):
        "Reinitialize the class data by emptying the list of data collectors"
        cls.collectorList = []

    @classmethod
    @apidocskip
    def reset_all(cls):
        "Reset every collector in the class collectorList"
        for dc in cls.collectorList:
            dc.reset()

    def __init__(self, element, datasetName, datasetValueType, isTimeSeriesDataset, aggregate):
        """
        Initialize the min, max and aggregate members. If an element is specified, also
        create a dataset.
        """
        # TODO all parameters should be non-null
        self.__entries = None
        self.__min = None
        self.__max = None
        self.__aggregate = aggregate
        dset = None
        if element is not None:
            dset = Dataset(element, self, datasetName, datasetValueType, isTimeSeriesDataset)
        self.__dataset = dset
        self.initialize()
        SimDataCollector.collectorList.append(self)

    @apidocskip
    def initialize(self):
        "Initialize (or re-initialize) raw data collectors"
        self.__entries = 0
        self.__aggregate.initialize()
        self.__min = self.__aggregate.initial_min_max_value()
        self.__max = self.__aggregate.initial_min_max_value()

    @apidocskip
    def reset(self):
        "Reset the statistics and data collection, typically for a new batch"
        self.__entries = 0
        self.__aggregate.reset()
        self.__min = self.__aggregate.initial_min_max_value()
        self.__max = self.__aggregate.initial_min_max_value()

    def add_value(self, newValue):
        """
        Add a new value to the dataset.
        """
        # TODO stop collecting min, max, mean
        if self.__max is None:
            self.__max = newValue
        else:
            self.__max = max(newValue, self.__max)

        if self.__min is None:
            self.__min = newValue
        else:
            self.__min = min(newValue, self.__min)

        self.__entries += 1
        self.__aggregate += newValue

    @property
    def name(self):
        "The data collector's dataset name (if any)"
        return self.__dataset.name

    @apidocskip
    def min(self):
        "Minimum collected data value"
        return self.__min

    @apidocskip
    def max(self):
        "Maximum collected data value"
        return self.__max

    @apidocskip
    def entries(self):
        "Number of collected data values"
        return self.__entries

    @apidocskip
    def mean(self):
        "Mean collected data value"
        return self.__aggregate.mean()
    
    @property
    def dataset(self):
        "Returns the dataset for the collector"
        return self.__dataset

    @property
    def datasink(self):
        "Returns the datasink for the collector"
        return self.__aggregate.datasink

    @datasink.setter
    def datasink(self, newDatasink):
        "Set the datasink for the collector (delegates to aggregate)"
        self.__aggregate.setDataSink(newDatasink)

    def __str__(self):
        # entries is invalid for queues, stations, etc.
        return 'Entries:' + str(self.entries()) + ' Min:' + str(self.min()) + ' Max:' + str(self.max()) + ' Mean:' + str(self.mean())

@apidoc
class SimUnweightedDataCollector(SimDataCollector):
    """
    SimDataCollector that collects unweighted (non-time-weighted) data.
    Process time is a typical example of unweighted data.

    Args:
        element:                 The data collection element object for which
                                 this object is collecting data
        datasetNamename (str):  The name of the  to-be-created dataset associated
                                 associated with this collector. Must be unique
                                 within the element.
        datasetValueType (type): The (Python) type of the data being collected.
                                 Generally `int`, `float` or :class:`~.simtime.SimTime`
    """
    # TODO should be no default values
    def __init__(self, element=None, datasetName=None, datasetValueType=None):
        super().__init__(element, datasetName, datasetValueType, False, UnweightedAggregate())

@apidoc
class SimTimeWeightedDataCollector(SimDataCollector):
    """
    SimDataCollector that collects time-weighted (time series) data, such as
    location population, resource utilization or work-in-process.

    Args:
        element:                 The data collection element object for which
                                 this object is collecting data
        datasetNamename (str):  The name of the  to-be-created dataset associated
                                 associated with this collector. Must be unique
                                 within the element.
        datasetValueType (type): The (Python) type of the data being collected.
                                 Generally `int`, `float` or :class:`~.simtime.SimTime`
    """
    def __init__(self, element=None, datasetName=None, datasetValueType=None):
        super().__init__(element, datasetName, datasetValueType, True, TimeWeightedAggregate())

class NullDataCollector(object):
    "Implements the DataCollector interface with no-ops"

    def initialize(self): pass

    def add_value(self, newValue): pass

    def min(self):
        return None

    def max(self):
        return None

    def entries(self):
        return None

    def mean(self):
        return None
