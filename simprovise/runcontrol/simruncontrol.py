#===============================================================================
# MODULE simruncontrol
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the replication and run control-related classes:
#    - SimRunControlParameters, SimReplicationParameters, which encapsulate
#      run and replication definition data
#    - SimRunControlScheduler, which schedules and handles simulation events
#      (WarmupComplete, BatchComplete and Progress) that trigger user interface
#      and/or output data collection logic at specified points during a
#      simulation run. The user interface events are triggered using Qt
#      signals; if operating in a non-GUI environment without PySide, the
#      Qt signals are replaced with mock objects that do nothing.
#    - SimWarmupCompleteEvent, SimBatchCompleteEvent an SimProgressEvent, which
#      implement the simulation events described above for the run control
#      scheduler.
#===============================================================================
import sys
import multiprocessing

# Use PySide if it is installed; otherwise replace with mock object classes
try:
    from PySide.QtCore import QObject, Signal
except ImportError:
    from simprovise.runcontrol.mockqt import MockQObject as QObject
    from simprovise.runcontrol.mockqt import MockSignal as Signal

from simprovise.core import SimDataCollector, SimClock, SimError
from simprovise.core import SimLogging, SimTime
from simprovise.core.simevent import SimEvent

logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "SimRunControl Error"

class SimRunControlParameters(object):
    """
    Manages simulation run control parameters - run number, warmup time, batch
    length, and the number of batches - used to define a single simulation run.
    (SimReplicationParameters manages parameters related to a set of replication
    runs.  These data are kept in separate classes because each replicated run
    requires its own SimRunControlParameters.)
    """
    def __init__(self, runNumber, warmupLength, batchLength, nBatches):
        """
        """
        self.set_run_number(runNumber)
        self.set_warmup_length(warmupLength)
        self.set_batch_length(batchLength)
        self.set_batch_count(nBatches)

    @property
    def warmup_length(self):
        """
        The length (in SimTime) of the simulation warmup.  Defaults to zero.
        """
        return self.__warmupLength

    @property
    def batch_length(self):
        """
        The length (in SimTime) of each simulation batch after the warmup completes.
        Defaults to infinite
        """
        return self.__batchLength

    @property
    def nbatches(self):
        """
        The number of batches (each of batchLength) to execute during the
        simulation run.  Defaults to one.
        """
        return self.__nBatches

    @property
    def run_number(self):
        """
        The specified simulation run number, which is varied when replicating
        a simulation using different random number streams.
        """
        return self.__runNumber

    # Set methods for run control parameters.  We use methods rather than
    # property setters so that these can be used as Qt slots

    def set_warmup_length(self, warmupLength):
        """
        Sets/changes the simulation warmup length.
        """
        try:
            self.__warmupLength = SimTime(warmupLength)
            assert self.__warmupLength >= 0, "Warmup length must be non-negative"
        except Exception as e:
            raise SimError(_ERROR_NAME, "Invalid warmup length: {0}", warmupLength)

    def set_batch_length(self, batchLength):
        """
        Sets/changes the simulation batch length.
        """
        try:
            self.__batchLength = SimTime(batchLength)
            assert self.__batchLength > 0, "Batch length must be greater than zero"
        except Exception as e:
            raise SimError(_ERROR_NAME, "Invalid batch length: {0}", batchLength)

    def set_batch_count(self, nBatches):
        """
        Sets/changes the number of simulation batches.
        """
        try:
            self.__nBatches = nBatches
            assert self.__nBatches > 0, "Batch count must be greater than zero"
        except Exception as e:
            raise SimError(_ERROR_NAME, "Invalid batch count: {0}", nBatches)

    def set_run_number(self, runNumber):
        """
        Sets/changes the simulation run number (typically set to > 1 when doing
        replication-based output analysis)
        """
        try:
            self.__runNumber = runNumber
            assert self.__runNumber > 0, "Run Number must be greater than zero"
        except Exception as e:
            raise SimError(_ERROR_NAME, "Invalid batch count: {0}", runNumber)


class SimReplicationParameters(object):
    """
    Manages simulation replication parameters - number of replications,
    starting run number for replications, the maximum number of
    replications to perform concurrently.
    """
    def __init__(self):
        """
        The default replication range is (1,1) - a single replication
        of run number 1. The default maximum number of concurrent
        replications is the CPU count, as obtained from the
        multiprocessing package; it defaults to one if that function
        is not implemented.
        """       
        self.__replicationRange = 1, 1
        try:
            self.__nConcurrentReplications = multiprocessing.cpu_count()
        except NotImplementedError:
            self.__nConcurrentReplications = 1

    @property
    def replication_range(self):
        """
        Returns the range of run numbers (first run, last run) for the
        simulations to be run during a replication analysis.
        Last run must be equal or greater than the first run.
        """
        return self.__replicationRange

    @property
    def max_concurrent_replications(self):
        """
        The maximum number of simulation replications to perform concurrently
        (when doing replication analysis).  Defaults to the number of CPU cores,
        as returned by multiprocessing.cpu_count().  If that function is not
        implemented, defaults to 1.
        """
        return self.__nConcurrentReplications

    def set_replication_range(self, startRunNumber, endRunNumber):
        """
        Set the replication range
        """
        if startRunNumber > endRunNumber:
            msg = "Replication start run ({0}) id greater than end run ({1})"
            raise SimError(_ERROR_NAME, msg, startRunNumber, endRunNumber)
        self.__replicationRange = startRunNumber, endRunNumber

    def set_max_concurrent_replications(self, value):
        """
        Set the number of concurrent replications allowed
        """
        self.__nConcurrentReplications = value


class SimRunControlScheduler(QObject):
    """
    """
    RunControlMessage = Signal(str)

    def __init__(self, model, runControlParameters, progressIntervalPct=None, *, msgQueue=None):
        super().__init__()
        assert not progressIntervalPct or (0 < progressIntervalPct and progressIntervalPct < 100), "Invalid progressInterval percentage"
        self.__model = model
        self.__runControlParameters = runControlParameters
        self.__progressIntervalPct = progressIntervalPct
        self.__msgQueue = msgQueue

    @property
    def model(self):
        return self.__model

    @property
    def warmup_length(self):
        return self.__runControlParameters.warmup_length

    @property
    def batch_length(self):
        return self.__runControlParameters.batch_length

    @property
    def nbatches(self):
        return self.__runControlParameters.nbatches

    @property
    def run_number(self):
        return self.__runControlParameters.run_number

    @property
    def run_length(self):
        return self.warmup_length + (self.batch_length * self.nbatches)

    def initialize_batch(self, batchNumber):
        """
        """
        for dset in self.model.datasets:
            dset.initialize_batch(batchNumber)

    def finalize_batch(self, batchNumber):
        """
        """
        for dset in self.model.datasets:
            dset.finalize_batch(batchNumber)

    def warmup_complete(self):
        """
        """
        logger.info("Warmup complete at %s", SimClock.now())
        SimDataCollector.reset_all()
        self.finalize_batch(0)
        self.initialize_batch(1)
        msg = "Warmup completed at simulated time {0}. Collecting statistics for "
        if self.nbatches > 1:
            msg += "Batch 1..."
        else:
            msg += "run..."
        formattedMsg = msg.format(SimClock.now())
        self.RunControlMessage.emit(formattedMsg)

    def batch_complete(self, batchNumber):
        logger.info("Batch %d complete at %s", batchNumber, SimClock.now())
        self.finalize_batch(batchNumber)
        if batchNumber < self.nbatches:
            self.initialize_batch(batchNumber + 1)
            SimDataCollector.reset_all()
            msg = "Simulation batch {0} completed at simulated time {1}; starting data collection for batch {2}..."
            formattedMsg = msg.format(batchNumber, SimClock.now(), batchNumber+1)
            self.RunControlMessage.emit(formattedMsg)
        else:
            msg = "Simulation run complete."
            self.RunControlMessage.emit(msg)

    def progress(self, progressPct):
        """
        """
        self._send_progress_message(progressPct)

    def _send_progress_message(self, pctComplete):
        if self.__msgQueue:
            self.__msgQueue.send_progress_message(pctComplete)

    def schedule_run_control_events(self):
        """
        Schedule warmup and batchComplete events, which reset statistics and output a
        messag to the status bar. (Also outputs a "Starting simulation" message
        """
        if self.warmup_length > 0:
            warmupCompleteEvent = WarmupCompleteEvent(self)
            warmupCompleteEvent.register()
            self.RunControlMessage.emit("Starting simulation warmup period...")
        else:
            self.RunControlMessage.emit("Starting simulation...")

        if self.batch_length > 0:
            batchCompleteEvent = BatchCompleteEvent(self)
            batchCompleteEvent.register()

        if self.run_length > 0 and self.__progressIntervalPct:
            progressEvent = SimProgressEvent(self, self.__progressIntervalPct)
            progressEvent.register()


