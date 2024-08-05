#===============================================================================
# MODULE model
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimModel class and the SimModel singleton instance.
#
# This program is free software: you can redistribute it and/or modify it under 
# the terms of the GNU General Public License as published by the Free Software 
# Foundation, either version 3 of the License, or (at your option) any later 
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with 
# this program. If not, see <https://www.gnu.org/licenses/>. 
#===============================================================================
__all__ = ['SimModel']

import sys, os
from simprovise.core import SimError
from simprovise.core.simlogging import SimLogging
from simprovise.core.utility import SimUtility
from simprovise.core.simelement import SimElement
from simprovise.core.apidoc import apidocskip

logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "SimModelError"

_PY_EXTENSION = '.py'
_SCRIPT_MODULE_NAME = "SimMain"
   
class SimModel(object):
    """
    SimModel manages access to a simulation model's simulation elements
    (subclasses of class :class:`SimElement`). There is only one model at a
    time, so the class is also a singleton.
    
    The simulation elements are maintained in a dictionary keyed by element ID.
    SimModel includes methods to register and access elements and their
    datasets.
    
    SimModel's primary role is to provide objects outside of the Simprovise
    core package with access to the current model's simulation objects and
    their data.
    
    For example, the ``database`` package uses SimModel to access any or
    all of the :class:`.datacollector.Dataset` objects in the model and
    assign them a database-specific :class:`.datacollector.DataSink` object.
    Modeling code can access static objects
    (e.g. :class:`resources<simprovise.modeling.resource.SimResource>`)
    defined in other modules via :meth:`get_static_object`.
    
    SimModel also provides a method (:meth:`SimModel.load_model_from_script`)
    that loads and imports a model (Python) script; this method is typically
    called when the model script is not the ``__main__`` program.
    """
    _theModel = None    # singleton instance
    
    @staticmethod
    def model():
        """
        :return: The singleton SimModel instance
        :rtype:  :class:`SimModel`
        
        """
        assert SimModel._theModel, "SimModel singleton not instantiated"
        return SimModel._theModel
    
    @staticmethod
    def load_model_from_script(scriptpath):
        """
        Loads a passed model script by importing it, returning the
        SimModel.model() singleton in the imported namespace. Since it is
        imported, the main program in the script does not execute.
        
        :param scriptpath: The filesystem path of Python script defining
                           the main model.
        :type scriptpaht:  `str`
        
        """
        logger.info("Loading script file: %s", scriptpath)
        assert scriptpath, "No script path supplied to SimModel.load_model_from_script()"
        extension = os.path.splitext(scriptpath)[1]
        assert extension == _PY_EXTENSION, "Script path argument to SimModel.load_model_from_script() must have a .py extension"
        
        try:           
            modelModule = SimUtility.load_module_from_file(scriptpath,
                                                           _SCRIPT_MODULE_NAME)
            model = SimModel.model()
            model._filename = scriptpath
            model._module = modelModule
        except Exception as e:
            logger.exception("Failure loading model %s from script into module: %s: %s",
                             scriptpath, _SCRIPT_MODULE_NAME, e)
            raise SimError(_ERROR_NAME, "Failure loading model script: {0}", scriptpath)

        logger.info("Loaded model %s from script %s into module: %s",
                    model, scriptpath, modelModule.__name__)
        return model
        #return SimModel.model()

    def __init__(self):
        """
        """
        self._filename = None
        self._module = None
        self._agents = set()
        self._processElements = {}
        self._entityElements = {}
        self._staticObjects = {}
        
    def _register_agent(self, agent):
        """
        """
        self._agents.add(agent)
        
    def _register_process_element(self, element):
        """
        Add a SimProcessElement to the dictionary. This method should only
        be called by SimProcess.__init_subclass__()
        """
        if element.element_id in self._processElements:
            msg = "SimProcess class with element ID {0} is already registered"
            raise SimError(_ERROR_NAME, msg, element.element_id)
        self._processElements[element.element_id] = element
        
    def _register_entity_element(self, element):
        """
        Add a SimEntityElement to the dictionary. This method should only
        be called by SimEntity.__init_subclass__()
        """
        if element.element_id in self._entityElements:
            msg = "SimEntity class with element ID {0} is already registered"
            raise SimError(_ERROR_NAME, msg, element.element_id)
        self._entityElements[element.element_id] = element
       
    def _register_static_object(self, statObj):
        """
        Add a SimStaticObject to the dictionary. This method should only
        be called by SimStaticObject.__init__()
        """
        if statObj.element_id in self._staticObjects:
            msg = "Static Object with element ID {0} is already registered"
            raise SimError(_ERROR_NAME, msg, statObj.element_id)
        self._staticObjects[statObj.element_id] = statObj
        
    @apidocskip
    def clear_registry_partial(self):
        """
        Clear all of the registered agents and staticObjects.
        Intended for use by unit test setup/teardown.
        """
        self._agents.clear()
        #self._processElements.clear()
        #self._entityElements.clear()
        self._staticObjects.clear()
        
                
    @property
    def filename(self):
        """
        The file path of the model script. If a script was loaded via
        :meth:`load_model_from_script`, returns the file path that was
        loaded. Otherwise, we assume the model script is being run
        directly, so we return sys.argv[0]
        
        TODO figure out how to get filename, module if the simulation is run
        directly from the model script
        
        :return: filesystem path to the loaded model script, or None
        :rtype:  `str` or None
        
        """
        if self._filename:           
            return self._filename
        else:
            return sys.argv[0]
        
    @property
    def model_module(self):
        """
        The Python module loaded via :meth:`load_model_from_script`.
         
        :return: Python module or None
        
        """
        return self._module
    
    def loaded_from_script(self):
        """
        :return: True if the model was loaded via :meth:`load_model_from_script`
        :rtype:  `bool`
        """
        return self._module is not None
    
    @property
    def datasets(self):
        """
        A generator that returns all :class:`datasets {.simelement.Dataset}`
        for all :class:`~.simelement.SimElement` objects in the model -
        the static object datasets, process element datasets and entity
        element datasets.
        """
        for e in self.elements:
            for dset in e.datasets:
                yield dset
                     
    @property
    def elements(self):
        """
        A generator that returns all :class:`SimElements
        <.simelement.SimElement>` in the model.
        """
        for e in self._processElements.values():
            yield e
        for e in self._entityElements.values():
            yield e
        for e in self._staticObjects.values():
            yield e
            
    @property
    def agents(self):
        """
        A generator returning all :class:`~.agent.SimAgent` objects in the
        model.
        """
        for agent in self._agents:
            yield agent
               
    @property
    def static_objects(self):
        """
        A generator that returns a all :class:`~.location.SimStaticObject`
        elements in the model
         """
        for e in self._staticObjects.values():
            yield e
    
    @property
    def process_elements(self):
        """
        A generator that returns a all :class:`~.process.SimProcess`
        classes in the model
        """
        for e in self._processElements.values():
            yield e
     
    @property
    def entity_elements(self):
        """
        A generator that returns a all :class:`~.entity.SimEntity`
        classes in the model
        """
        for e in self._entityElements.values():
            yield e
            
    def has_static_object(self, elementid):
        """
        Returns True if there is a :class:`~.location.SimStaticObject`
        with the passed element ID registered in the model, False
        otherwise.
        
        :param elementid: The element ID of the static object to query for
        :type elementid:  `str`
    
        """
        return elementid in self._staticObjects
    
    def get_static_object(self, elementid):
        """
        Returns the registered :class:`~.location.SimStaticObject` with the
        passed element ID; raises a :class:`~.simexception.SimError` if
        not found.
        
        :param elementid: The element ID of the requested static object
        :type elementid:  `str`
        
        :return: The specified static object
        :rtype:  :class:`~.location.SimStaticObject`
        
        """
        if elementid in self._staticObjects:
            return self._staticObjects[elementid]
        else:
            msg = "get_static_object({0}): element ID not found"
            raise SimError(_ERROR_NAME, msg, elementid)
    
    def get_entity_element(self, entity_cls):
        """
        Returns the registered :class:`~.entity.SimEntityElement` for the 
        passed entity class; raises a :class:`~.simexception.SimError` if
        not found.
        
        :param entity_cls: The entity class corresponding to the requested
                           :class:`~simprovise.modeling.entity.SimEntity`
        :type entity_cls:  `class`
                           
        :return:           The specified static entity element
        :rtype:            :class:`~simprovise.modeling.entity.SimEntityElement`
        
        """
        elementid = SimElement.get_full_class_name(entity_cls)
        
        if elementid in self._entityElements:
            return self._entityElements[elementid]
        else:
            msg = "get_entity_element({0}): element ID {1} not found"
            raise SimError(_ERROR_NAME, msg, entity_cls, elementid)
    
    def get_process_element(self, process_cls):
        """
        Returns the registered :class:`~.process.SimProcessElement` for the 
        passed process class; raises a :class:`~.simexception.SimError` if
        not found.
        
        :param process_cls: The process class corresponding to the requested
                            :class:`~.process.SimProcessElement`
        :type entity_cls:  `class`
        
        :return:            The specified process element
        :rtype:             :class:`~.process.SimProcessElement`
        
        """
        elementid = SimElement.get_full_class_name(process_cls)
        
        if elementid in self._processElements:
            return self._processElements[elementid]
        else:
            msg = "get_process_element({0}): element ID {1} not found"
            raise SimError(_ERROR_NAME, msg, process_cls, elementid)
                 
        
logger.info("Creating SimModel singleton in module: %s, pid %s", __name__, os.getpid())
SimModel._theModel = SimModel()    

if __name__ == '__main__':
    from simprovise.modeling import SimProcess
    
    class testProcess(SimProcess):
        """
        """
       
    scriptpath = "..\\models\\mm1.py"
    model = SimModel.load_model_from_script(scriptpath)
    #r = SimSimpleResource("Test Resource")
    
    print("SimElements in model")
    for e in SimModel.model().elements:
        print("   ", e.element_id, e.__class__)
                
    print("Entity Elements in model")
    for e in SimModel.model().entity_elements:
        print("   ", e.element_id)
        
    print("Static Objects in model")
    for e in SimModel.model().static_objects:
        print("   ", e.element_id)
            
    print("Process Elements in model")
    for e in SimModel.model().process_elements:
        print("   ", e.element_id)
        
    print("Datasets in model")
    for ds in SimModel.model().datasets:
        print("   ", ds.element_id, ds.name)
        
    print("model has static object Queue:",
          SimModel.model().has_static_object("Queue"))
        
    print("model has static object FakeQueue:",
          SimModel.model().has_static_object("FakeQueue"))
    
    print("Queue static object:",
          SimModel.model().get_static_object("Queue").element_id)
    
    try:
        print("FakeQueue static object:",
              SimModel.model().get_static_object("FakeQueue").element_id)
    except SimError as e:
        print(e)
        
