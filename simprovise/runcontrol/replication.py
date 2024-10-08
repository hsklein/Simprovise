#===============================================================================
# MODULE replication
#
# Copyright (C) 2014-2015 Howard Klein - All Rights Reserved
#
# Defines SimReplication and SimReplicator classes. SimReplicator instances
# are used to run one or more simulation run replications via SimReplication
# instances.
#
# When SimReplicator is used by a Qt-based UI, it communicates replication
# status updates to the UI via Qt Signals. When used in an environment without
# PySide, the Signal class is replaced by a mock whose methods are no-ops.
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
import sys, os, time
import multiprocessing, threading
import tempfile, shutil
import sqlite3
from traceback import format_tb

# Use PySide if it is installed; otherwise replace with mock object classes
try:
    from PySide.QtCore import QObject, Signal
except ImportError:
    from simprovise.runcontrol.mockqt import MockQObject as QObject
    from simprovise.runcontrol.mockqt import MockSignal as Signal

from simprovise.core.simlogging import SimLogging
from simprovise.core.model import SimModel
from simprovise.core.simclock import SimClock
from simprovise.core import SimError, simrandom, simtrace
from simprovise.core.simevent import EventProcessor
from simprovise.database import SimDatabaseManager
from simprovise.runcontrol.simruncontrol import (SimRunControlParameters,
                                                 SimRunControlScheduler,
                                                 SimReplicationParameters)
from simprovise.runcontrol.messagequeue import (SimMessageQueue,
                                                SimMessageQueueSender)

logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "Replication Error"
_STATUS_NOT_STARTED = 'NOT_STARTED'
_STATUS_IN_PROGRESS = 'IN_PROGRESS'
_STATUS_COMPLETE = 'COMPLETE'
_STATUS_CANCELLED = 'CANCELLED'


def execute_replication(modelPath, dbpath, runNumber, warmupLength,
                       batchLength, nBatches, queue=None):
    """
    Simple function that creates and executes a replication, and captures
    any failures that occurred during that execution.  Exceptions raised
    by the model are captured in the replication exception member; exceptions
    raised during event processing "should" just propagate to here, where we
    in turn catch them.

    Designed as a task to be executed by a multiprocessing Pool.  Returns
    the replication run number, the path of the temporary database populated
    by the replication, and any exception that was raised (or None)
    
    :param modelPath:    The model Python script path to be executed.
    :type modelPath:     ``str``
    
    :param dbPath:       The path to an existing output database to be
                         populated by this run. If ``None`` a new output
                         database will be created.
    :type dbPath:        ``str`` or ``None``    
    
    :param runNumber:    The simulation run number, in range
                         [1 - :func:`~simprovise.core.simrandom.max_run_number`]
    :type runNumber:     `int`    
    
    :param warmupLength: The warmup time for the simulation (before data
                         collection begins)
    :type warmupLength:  :class:`~simprovise.core.simtime.SimTime`
    
    :param batchLength:  The time length for each batch after the warmup
    :type batchLength:   :class:`~simprovise.core.simtime.SimTime`
    
    :param nBatches:     The number of batches to execute
    :type nBatches:      `int`    
    
    :param queue:        The ``multiprocessing.Queue`` used to send status
                         messages to the :class:`SimReplicator` via a
                         :class:`~.messagequeue.SimMessageQueue` which wraps
                         it. May be ``None``, in which case not messages will
                         be sent
    :type queue:         :class:`multiprocessing.Queue` or ``None``   
    
    """
    tbstring = None
    try:
        logger.info("execute_replication() for run %d, model path: %s, pid: %s",
                    runNumber, modelPath, os.getpid())
        if modelPath:
            model = SimModel.load_model_from_script(modelPath)
        else:
            model = SimModel.model()
        replication = SimReplication(model, runNumber, warmupLength, batchLength,
                                     nBatches, dbpath, queue)
        replication.execute()
    except Exception as e:
        print("execute_replication() exception:", e)
        replication.exception = e
        lines = format_tb(e.__cause__.__traceback__)
        tbstring = "".join(lines)

    return runNumber, dbpath, replication.exception, tbstring

