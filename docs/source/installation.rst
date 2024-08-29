============
Installation
============

Coming soon::

  pip install simprovise
   
Until then, the latest version is available from the simprovise 
`GitHub repository. <https://github.com/hsklein/Simprovise>`_
In this case, the dependencies (**greenlet** and **numpy**) will need to be 
installed as well. (See below.)

**simprovise** is implemented entirely in Python (i.e. it includes
no additional C extensions).


Dependencies
============

Greenlet
--------

**greenlet** provides a lightweight coroutines (*greenlets*) that can be
cooperately scheduled within a single OS thread. The *simprovise* methods
(in class :class:`~simprovise.modeling.process.SimProcess`) that can "block" for
some period of simulated time are implemented using greenlets.

Greenlets are similar to the generator-based coroutines that are available
from the standard CPython distribution, while providing some additional
flexability. In particular, use of the **yield** keyword is not required and
nested methods/functions can be used as well; see:

https://greenlet.readthedocs.io/en/latest/history.html

For more information, see:

https://pypi.org/project/greenlet/

NumPy and SciPy
----------------

The `NumPy <https://numpy.org/>`_  and `SciPy <https://scipy.org/>`_
scientific computing packages are used to provide the following 
**simprovise** functionality:

* Pseudo-random number generation. See 
  :ref:`this <random-number-streams-concept-label>` for details.
* Probability distributions for modeling. See
  :ref:`this <random-number-distribution-concept-label>` for more information.
* Calculation of summary statistics 
  (e.g. mean, standard error/deviation, order statistics, confidence
  intervals) for simulation output analysis.