class WarmupCompleteEvent(SimEvent):
    """
    An event that initiates warmup completion processing at the end of the
    specified simulation warmup.  The completion processing is invoked via
    a passed function, that may vary based on simulation mode.
    """
    def __init__(self, runControlScheduler):
        super().__init__(runControlScheduler.warmup_length)
        self.__runControlScheduler = runControlScheduler

    def process_impl(self):
        """
        Process the event by delegating to the passed on completion function
        """
        self.__runControlScheduler.warmup_complete()

class BatchCompleteEvent(SimEvent):
    """
    An event that initiates batch completion processing at the end of the
    specified simulation warmup and batch time length.  The completion processing
    is invoked via a passed function, that may vary based on simulation mode.

    The event is also initialized with the number of simulation batches to
    execute.  If this number is more than one, the event reschedules itself
    until all batches are complete.
    """
    def __init__(self, runControlScheduler):
        super().__init__(runControlScheduler.warmup_length + runControlScheduler.batch_length)
        self.__runControlScheduler = runControlScheduler
        self.__batchLength = runControlScheduler.batch_length
        self.__nBatches = runControlScheduler.nbatches
        self.__currentBatchNum = 0

    def process_impl(self):
        """
        Process the event by delegating to the passed on completion function
        """
        self.__currentBatchNum += 1
        self.__runControlScheduler.batch_complete(self.__currentBatchNum)
        if self.__currentBatchNum < self.__nBatches:
            self._time += self.__batchLength
            self.register()


class SimProgressEvent(SimEvent):
    """
    An event that triggers simulation progress updates (e.g. progress bar)
    in the UI at regular intervals. The event is initialized with the run
    control scheduler (which provides the run length and handles actual
    progress interval processing) and an interval percentage, which dictates
    how many progress events will be fired over the course of a simulation
    run. (e.g., if interval percentage is 5, than an event will be fired
    every 5% of the scheduled simulation run, or 20 total.)
    """
    @staticmethod
    def interval_sim_time(runControlScheduler, intervalPct):
        """
        Returns the simulated time between progress updates based on the
        scheduled run length and interval percentage.
        """
        interval = runControlScheduler.run_length * (intervalPct / 100.0)
        return interval

    def __init__(self, runControlScheduler, intervalPct):
        self.__intervalTime = self.interval_sim_time(runControlScheduler, intervalPct)
        assert self.__intervalTime > 0, "ProgressEvent interval must be > 0"
        super().__init__(self.__intervalTime)
        self.__runControlScheduler = runControlScheduler
        self.__intervalPct = intervalPct
        self.__intervalCount = 0

    def process_impl(self):
        """
        Process the event by delegating to the scheduler, and then
        re-registering at the next progress interval time.
        """
        self.__intervalCount += 1
        self.__runControlScheduler.progress(self.__intervalPct * self.__intervalCount)
        self._time += self.__intervalTime
        self.register()
