#===============================================================================
# MODULE datacollector
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the Dataset and SimDataCollector class.
#===============================================================================
__all__ = ['SimDataCollector',
           'SimUnweightedDataCollector', 'SimTimeWeightedDataCollector']

from abc import ABCMeta, abstractmethod

from simprovise.core import simtime, SimError
from simprovise.core.simclock import SimClock
from simprovise.core.simlogging import SimLogging
from simprovise.core.datasink import DataSink, NullDataSink
from simprovise.core.apidoc import apidoc, apidocskip

logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "Sim DataCollector Error"

@apidoc
class Dataset(object):
    """
    Encapsulates a set of measurements (of a specific value) to be collected
    by the simulation for a single simulation element
    (:class:`~.element.SimElement`).  Includes the
    :class:`~.simelement.SimElement` (the simulation object - resource,
    location, entity process, etc) - being measured, the type of data being
    collected (e.g. Queue size), the :class:`DataSink` object that these
    measurement values should be directed into, and the
    :class:`SimDataCollector` that acts as the collection interface to
    the outside world.
    
    Also defines methods that tell the element to start or stop collecting data.

    Note:

        Datasets are instantiated by :class:`SimDataCollector` and should
        not be created directly by (or even accessed) client modeling code.

    See also class :class:`SimDataCollector` for a more complete description of
    interaction between data collectors, datasets and datasinks.
    
    :param element:        The data collection element for which data are to
                           be collected. Can also be specified as a class
                           (e.g. SimProcess subclass) that has a
                           :class:`~.simelement.SimClassElement` associated
                           with it
    :type element:         :class:`~.simelement.SimElement` or `class`
    
    :param name:           The name of the dataset. Dataset names must be
                           non-null and unique within the element.
    :type name:            `str`
    
    :param datacollector:  The data collector associated with this dataset
    :type datacollector:   :class:`~.datacollector.SimDatacollector`     
    
    :param valueType:      The Python numeric type of the data values
                           collected, or :class:`simtime.SimTime`
    :type valueType:       `int`, `float` or :class:`~.simtime.SimTime`
   
    :param isTimeWeighted: If True, the data values collected represent
                           state and will be weighted by time in that state.                          
    :type isTimeWeighted:  `bool`
     
    """
    __slots__ = ('__element', '__dataCollector', '__dataCollectionEnabled',
                 '__savedDatasink', '__name', '__valueType',
                 '__isTimeWeighted', '__batchNumber', '__timeUnit')

    def __init__(self, element, dataCollector, name, valueType, isTimeWeighted):
        assert element is not None, "Dataset element must be non-null"
        assert dataCollector is not None, "Dataset dataCollector must be non-null"
        assert name, "Dataset name must be non-null"
        
        if isinstance(element, type):
            # element is actually a class; it should be one that has an
            # element (SimClassElement) associated via class attribute
            # element
            cls = element
            try:                    
                element = cls.element
            except AttributeError:
                errstr = "Failure extracting element from class {0} - not a process or entity class?"
                raise SimError(_ERROR_NAME, errstr, cls)
        
        self.__element = element
        self.__dataCollector = dataCollector
        self.__dataCollectionEnabled = True
        self.__savedDatasink = None
        self.__name = name
        self.__valueType = valueType
        self.__isTimeWeighted = bool(isTimeWeighted)
        self.__timeUnit = None
        self.__batchNumber = None
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
    
    
    @property
    def data_collection_enabled(self):
        """
        :return: ``True`` if data collection is enabled for this dataset
                 AND it's parent :class:`~.simelement.SimElement`
        :rtype:  ``bool``
        """
        return self.__dataCollectionEnabled and self.element.data_collection_enabled
    
    def disable_data_collection(self):
        """
        Disable data collection for this dataset, and make sure the
        dataset's datasink is appropriately set for that state.
        """
        logger.info("Disabling data collection for dataset %s in element %s",
                    self.name, self.element.element_id)
        self.__dataCollectionEnabled = False


    @property
    def datasink(self):
        """      
        :return: The datasink that drains this dataset
        :rtype:  :class:`.datasink.DataSink`       
        """
        return self.__dataCollector.datasink

    @datasink.setter
    def datasink(self, newSink):
        """
        Sets the datasink. datasink is NOT set if data collection is
        disabled AND the new sink is not a NullDataSink - but if
        data collection is disabled, the non-null new sink is saved
        (to the __savedDatasink attribute) in case data collection is
        later enabled.
        """
        oldSink = self.datasink
        self.__dataCollector.datasink = newSink
        if self.__batchNumber is not None:
            oldSink.finalize_batch(self.__batchNumber)
            newSink.initialize_batch(self.__batchNumber)

    @apidocskip
    def flush(self):
        self.__dataCollector.datasink.flush()

    @apidocskip
    def initialize_batch(self, batchnum):
        """
        Should be invoked when starting a new batch within a simulation run.
        Updates the batch number and delegates to the datasink to perform
        sink-specific (typically database-specific) start-of-batch processing.
        """
        self.__batchNumber = batchnum
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
             
        self.datasink.finalize_batch(batchnum)


