
=================================
The simprovise.runcontrol Package
=================================

The ``runcontrol`` package consists of three modules:

* :ref:`runcontrol-replication-module-label`, which implements the two
  primary classes in this package - 
  :class:`~simprovise.runcontrol.replication.SimReplicator` and
  :class:`~simprovise.runcontrol.replication.SimReplication`
  
* :ref:`runcontrol-messagequeue-module-label`, which implements 
  classes used to send replication status and progress messages to a 
  Qt (PySide) GUI application. When Qt is not present (i.e. only the
  base Simprovise library is being used, and simulations are executed
  via command-line Python scripts), the message queue does essentially nothing.
  
* :ref:`runcontrol-simruncontrol-module-label`, which performs two major
  functions on behalf of ``SimReplicators``/``SimReplications``:
  
  - Sending status/progress messages through the 
    :class:`~simprovise.runcontrol.messagequeue.SimMessageQueue`.
  - Scheduling :class:`SimEvents <~simprovise.core.simevent.SimEvent>`
    that trigger end-of-warmup and end-of-batch processing.

.. note::

    The Qt interfaces were built for a Simprovise prototype that included a GUI.
    That GUI has been stripped from the current release as part of an effort
    to separate base/core functionality from other tools (such as a GUI).
    To what extent the Qt support in these classes will work for a future GUI 
    application is to be determined. The messages are processed through
    a :class:`~simprovise.runcontrol.messagequeue.SimMessageQueue` are likely
    to work (or be close to working) with a
    :class:`~simprovise.runcontrol.replication.SimReplicator` as long as it
    is running in the same process as a GUI. 

    *TLDR*: The Qt objects in this package are currently replaced by no-op 
    mock objects. They may or may not work (using "real"Qt objects) for
    future Qt-based applications built on top of Simprovise without 
    modification.

.. _runcontrol-replication-module-label:

The ``replication`` Module
=========================================

.. autoclass:: simprovise.runcontrol.replication.SimReplicator
    :members:

.. autoclass:: simprovise.runcontrol.replication.SimReplication
    :members:

.. autofunction:: simprovise.runcontrol.replication.execute_replication


.. _runcontrol-messagequeue-module-label:

The ``messagequeue`` Module
=========================================

.. autoclass:: simprovise.runcontrol.messagequeue.SimMessageQueue
    :members:

.. autoclass:: simprovise.runcontrol.messagequeue.SimMessageQueueSender
    :members:

.. _runcontrol-simruncontrol-module-label:

The ``simruncontrol`` Module
=========================================

Classes
-------

.. autoclass:: simprovise.runcontrol.simruncontrol.SimRunControlParameters
    :members:

.. autoclass:: simprovise.runcontrol.simruncontrol.SimReplicationParameters
    :members:

.. autoclass:: simprovise.runcontrol.simruncontrol.SimRunControlScheduler
    :members:
    
Event Classes
-------------

.. autoclass:: simprovise.runcontrol.simruncontrol.WarmupCompleteEvent
    :members:

.. autoclass:: simprovise.runcontrol.simruncontrol.BatchCompleteEvent
    :members:

.. autoclass:: simprovise.runcontrol.simruncontrol.SimProgressEvent
    :members:
