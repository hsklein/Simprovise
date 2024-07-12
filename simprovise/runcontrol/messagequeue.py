#===============================================================================
# MODULE messagequeue
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines SimMessageQueue, SimMessageQueueSender classes that facilitate
# communications between simulation replications (each running in their own
# process) and the main application.
#===============================================================================
import sys, os, time
import multiprocessing, threading

# Use PySide if it is installed; otherwise replace with mock object classes
try:
    from PySide.QtCore import QObject, Signal
except ImportError:
    from simprovise.runcontrol.mockqt import MockQObject as QObject
    from simprovise.runcontrol.mockqt import MockSignal as Signal

from simprovise.core import SimError
from simprovise.core.simlogging import SimLogging
from simprovise.core.apidoc import apidocskip

logger = SimLogging.get_logger(__name__)

_STATUS_MSG_TYPE = 1
_LOG_MSG_TYPE = 2
_PROGRESS_MSG_TYPE = 3

class SimMessageQueue(QObject):
    """
    Facilitates communication between simulation replications (running in
    separate processes) and the main (replicator) process that spawned
    them.  The communication mechanism is a multiprocessing queue.
    
    The big picture: SimMessageQueue is designed on behalf of a (PySide) Qt
    GUI application that runs simulation replication(s) and would like to
    stay responsive while those replication(s) execute and receive/report on
    status updates during the execution. When PySide is not present, this
    class essentially does nothing. See :class:`~.replication.SimReplicator`
    for details.
        
    SimMessageQueue has three public properties/methods:
    
      - :meth:`start_listening`.  Starts a separate thread that pulls items off 
        of the queue and emits message signals.
      - :meth:`stop_listening.`  Tells the listener thread to exit.
      - :meth:`queue`.  The ``multiprocessing.Queue`` object that can be
        passed to replication processes (which will put messages on it.)

    Note again that the message signals are emitted from the listener thread, 
    not the main thread.  Typically the client will rely on Qt to execute the
    slots to which they are connected to run on the main thread, which
    in turn requires that a Qt event loop be running.

    Finally, note that if we are running in an environment without PySide/Qt,
    the ``QObject`` and ``Signal`` classes are replaced by mocks that do nothing
    - so in that scenario, the message queue itself does essentially nothing.
    (When Qt is involved, both ``SimMessageQueue`` and ``SimReplicator`` need to
    inherit from ``QObject``.)
    """
    STATUS_STARTED = "Started"
    STATUS_COMPLETED = "Completed"
    STATUS_FAILED = "Failed"
    STATUS_CANCELLED = "Cancelled"

    StatusMessageReceived = Signal(int, str)
    LogMessageReceived = Signal(int, str, str)
    ProgressMessageReceived = Signal(int, int)

    def __init__(self):
        """
        Initialize by creating the multiprocessing Queue.  We need
        to create it using a multiprocessing manager; otherwise, if
        sharing the queue with multiple processes results in a
        "RuntimeError: Queue objects should only be shared between processes
        through inheritance" exception on put().  See:
        http://stackoverflow.com/questions/9908781/sharing-a-queue-among-several-processes
        """
        super().__init__(None)
        self.__manager = multiprocessing.Manager()
        self.__queue = self.__manager.Queue()
        self.__listenerThread = None

    @property
    def queue(self):
        """
        Return the underlying ``multiprocessing.Queue``
        """
        return self.__queue

    def start_listening(self):
        """
        Start listening for messages on the queue from a new thread.
        Emit a signal for each message received.  Exit after receiving
        a sentinal value of ``None``.
        """
        def listen():
            msg = self.__queue.get()
            while msg is not None:
                try:
                    runNumber, msgType, msgContent = msg
                    if msgType == _STATUS_MSG_TYPE:
                        self.StatusMessageReceived.emit(runNumber, msgContent)
                    elif msgType == _PROGRESS_MSG_TYPE:
                        self.ProgressMessageReceived.emit(runNumber, msgContent)
                    elif msgType == _LOG_MSG_TYPE:
                        self.LogMessageReceived.emit(runNumber, msgContent)
                    else:
                        logger.error("Invalid Message Type in message: %s",
                                     str(msg))
                except Exception as e:
                    errorMsg = "Exception raised handling message: %s.  Exception: %s"
                    logger.error(errorMsg, str(msg), str(e))
                msg = self.__queue.get()
            logger.info("SimMessageQueue listener exiting")

        self.__listenerThread = threading.Thread(target=listen)
        self.__listenerThread.daemon = True
        self.__listenerThread.start()

    def stop_listening(self):
        """
        Tell the listener to exit by putting a sentinal ``None`` value in the
        queue.  Then join the thread, which should exit.
        """
        assert self.__listenerThread, "listener thread not set"
        self.__queue.put(None)
        self.__listenerThread.join()
        logger.info("Listening stopped")