@apidoc
class SimDataCollector(metaclass=ABCMeta):
    """
    SimDataCollectors collect numeric or state data (including
    :class:`~.simtime.SimTime` data) during a simulation run.
    SimDataCollector works in tandem with :class:`Dataset`; SimDataCollector
    objects each have an associated dataset object, which, coupled with
    a datasink object, are used to collect, store and eventually process 
    simulation output data.

    Essentially, the roles are as follows:

    - :class:`SimDataCollector` provides the data collection interface to
      modeling elements (class :class:`~.element.SimElement`) such as
      processes and resources.

    - :class:`Dataset` objects encapsulate output metadata, for use
      primarily by the output data collection subsystem.

    - :class:`~.datasink.Datasink` is an abstract class defining the interface
      to the output data collection subsystem; concrete subclasses implement
      that interface, which is used by data collectors - i.e., simulation
      data are sent from modeling elements to data collectors, which then
      send them on to data sinks. Plugging in different datasink types allows
      us to use different data stores, vary the amount/type of data collected,
      or to turn off data collection entirely for datasets we are not interested
      in. There are separate datasink classes for time-weighted and
      unweighted data

    `SimDataCollector` is an abstract base class; client code should instantiate
    one of its subclasses, either :class:`SimTimeWeightedDataCollector` or
    :class:`SimUnweightedDataCollector` (which are in fact different
    parameterizations of `SimDataCollector`)
    """
    __slots__ = ('__dataset', '__datasink', '__entries')
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

    def __init__(self, element, datasetName, datasetValueType, isTimeSeriesDataset):
        """
        Initialize the entries and datasink members. If an element is specified, also
        create a dataset.
        """
        self.__entries = 0
        self.__datasink = NullDataSink()
        dset = None
        if element is not None:                
            dset = Dataset(element, self, datasetName, datasetValueType, isTimeSeriesDataset)
        self.__dataset = dset
        SimDataCollector.collectorList.append(self)

    @apidocskip
    def reset(self):
        "Reset the statistics and data collection, typically for a new batch"
        self.__entries = 0
 
    def add_value(self, newValue):
        """
        Add a new value to the dataset if data collection is enabled.
        """
        self.__entries += 1
        if self.dataset.data_collection_enabled:            
            self.datasink.put(newValue)

    @property
    def name(self):
        "The data collector's dataset name"
        if self.__dataset is not None:
            return self.__dataset.name
        else:
            return None

    @apidocskip
    def entries(self):
        "Number of collected data values"
        return self.__entries
    
    @property
    def dataset(self):
        "Returns the dataset for the collector"
        return self.__dataset

    @property
    def datasink(self):
        "Returns the datasink for the collector"
        return self.__datasink

    @datasink.setter
    def datasink(self, newDatasink):
        "Set the datasink for the collector"
        self.__datasink = newDatasink
        
    def __str__(self):
        # entries is invalid for queues, stations, etc.
        return 'Entries:' + str(self.entries()) + ' Min:' + str(self.min()) + ' Max:' + str(self.max()) + ' Mean:' + str(self.mean())

@apidoc
class SimUnweightedDataCollector(SimDataCollector):
    """
    A :class:`SimDataCollector` that collects unweighted (non-time-weighted)
    data. Process time is a typical example of unweighted data.

    :param element:         The data collection element object for which
                            this object is collecting data. Can also specify
                            a class (e.g. SimProcess subclass) that has
                            a :class:`~.simelement.SimClassElement` associated
                            with it
    :type element:          :class:`~.simelement.SimElement` or `class`
    
    :param datasetNamename: The name of the  to-be-created dataset associated
                            associated with this collector. Must be unique
                            within the element.
    :type datasetNamename:  `str`
    
    :param datasetValueType: The (Python) type of the data being collected.                                
    :type datasetValueType:  `int`, `float` or :class:`~.simtime.SimTime`

    """
    # TODO should be no default values
    def __init__(self, element, datasetName, datasetValueType):
        super().__init__(element, datasetName, datasetValueType, False)


@apidoc
class SimTimeWeightedDataCollector(SimDataCollector):
    """
    A :class:`SimDataCollector` that collects time-weighted (time series)
    data, such as location population, resource utilization or
    work-in-process.

    :param element:         The data collection element object for which
                            this object is collecting data. Can also specify
                            a class (e.g. SimProcess subclass) that has
                            a :class:`~.simelement.SimClassElement` associated
                            with it
    :type element:          :class:`~.simelement.SimElement` or `class`
    
    :param datasetNamename: The name of the  to-be-created dataset associated
                            associated with this collector. Must be unique
                            within the element.
    :type datasetNamename:  `str`
    
    :param datasetValueType: The (Python) type of the data being collected.                                
    :type datasetValueType:  `int`, `float` or :class:`~.simtime.SimTime`
                             TODO state values

    """
    def __init__(self, element, datasetName, datasetValueType):
        super().__init__(element, datasetName, datasetValueType, True)
               

class NullDataCollector(SimDataCollector):
    "Implements the DataCollector interface with no-ops"
    
    def __init__(self):
        super().__init__(None, None, None, False)

    def add_value(self, newValue): pass

    def entries(self):
        return None

    def _add_value_impl(self, newValue): pass
