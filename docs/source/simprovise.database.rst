
===============================
The simprovise.database Package
===============================

The ``database`` package has one module, ``outputdb``, which encapsulates
read, write, and management access to the sqlite3 output database.
All sqlite3 API calls and SQL query definitions are contained in this
module.

This module also contains the methods that "wire" simulation 
:class:`simprovise.core.datacollector.Dataset` objects to the database
by setting their :class:`datasinks <simprovise.core.datasink.Datasink>`
to the database write sink class objects defined here
(:class:`~simprovise.database.outputdb.SimDbDatasink` and
:class:`~simprovise.database.outputdb.SimDbTimeSeriesDatasink`)

.. note::
    This section documents the main APIs used to directly access
    simprovise output databases. A description of the database
    schema itself can be found in :doc:`output_database`.

Database Management and Update Classes
======================================

.. autoclass:: simprovise.database.outputdb.SimDatabaseManager
    :members:

.. autoclass:: simprovise.database.outputdb.SimOutputDatabase
    :members:

.. autoclass:: simprovise.database.outputdb.SimLiveOutputDatabase
    :members:
    :show-inheritance:

.. autoclass:: simprovise.database.outputdb.SimDbDatasink
    :members:
    :show-inheritance:

.. autoclass:: simprovise.database.outputdb.SimDbTimeSeriesDatasink
    :members:
    :show-inheritance:
   
Database Queries/Reporting Classes
==================================

.. autoclass:: simprovise.database.outputdb.SimDatasetSummaryData
    :members:

.. autoclass:: simprovise.database.outputdb.DbDataset
    :members:
