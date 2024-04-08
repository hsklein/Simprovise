#===============================================================================
# MODULE datasink
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the NullDataSink class (and by extension,  datasink interface)
#
# Various classes in the datacollector module (Dataset and aggregate classes)
# direct simulation output data values into datasink objects, which "absorb"
# output data for a single simulation dataset.  (Each dataset generally
# corresponds to a single measure on a single simulation object.)
#
# The Core datacollector module objects assume that each datasink supports
# the following methods:
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
# TODO: Currently every datasink in the simulation model is replaced by a
# non-null datasink prior to the start of a simulation run.  We would eventually
# like to be able to configure which datasets should collect data (and which
# should not), in order to optimize execution time and the amount of simulation
# output.  At that point, we may find that the NullDataSink requires additional
# stub methods.
#===============================================================================

class NullDataSink(object):
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