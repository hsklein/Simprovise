====================================
simprovise
====================================

**simprovise** is a Python library for process-based discrete event simulation. 
Simprovise modelers create models by using or inheriting from
classes representing simulation objects such as processes, resources,
resource pools, and locations (such as queues).

For example, the following code snippet implements the service process for 
an M/M/1 queuing model::

    queue = SimQueue("Queue")
    server = SimSimpleResource("Server")
    server_location = SimLocation("ServerLocation")
    customer_source = SimEntitySource("Source")
    customer_sink = SimEntitySink("Sink")

    mean_service_time = SimTime(8)
    service_time_generator = SimDistribution.exponential(mean_service_time)

    class mm1Process(SimProcess):
        def run(self):
            service_time = next(service_time_generator)
            customer = self.entity
            customer.move_to(queue)
            with self.acquire(server) as resource_assignment:
                customer.move_to(server_location)
                self.wait_for(service_time)            
            customer.move_to(customer_sink)

**simprovise** also provides APIs and tools for model execution, 
data collection, and output analysis, including:

* Parallel execution of multiple replications, each using  an independent 
  set of pseudo-random number streams.
* Output reports including summary statistics, through both batch means and
  replication analysis.
  
Simprovise implements process-based simulation using lightweight coroutines
provided by `greenlet. <https://pypi.org/project/greenlet/>`_ 
Greenlets are similar to the generator-based coroutines that are available
from the standard CPython distribution, while providing some additional
flexability. In particular, use of the ``yield`` keyword is not required,
and ``greenlet`` switching can occur in nested method calls.
In the case of simprovise, this allows blocking and process-switching to 
occur "under the covers" during a method call like ``acquire(resource)``;
a model developer using simprovise should have no need to see, use or even
understand the ``greenlet`` API.

Status
======

**simprovise** is under development, with an initial public release planned for
fall 2024. (So yes, the current development version should be considered 
unstable, though it includes almost all the features planned for the initial
release.)

Installation
============

For now, simprovise is only available via this repository; your PYTHONPATH
should be set to include the ``simprovise`` directory.
``greenlet`` and ``numpy`` can be installed from the Python Package Index 
(PyPI) via ``py install``. 

Documentation
=============

The current documentation can be found in the ``docs`` directory and built
using Sphinx. (It should be available online as well shortly.)

Other Dependencies
==================

Simprovise uses
`NumPy <https://numpy.org/doc/stable/index.html>`_ for psuedo-random-number
generation, probability distribution sampling, and calculation of summary
statistics.

Compatibility
=============

Simprovise has been developed using Python 3.12.2 (on Windows 11). 
It has been tested successfully on Linux (Ubuntu 22.04.4) 
running Python 3.9.19, 3.10.12, and 3.12.4.

Simprovise has **not** yet been tested on any other (non-CPython)
distributions.


License
=======

**simprovise** is available under the GNU General Public License version 3.
See the ``LICENSE`` file in this directory for details.