class SimReplication(QObject):
    """
    Encapsulates a single replication - i.e., a single run of the simulation
    model as defined by the passed model and run control parameters.

    The initializer may also be passed a database path, which should be an 
    output database that is fully initialized - i.e., has it's dataset table
    populated - but does not contain any datasetvalues.  By doing this, we
    ensure that every replication in a set has the same dataset table data -
    and therefore the same dataset integer IDs for a given dataset
    (element name/dataset name)  If we create the database from scratch,
    dataset integer IDs could vary from replication replication, meaning that
    the datasetvalue row data could not be simply copied from one replication
    database to another.

    The database path may be ``None``; that should only be used if we are doing
    a single stand-alone run - e.g., using ``SimReplication`` to execute a model
    in-process. When the database path is none, we do create a new database
    and initialize it during initialization.

    :param model:        The :class:`~simprovise.core.model.SimModel`
                         to be executed.
    :type model:         :class:`~simprovise.core.model.SimModel`
    
    :param runNumber:    The simulation run number, in range
                         [1 - :func:`~simprovise.core.simrandom.max_run_number`]
    :type runNumber:     `int`    
    
    :param warmupLength: The warmup time for the simulation (before data
                         collection begins)
    :type warmupLength:  :class:`~simprovise.core.simtime.SimTime`
    
    :param batchLength:  The time length for each batch after the warmup
    :type batchLength:   :class:`~simprovise.core.simtime.SimTime`
    
    :param nBatches:     The number of batches to execute
    :type nBatches:      `int`    
    
    :param dbPath:       The path to an existing output database to be
                         populated by this run. If ``None`` a new output
                         database will be created.
    :type dbPath:        ``str`` or ``None``    
    
    :param queue:        The ``multiprocessing.Queue`` used to send status
                         messages to the :class:`SimReplicator` via a
                         :class:`~.messagequeue.SimMessageQueue` which wraps
                         it. May be ``None``, in which case not messages will
                         be sent
    :type queue:         :class:`multiprocessing.Queue` or ``None``   

    """
    #TODO: Don't think this needs to be a QObject, since it doesn't emit or
    #connect to any Qt Signals
    def __init__(self, model, runNumber, warmupLength,
                 batchLength, nBatches, dbPath=None, queue=None):
        """
        Initialize a replication with the path to the model, an initialized
        output database, and the run control parameters.  The initializer
        sets up a non-animated run, initializes the random number generators
        for this run, initializes the simulation clock, and loads the model.
        """
        super().__init__()
        #SimLogging.set_level(logging.WARN)
        self.__databaseManager = SimDatabaseManager()
        self.__dbPath = dbPath
        self.__model = model
        self.__runControlParameters = \
            SimRunControlParameters(runNumber, warmupLength, batchLength,
                                    nBatches)
        
        self.__totalRunLength = warmupLength + nBatches * batchLength
        self.__hasExecuted = False
        self.exception = None
        if not self.__totalRunLength > 0:
            msg = 'Total Simulation run time not greater than zero'
            raise SimError(_ERROR_NAME, msg)

        self.__msgQueue = None
        if queue:
            self.__msgQueue = SimMessageQueueSender(runNumber, queue)

    @property
    def dbPath(self):
        """
        :return: The output database path for this :class:`SimReplication`
        :rtype:  `str`
        """
        return self.__dbPath

    def execute(self):
        """
        Actually execute the replication/simulation run.
        """
        if self.__hasExecuted:
            raise SimError(_ERROR_NAME,
                           "Replication has already executed (and cannot be re-executed)")

        runNumber = self.__runControlParameters.run_number
        logger.info("starting replication for run number %d ...", runNumber)
        try:
            simrandom.initialize(runNumber)
            SimClock.initialize()
             
            # Create the event processor before loading the model, as the
            # EventProcessor initializer re-initializes/empties the events chain
            # (and model static initialization adds source generation events to
            # the chain)
            eventProcessor = EventProcessor()
                           
            # Invoke final_initialize() on all agents in the model
            for agent in self.__model.agents:
                agent.final_initialize()
                
            # Invoke final_initialize() on all process and entity elements in 
            # the model. Skip static objects, since they are also agents and
            # were therefore final_initialized() in the previous step.
            for e in self.__model.process_elements:
                e.final_initialize()
            for e in self.__model.entity_elements:
                e.final_initialize()
            
            # Do any model initialization functions (a TODO)
               
            # Do output database initialization
            if self.__dbPath:
                self.__databaseManager.open_existing_database(self.__model,
                                                              self.__dbPath)
            else:
                self.__databaseManager.create_output_database(self.__model)
                self.__dbPath = self.__databaseManager.current_database_path
                
            self.__databaseManager.set_commit_rate(0)
            self.__databaseManager.initialize_run(runNumber)
            
            # Initialize the first batch
            for dset in self.__model.datasets:
                dset.initialize_batch(self._initial_batch_number())
                
            # TODO replication/background scheduler
            runControlScheduler = SimRunControlScheduler(self.__model,
                                                         self.__runControlParameters,
                                                         progressIntervalPct=10,
                                                         msgQueue=self.__msgQueue)
            runControlScheduler.schedule_run_control_events()

            # Initialize the trace, if any (in particular, open the trace file)
            simtrace.initialize(self.__model.filename)
            
            startTime = time.time()
            self._send_status_message(SimMessageQueue.STATUS_STARTED)
            nEvents = eventProcessor.process_events(self.__totalRunLength)
            print("Run", self.__runControlParameters.run_number,
                  "execution complete:", nEvents,
                  "events processed. Process Time:",
                  time.time()-startTime)
            self.__databaseManager.close_output_database(delete=False)
        except Exception as e:
            try:
                self.__databaseManager.close_output_database(delete=True)
            except Exception as dbexcpt:
                closemsg = "Unable to close/delete temporary output database: %s"
                logger.error(closemsg, dbexcpt)
            raise SimError(_ERROR_NAME, str(e)) from e
        finally:
            self.__hasExecuted = True
            simtrace.finalize()

    def _send_status_message(self, status):
        if self.__msgQueue:
            self.__msgQueue.send_status_message(status)
            
    def _initial_batch_number(self):
        """
        Returns the (integer) number of the first batch.
        
        By convention, the warmup is batch number zero. So if a warmup
        is specified, the initial batch number is zero; if not, te
        initial batch is one.
        """
        if self.__runControlParameters.warmup_length > 0:
            return 0
        else:
            return 1


class SimReplicator(QObject):
    """
    The ``SimReplicator`` manages/executes a set of
    :class:`SimReplications <SimReplication>`. When PySide is installed, it
    inherits from QObject and emits Qt signals. When PySide is not installed,
    the signal emit is a no-op. (See `Qt Issues` below)

    The ``SimReplicator`` is initialized with a model and run control parameters.
    The primary public method is :meth:`execute_replications`, which takes
    replication parameters as an argument and executes the replications as
    tasks on amultiprocessing pool allowing tasks to execute in parallel
    (in separate processes).  The replication parameters specifies the maximum
    number of processes to run concurrently.

    :meth:`execute_replications` also takes an optional ``asynch`` parameter.
    When True, the method returns immediately, with a background thread emitting 
    a ReplicationsComplete Qt signal once all tasks have finished.  If False,
    :meth:`execute_replications` will block until all replication tasks complete
    (at which point it will emit the ReplicationsComplete signal as well.)  When
    executed asynchronously, a ReplicationFinished Qt signal is emitted after
    each replication.

    If :meth:`execute_replications` is called with ``asynch``=``True``, the
    client may cancel in-progress and remaining tasks via a :meth:`cancel`
    call, which invokes the pool's ``terminate()`` method and emits a
    ``ReplicationsCancelled`` Qt signal.

    All replication output is written to a temporary output database, created
    by the replicator.  The path to that database is available via property.
    The code that creates the replicator is responsible for cleaning up this
    temporary file by either moving it to a permanent location or deleting it.

    Finally, there are a number of properties which either:
    
    - Indicate the status of the replication execution.
    - If completed, indicate the number of tasks/number of failed tasks.
    - Provide the path of the output database created by the replicator.

    In order to minimize database contention between replications executing
    in parallel, each replication writes to its own (temporary) output
    database.  An "empty" database (with Element and Dataset tables populated,
    but no dataset values) is created by the replicator, with a copy being
    sent to each replication.  This ensures that each replication uses
    an identical dataset table.  When the first (successful) replication
    completes, it's database becomes the master; when subsequent replications
    complete, their dataset values are merged into the master.
    
    Context Manager Use
    -------------------
    
    The SimReplicator can and should be used as a context manager, a-la::
    
        replicator = SimReplicator(model, warmupLength, batchLength, nBatches)
        with replicator:            
            replicator.execute_replications(replicationParameters, asynch=False)

    The context manager protocol should ensure that all the temporary files
    created during replication are cleaned up; if
    :meth:`~SimReplicator.execute_replications` is invoked with `asynch=True`,
    it is difficult to do so any other way, as, the method will likely return 
    before all the replication processes complete. If the replicator raises
    an exception, the created output database will also be removed.

    Concurrency/Thread Safety
    -------------------------

    Replications have a process to themselves when executing, so there should
    be no safety issues there.  The results of each replication (a simple run
    number, database path and exception tuple) are processed by a callback
    function that runs on a separate thread in the main process.  Every callback
    runs on the same thread, so the database merge calls should never occur
    in parallel.  If :meth:`execute_replications` is invoked with asynch=True, 
    there is a third thread, which joins the pool.  Changes to the __status
    member variable should be threadsafe in a Python context, and the result
    accessors should prevent the results (or output database) from being
    accessed until after the pool has finished processing and both of these
    background threads are done.  When running in a Qt environment (see below),
    this third thread emits a ReplicationsComplete Qt signal when the pool is
    joined.  If the signal is connected to a ``QObject`` created on the main
    thread, the slot function will be executed on the main thread (per Qt
    behavior).

    Also... in many respects a cleaner design would involve passing an
    external SimDatabaseManager instance into the replicator, which would open
    and take ownership of the output database.  The problem is that ``sqlite3``
    connection objects can operate only in the thread in which they are created.
    If a database object (and it's connection) is created in the callback
    thread, it cannot be used to access the database in the main thread.  So
    instead, we close the connection after replications are completed/cancelled
    and provide access to the output database path, which may then be opened by
    a database manager in the main thread.
    
    Qt Issues
    ---------
    
    The ``SimReplicator`` (in conjunction with its
    :class:`~messagequeue.SimMessageQueue`) is designed to be used by a PySide
    Qt GUI application (and can also be used outside of one). It facilitates
    a Qt application that can stay responsive to user input while it's
    ``SimReplicator`` executes replications asynchronously, and receives/reports 
    on status updates during the execution. The basic flow:
    
     1. The ``SimReplicator`` creates a :class:`~messagequeue.SimMessageQueue`
        during initialization.
    
     2. The ``SimReplicator`` passes the ``SimMessageQueue``'s multiprocessing
        queue to each replication process, which executes a
        :class:`SimReplication`. The replication processes are launched via a
        multiprocessing pool. Each ``SimReplication`` object creates a
        :class:`.messagequeue.SimMessageQueueSender`, which
        puts status update messages into the queue. In this scenario, 
        :meth:`execute_replications` should be called with parameter ``asynch``
        set to ``True``; in that case, ``execute_replications()`` returns after
        creating a separate thread to wait on completion of all of the
        replication processes, at which point a Qt Signal is emitted.
                
     3. The SimReplicator's ``SimMessageQueue`` creates a separate thread 
        and listens for messages from the SimReplication senders on that
        thread. It responds to messages by emitting Qt Signals, which can
        then be  connected to and processed by the Qt GUI application running
        on the main thread. Essentially the listener just converts recieved
        queue messages into Qt Signals, and relies on the GUI app to connect
        those signals to slots in the GUI app.
        
    When operating outside of a Qt GUI (e.g. a command line application),
    the SimReplicator would typically execute replications synchronously.
    PySide is not required for that type of application, and if it is
    not installed, mock versions of Qt classes ``QObject`` and ``Signal`` are 
    used in their place. In that case all Signal-related calls are no-ops.
    
    :param model:        The :class:`~simprovise.core.model.SimModel`
                         to be executed.
    :type model:         :class:`~simprovise.core.model.SimModel`
    
    :param warmupLength: The warmup time for the simulation (before data
                         collection begins)
    :type warmupLength:  :class:`~simprovise.core.simtime.SimTime`
    
    :param batchLength:  The time length for each batch after the warmup
    :type batchLength:   :class:`~simprovise.core.simtime.SimTime`
    
    :param nBatches:     The number of batches to execute
    :type nBatches:      `int`    
    
    """
    ReplicationsComplete = Signal()
    ReplicationsCancelled = Signal()
    ReplicationStarted = Signal(int)
    ReplicationFinished = Signal(int, bool, str)
    ReplicationProgress = Signal(int, int)

    def __init__(self, model, warmupLength, batchLength, nBatches):
        """
        Set up the replication sequence based on the model, run control
        parameters, and replication parameters.  Also create the initial
        "template" output database, which will be copied and populated
        by each replication.
        """
        super().__init__()
        # create a SimRunControlParameters object just to validate
        # those parameters (raising if invalid) before things get going
        testRunControlParameters = \
            SimRunControlParameters(1, warmupLength, batchLength,
                                    nBatches)
        self.__model = model        
        self.__warmupLength = warmupLength
        self.__batchLength = batchLength
        self.__nBatches = nBatches
        self.__pool = None
        self.__status = _STATUS_NOT_STARTED
        self.__nRuns = None        
        self.__nRepsStarted = 0
        self.__nRepsFailed = 0
        self.__nRepsFinished = 0
        self.__results = {}
        self.__msgQueue = SimMessageQueue()
        self.__masterDbPath = None
        self.__masterDbConnection = None
        self.__initializedDbPath = None
        
        # We create a TemporaryDirectory as an attribute, rather than
        # as a variable within execute_replications because we don't
        # want to clean it up prematurely if we do an asynchronous join.
        # (For that reason, we can't use it as a context manager.)
        # We'll place the temporary database files here so that they get
        # cleaned up regardless (along with the temporary directory) on
        # destruction.
        self.__tempdir = tempfile.TemporaryDirectory()
        
        self._create_initialized_database()
        self.__msgQueue.StatusMessageReceived.connect(self._replication_started)
        self.__msgQueue.ProgressMessageReceived.connect(self.ReplicationProgress)
        # Should we be doing something with msgQueue.LogMessageReceived?

    def __enter__(self):
        """
        To use replicator as a context manager
        """
        return self

    def __exit__(self, type, value, tb):
        """
        When using the replicator as a context manager, clean up on exit
        without handling any exceptions - but if an exception was raised,
        delete the created output database in addition to any other
        temporary files (which are cleaned up regardless of whether or not
        an exception was raised).
        
        On normal exit, the output database is the responsibility of the
        replicator's owner/caller)
        """
        if value is not None:
            logger.error("Replication error %s, cleaning up...", value)
            # exceptioned raised, so delete the output database
            if self.__masterDbPath:
                logger.error("Replication error: removing database %s...",
                             self.__masterDbPath)
                os.remove(self.__masterDbPath)
        self.cleanup()
        self.__tempdir.cleanup()
        
        return False

    @property
    def warmup_length(self):
        """
        Run Control - warmup length for each replication
        """
        return self.__warmupLength

    @property
    def batch_length(self):
        """
        Run Control - batch length for each replication
        """
        return self.__batchLength

    @property
    def nbatches(self):
        """
        Run Control - number of batches for each replication
        """
        return self.__nBatches

    @property
    def status(self):
        """
        Current status of the replicator - NOT_STARTED, IN_PROGRESS or
        COMPLETE
        """
        return self.__status

    @property
    def msg_queue(self):
        """
        Return the message queue instance, primarily so that clients can
        connect it's signals
        """
        return self.__msgQueue

    @property
    def not_started(self):
        """
        Returns True if replication execution has not yet started
        """
        return self.__status == _STATUS_NOT_STARTED

    @property
    def in_progress(self):
        """
        Returns True if execution is in progress (but not complete)
        """
        return self.__status == _STATUS_IN_PROGRESS

    @property
    def complete(self):
        """
        Returns True if execution is completed - i.e., all replications have
        finished.
        """
        return self.__status == _STATUS_COMPLETE

    @property
    def cancelled(self):
        """
        Returns True if execution was cancelled
        """
        return self.__status == _STATUS_CANCELLED

    @property
    def output_dbpath(self):
        """
        Returns the path to the (temporary) output database, once it is created
        (after the first replication completes).  Should generally not be called
        during execution, and raises an exception if the path has not yet been set.
        """
        if self.__masterDbPath:
            return self.__masterDbPath
        else:
            raise SimError(_ERROR_NAME, "outputDbPath() called before any replications complete")

    @property
    def started_count(self):
        """
        Returns the number of replications that have started
        """
        return self.__nRepsStarted

    @property
    def in_progress_count(self):
        """
        Returns the number of replications that are currently in progress
        """
        return self.__nRepsStarted - self.__nRepsFinished

    @property
    def finished_count(self):
        """
        Returns the number of replications that have finished (successes
        and failures)
        """
        return self.__nRepsFinished

    @property
    def success_count(self):
        """
        Returns the number of replications that have succeeded
        """
        return self.__nRepsFinished - self.__nRepsFailed

    @property
    def failure_count(self):
        """
        Returns the number of replications that failed
        """
        return self.__nRepsFailed

    def cancel(self):
        """
        Cancel replications in progress
        """
        if not self.in_progress:
            logger.info("replications not executing - nothing to cancel")
            return

        assert self.__pool, "__pool member not set for cancel() call"
        self.__status = _STATUS_CANCELLED
        self.__pool.terminate()
        self.ReplicationsCancelled.emit()

    def results(self):
        """
        Returns a copy of the results dictionary (keyed by run number) for
        all runs executed by this replicator - potentially over multiple
        runs. (In other words, if we execute runs 1-10 followed by runs 8-18,
        results will contain a result object for runs 1-18).  Each result
        contains the exception generated if the run failed, or None if the
        run succeeded.

        The making of the copy is protected by a lock, as the results
        dictionary gets updated in a separate thread.
        """
        lock = threading.Lock()
        with lock:
            return dict(self.__results)

    def cleanup(self):
        """
        Delete the initialized (but no datasetvalues) database
        """
        if self.__initializedDbPath:
            logger.info("removing temporary file: %s", self.__initializedDbPath)
            os.remove(self.__initializedDbPath)
            self.__initializedDbPath =  None

    def execute_replications(self, replicationParameters, asynch=False):
        """
        Executes replications using a multiprocessing Pool, with the
        replication runs (and the size of the pool) sepcified via the passed
        replication parameters.  If this is the first call to
        executeReplications(), a new temporary output database is created,
        with all replication outputs merged into that database (including
        replications generated by subsequent executeReplications() calls.)

        The size (maximum number of simultaneous child processes) of the pool
        is specified by the caller, though we do ensure it doesn't exceed
        the number of replications. We also specify maxtasksperchild
        as 1, which starts a new process for each replication (rather than
        reusing processes once we have more than n replications). This is
        required because model loading (in SimModel) currently breaks if
        the process has previously loaded the same or a different model.
        
        Starting a new process for each run is perhaps a bit inelegant, and
        it does entail some performance hit, but that hit is likely negligible
        for large/long-running models (i.e., the hit is constant relative to the
        simulation length) and using a new process is both easier and more
        robust. (For small models, with execution time < 1 second, the hit might be
        ~20%)
        """
        print("in SimReplicator.execute_replications")
        if self.in_progress:
            raise SimError(_ERROR_NAME, "Replications are currently in progress")

        self.__status = _STATUS_IN_PROGRESS
        firstRun, lastRun = replicationParameters.replication_range
        self.__nRuns = lastRun + 1 - firstRun
        
        # The number of processes in the Pool should be the minimum of the
        # maximum current replications (which typically defaults to cpu_count)
        # and te actual number of replications we're going to do - i.e,
        # no need for more processes than we have replications to perform.
        n = min(replicationParameters.max_concurrent_replications, self.__nRuns)
        
        # make sure we use the 'spawn' start method; 'fork' (presumably because
        # it carries over the SimModel object from the parent process) results
        # in 'register element with duplicate element id' errors.
        # As of Python 3.12, explicitly setting 'spawn' is required on Linux
        # (where the default is 'fork)
        ctx = multiprocessing.get_context('spawn')
        
        with multiprocessing.pool.Pool(processes=n, maxtasksperchild=1,
                                  context=ctx) as pool:
            self.__pool = pool
            self.__nRepsStarted = 0
            self.__nRepsFailed = 0
            self.__nRepsFinished = 0
            self.__msgQueue.start_listening()
            logger.info("Replication process pool initialied with %d processes", n)
    
            for runNumber in range(firstRun, lastRun+1):
                dbpath = self._clone_initialized_database(self.__tempdir.name)
                ar = pool.apply_async(execute_replication,
                                      self._execute_args(runNumber, dbpath),
                                      callback=self._callback)
    
            pool.close()
            logger.info("Running replications on thread %d", threading.get_ident())
            if asynch:
                self._async_join(pool)
            else:
                pool.join()
                self.__status = _STATUS_COMPLETE
                self.__msgQueue.stop_listening()
                self.ReplicationsComplete.emit()
                logger.info("(synchronous) replications complete")

    def _async_join(self, pool):
        """
        An asynchronous join the to the passed multiprocessing pool, allowing
        a UI to be responsive during replication execution.  Emits a
        ReplicationsComplete after the join - unless the replication tasks were
        cancelled by the client (via a cancel() call)

        The pool.join() is executed on a separate thread, emitting a
        ReplicationsComplete signal once that completes.  Connecting that
        signal to a an object running on the main thread should work (i.e.
        execute the slot call) as long as the main thread is running a Qt event
        loop.  (If no event loop is running, the signal seems to disappear
        into the ether.)
        """
        def joinAndSignal(pool):
            startTime = time.time()
            pool.join()
            self.__msgQueue.stop_listening()
            if self.cancelled:
                logger.info("Cancel requested.  Exiting execute")
            else:
                self.__status = _STATUS_COMPLETE
                logger.info("(asynchronous) replications complete. Total execution time = %f",
                            time.time() - startTime)
                self.ReplicationsComplete.emit()

        t = threading.Thread(target=joinAndSignal, args=(pool,))
        t.daemon = True
        t.start()

    def _create_initialized_database(self):
        """
        Create an output database for this model and initialize it to include
        a populated dataset table - but no datasetvalue rows.  We'll make a
        copy of this database for each replication, ensuring that each
        replication defines datasets (including dataset integer IDs) the same
        way.
        """
        self.cleanup()        
        databaseManager = SimDatabaseManager()
        databaseManager.create_output_database(self.__model)
        
        # We'll rely on the context manager protocol (as implemented in
        # __exit__()) to make sure  this file is deleted when we're done.
        # A bit more elegance in the databaseManager implementation might
        # help, but we'll save that for another day.
        self.__initializedDbPath = databaseManager.database.db_path
        databaseManager.close_output_database(delete=False)

    def _clone_initialized_database(self, tempdir):
        """
        Make a copy of the initialized database created by
        _createInitializedDatabase() in a temporary file in the passed
        temporary directory and return that file's path. The
        temporary directory should be the name of a tempfile.TemporaryDirectory,
        which automatically gets deleted on destruction.
        """
        f, clonepath = tempfile.mkstemp(suffix='.simoutput', dir=tempdir)
        os.close(f)
        shutil.copyfile(self.__initializedDbPath, clonepath)
        return clonepath

    def _execute_args(self, runNumber, dbpath):
        """
        Returns the arguments to an execute_replication() call for the
        specified run number as a sequence, so that they may be passed
        in as part of a pool.apply_async() call.
        """
        
        # If ther replicator is being invoked directly from the model script
        # itself (and the model script therefore was not loaded via 
        # model.load_model_from_script()) then tell execute_replication() 
        # by passing a None modelpath parameter, so it won't do a
        # load_model_from_script() either. 
        modelPath = None
        if self.__model.loaded_from_script():
            modelPath = self.__model.filename
        
        args = (modelPath, dbpath, runNumber,
                self.__warmupLength, self.__batchLength, self.__nBatches,
                self.__msgQueue.queue)
        return args

    def _callback(self, result):
        """
        Callback invoked after a replication finishes. Result is a tuple
        containing:
        - The run number of that replication
        - The path of the temporary database file created by the replication
        - An exception if the run failed, or None if it completed successfully
        - A string containing the traceback if the run failed, or None if it
          completed successfully

        By making all runs "succeed" (by not letting exceptions leak out of
        the task function executeReplication()), we can more easily get the
        run number that failed.  (An error callback would just get the exception,
        requiring either the run number to be embedded in the exception or other
        addiional code to find the corresponding run number.)

        Note that this callback occurs on the main (parent) process, though in
        a different thread.  It is possible for multiple runs complete and
        invoke this method nearly simultaneously; it is there at least
        theoretically possible for access to the master database (for the
        purpose of copying data) to become a bottleneck, and even timeout. If
        necessary, the handling of this callback could be delegated to a thread
        or process pool (with a single thread/process), thereby ensuring that
        only one callback is attempting to access the master database at a time.

        For successful runs, merge the temporary database into the master (also
        temporary) database that contains the datasetvalue data for all runs.

        The callback also creates or updates the __results dictionary value
        for the run.  (each __results value is an exception or None if the
        run completed successfully)
        """
        runNumber, dbpath, exception, tbstring = result
        self.__nRepsFinished += 1
        if exception:
            logger.error("Run %d failed: %s", runNumber, exception)
            print("Traceback:")
            print(tbstring)
        else:
            print("Replication Run", runNumber, "complete")
            try:
                self._merge_run(dbpath, runNumber)
            except Exception as e:
                print("Run", runNumber, "Data merge from ", dbpath,
                      "to", self.__masterDbPath, "failed:", e)
                result = runNumber, dbpath, e
                exception = e

        success = exception is None
        if not success:
            self.__nRepsFailed += 1
        errMsg = "" if success else str(exception)
        self.ReplicationFinished.emit(runNumber, success, errMsg)

        # The UI may access the results while the replicator is working, so
        # protect them with a lock.
        lock = threading.Lock()
        with lock:
            self.__results[runNumber] = exception

        if self.__nRepsFinished == self.__nRuns:
            if self.__masterDbConnection:
                self.__masterDbConnection.close()
                self.__masterDbConnection = None
            self.cleanup()

    def _merge_run(self, dbpath, runNumber):
        """
        Merge a passed database (created by a single replication) with a master
        database for all replications.  There are three possible scenarios here:

        1.  This is the the very first call to mergeRun() for this SimReplicator
            instance i.e., this is also the first call to executeReplications()
            for this instance.  In this case, there is not yet a master database
            file, so the passed dbpath becomes that file (and masterDbPath is
            set to it).

        2.  This is the first call to mergeRun() from a second or subsequent
            call to executeReplications() for this SimReplicator instance.
            (e.g., the user has run eight replications, and then decides to run
            eight more.)  In this case, the masterDbPath is set, but the
            connection to it needs to be re-opened.  After the re-connect, the
            data from the passed dbpath can be merged into the master database.

        3.  This is a second or subsequent call to mergeRun() for a given call
            to executeReplications().  The master database connection is
            already set, so we just merge data from the passed dbpath into the
            master database (via _copydata()).
        """
        if not self.__masterDbPath:
            f, self.__masterDbPath = tempfile.mkstemp(suffix='.simoutput')
            os.close(f)
            shutil.copyfile(dbpath, self.__masterDbPath)
        else:
            if not self.__masterDbConnection:
                # It's possible for the outside world to mess with this file.
                #  We'll at least make sure it hasn't been deleted.
                if not os.path.isfile(self.__masterDbPath):
                    raise SimError(_ERROR_NAME,
                                   "Replicator Output Database has been removed")
                self.__masterDbConnection = sqlite3.connect(self.__masterDbPath)
            self._copydata(dbpath, self.__masterDbConnection, runNumber)
            os.remove(dbpath)

    def _copydata(self, srcpath, conn, runNumber):
        """
        Delete any dataset values for the passed run number from the master
        database.  (This handles the situation where the caller repeats a run
        in successive calls to executeReplications().) Then copy all rows
        from the passed srcpath database's datasetvalue table to the
        datasetvalue table in the passed master database connection (conn)
        It is assumed that the source database has datasetvalue data only for
        the passed runNumber.
        """
        startTime = time.time()
        cursor = conn.cursor()
        cursor.execute("delete from datasetvalue where run = ?", (runNumber,))
        attachsql = "attach '{0}' as srcdb".format(srcpath)
        cursor.execute(attachsql)
        sqlstr = """
                 insert into datasetvalue
                 select * from srcdb.datasetvalue
                 """
        cursor.execute(sqlstr)
        conn.commit()
        cursor.execute("detach srcdb")
        #print("copydatavalues for run", runNumber, srcpath, "time", time.time()-startTime)

    def _replication_started(self, runNumber):
        """
        Invoked when an asynchronous replication starts.
        """
        logger.info("Replication %d starting...", runNumber)
        self.__nRepsStarted += 1
        self.ReplicationStarted.emit(runNumber)



