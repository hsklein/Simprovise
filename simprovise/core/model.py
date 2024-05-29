#===============================================================================
# MODULE model
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimModel class and the SimModel singleton instance.
#===============================================================================
__all__ = ['SimModel']

import sys, os
from simprovise.core import SimError, SimLogging, SimEntity, SimProcess
from simprovise.core.location import SimStaticObject
from simprovise.core.utility import SimUtility
from simprovise.core.simelement import SimElement
from simprovise.core.agent import SimAgent

logger = SimLogging.get_logger(__name__)

_ERROR_NAME = "SimModelError"

_PY_EXTENSION = '.py'
_SCRIPT_MODULE_NAME = "SimMain"
   
class SimModel(object):
    """
    SimModel manages access to a simulation model's simulation elements. There is
    only one model at a time, so the class is also a singleton.
    
    The simulation elements are maintained in a dictionary keyed by element ID.
    SimModel includes methods to register and access elements and their datasets.
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
        Loads a passed model script by importing it, returning the SimModel.model()
        singleton in the imported namespace. Since it is imported, the main program in
        the script does not execute.
        
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
        
    @property
    def filename(self):
        """
        The file path of the model script loaded via
        :meth:`load_model_from_script`.
        
        TODO figure out how to get filename, module if the simulation is run
        directly from the model script
        
        :return: filesystem path to the loaded model script, or None
        :rtype:  `str` or None
        
        """
        return self._filename
        
    @property
    def model_module(self):
        """
        The Python module loaded via :meth:`load_model_from_script`.
         
        :return: Python module or None
        
        """
        return self._module
    
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
        for e in SimProcess.elements.values():
            yield e
        for e in SimEntity.elements.values():
            yield e
        for e in SimStaticObject.elements.values():
            yield e
            
    @property
    def agents(self):
        """
        A generator returning all :class:`~.agent.SimAgent` objects in the
        model.
        """
        for agent in SimAgent.agents:
            yield agent
               
    @property
    def static_objects(self):
        """
        A generator that returns a all :class:`~.location.SimStaticObject`
        elements in the model
         """
        for e in SimStaticObject.elements.values():
            yield e
    
    @property
    def process_elements(self):
        """
        A generator that returns a all :class:`~.process.SimProcess`
        classes in the model
        """
        for e in SimProcess.elements.values():
            yield e
     
    @property
    def entity_elements(self):
        """
        A generator that returns a all :class:`~.entity.SimEntity`
        classes in the model
        """
        for e in SimEntity.elements.values():
            yield e
            
    def has_static_object(self, elementid):
        """
        Returns True if there is a :class:`~.location.SimStaticObject`
        with the passed element ID registered in the model, False
        otherwise.
        
        :param elementid: The element ID of the static object to query for
        :type elementid:  `str`
    
        """
        return elementid in SimStaticObject.elements
    
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
        if elementid in SimStaticObject.elements:
            return SimStaticObject.elements[elementid]
        else:
            msg = "get_static_object({0}): element ID not found"
            raise SimError(_ERROR_NAME, msg, elementid)
    
    def get_entity_element(self, entity_cls):
        """
        Returns the registered :class:`~.entity.SimEntityElement` for the 
        passed entity class; raises a :class:`~.simexception.SimError` if
        not found, or the passed parameter is not a SimEntity subclass.
        
        :param entity_cls: The entity class corresponding to the requested
                           :class:`~.entity.SimEntityElement`
        :type entity_cls:  `class`
                           
        :return:           The specified static entity element
        :rtype:            :class:`~.entity.SimEntityElement`
        
        """
        if not issubclass(entity_cls, SimEntity):
            msg = "get_entity_element({0}): parameter is either not a class or not a subclass of SimEntity"
            raise SimError(_ERROR_NAME, msg, entity_cls)
            
        elementid = SimElement.get_full_class_name(entity_cls)
        
        if elementid in SimEntity.elements:
            return SimEntity.elements[elementid]
        else:
            msg = "get_entity_element({0}): element ID not found"
            raise SimError(_ERROR_NAME, msg, elementid)
    
    def get_process_element(self, process_cls):
        """
        Returns the registered :class:`~.process.SimProcessElement` for the 
        passed process class; raises a :class:`~.simexception.SimError` if
        not found, or the passed parameter is not a SimProcess subclass.
        
        :param process_cls: The process class corresponding to the requested
                            :class:`~.process.SimProcessElement`
        :type entity_cls:  `class`
        
        :return:            The specified process element
        :rtype:             :class:`~.process.SimProcessElement`
        
        """
        if not issubclass(process_cls, SimProcess):
            msg = "get_process_element({0}): parameter is either not a class or not a subclass of SimProcess"
            raise SimError(_ERROR_NAME, msg, process_cls)
            
        elementid = SimElement.get_full_class_name(process_cls)
        
        if elementid in SimProcess.elements:
            return SimProcess.elements[elementid]
        else:
            msg = "get_process_element({0}): element ID not found"
            raise SimError(_ERROR_NAME, msg, elementid)
                 
        
logger.info("Creating SimModel singleton in module: %s", __name__)
SimModel._theModel = SimModel()    

if __name__ == '__main__':
    from simprovise.core import SimSimpleResource
    
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
        