class SimMessageQueueSender(object):
    """
    Wraps a multiprocessing Queue (created by a :class:`SimMessageQueue`),
    providing methods to send the types of messages that SimMessageQueue expects
    to receive.

    The standard use case:
    
      1.  Main UI (or equivalent process) creates a ``SimMessageQueue``
      2.  Main UI passes the py:property:`SimMessageQueue.queue` to child
          process(es) (initiated via multiprocessing ``Pool`` or ``Process``)
      3.  Each child process creates a ``SimMessageQueueSender`` with that 
          queue, and uses it to send messages back to the main UI.
        
    """
    def __init__(self, run, queue):
        """
        Initialize with a Queue and the child run number (required for
        every message)
        """
        assert run > 0, "Invalid run number"
        self.run = run
        self.queue = queue

    def send_status_message(self, status):
        """
        Put a status message into the queue.
        """
        msgs = (SimMessageQueue.STATUS_CANCELLED,
                SimMessageQueue.STATUS_COMPLETED,
                SimMessageQueue.STATUS_FAILED,
                SimMessageQueue.STATUS_STARTED)
        assert status in msgs, "Invalid status message"
        self.queue.put((self.run, _STATUS_MSG_TYPE, status))

    def send_progress_message(self, pctComplete):
        """
        Put a progress message into the queue.
        """
        assert 0 <= pctComplete and pctComplete <= 100, "Invalid progress value"
        self.queue.put((self.run, _PROGRESS_MSG_TYPE, pctComplete))



@apidocskip
def sendMsgsTest(run, queue):
    """
    This test function cannot be defined in the if __name__ == '__main__'
    and still be used as the target of a multiprocessing Process.
    Sorry about polluting the namespace :-)
    """
    sender = SimMessageQueueSender(run, queue)
    sender.send_status_message(SimMessageQueue.STATUS_STARTED)
    sender.send_progress_message(25)
    sender.send_progress_message(50)
    sender.send_progress_message(75)
    sender.send_progress_message(100)
    sender.send_status_message(SimMessageQueue.STATUS_COMPLETED)


if __name__ == '__main__':
    #from PySide.QtGui import *
    #app = QApplication(sys.argv)

    class TestMsgReceiver(object):
        def __init__(self, parent=None):
            super().__init__(parent)

        def receiveStatusMsg(self, run, status):
            msg = "Run {0}, Status: {1}".format(run, status)
            print("Status Message Received.", msg)

        def receiveProgressMsg(self, run, pctComplete):
            msg = "Run {0}, % Complete: {1}".format(run, pctComplete)
            print("Progress Message Received.", msg)

    class QueueTester(QObject):
        def __init__(self, msgQueue, msgReceiver):
            super().__init__(None)
            self.msgQueue = msgQueue
            self.msgReceiver = msgReceiver

        def test(self):
            msgQueue.start_listening()
            sendProcess = multiprocessing.Process(target=sendMsgsTest,
                                                  args=(1, msgQueue.queue))
            sendProcess.start()
            sendProcess.join()
            msgQueue.stop_listening()

    msgQueue = SimMessageQueue()
    msgReceiver = TestMsgReceiver()
    msgQueue.StatusMessageReceived.connect(msgReceiver.receiveStatusMsg)
    msgQueue.ProgressMessageReceived.connect(msgReceiver.receiveProgressMsg)
    tester = QueueTester(msgQueue, msgReceiver)
    tester.test()
    button = QPushButton("Test")
    button.clicked.connect(tester.test)
    button.show()
    app.exec_()
