#===============================================================================
# MODULE configuration
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimConfigParser class and related functions. The functions are
# the primary public interface; they access a SimConfigParser singleton that
# is created and initialized when this module is loaded.
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
import sys, os, configparser, logging
from fnmatch import fnmatchcase
from simprovise.core import SimError

_CONFIG_EXTENSION = '.ini'
_SIMPROVISE_CFG_BASENAME = 'simprovise.ini'
_MODEL_SCRIPT_ENV_VARNAME = 'SIMPROVISE_MODEL_SCRIPT'

# Configuration .ini file section names
_SIM_TIME = 'SimTime'
_LOGGING = 'Logging'
_SIM_RANDOM = 'SimRandom'
SIM_TRACE = 'SimTrace'
_OUTPUT_REPORT = 'Output Report'
_DATA_COLLECTION = 'Data Collection'

_ERROR_NAME = 'SimConfiguration Error'

class SimConfigParser(configparser.ConfigParser):
    """
    A subclass of ConfigParser that overloads the :meth:`getint` and
    :meth:`getboolean` methods and provides an additional :meth:`getstring`
    method. Also implements a :meth:`read_files` method that reads a set of
    .ini configuration files (see below) to initialize settings; these files
    are read on the first attempt by client code to obtain a configuration
    setting.
    
    All of these methods raise SimError exceptions (in place of the exceptions
    raised by the default ConfigParser). :meth:`getint` adds the ability
    to specify the minimum and/or maximum valid integer values. :meth:`getstring`
    validates the string setting value against an iterable of valid string
    values.
    
    Configuration Files:
    
    :meth:`read_files` reads up to four configuration files (if they exist)
    in the following order, where <filename>.py is the main (top-level) script:
    
      - simprovise.ini in the simprovise installation directory
      - simprovise.ini in the user's working directory
      - <filename>.ini in the same directory as <filename>.py 
      - <filename>.ini in the user's working directory 
    
    Setting values in later-read files supercede those from earlier-read
    files.
    
    <filename> and it's path default to the value of environment variable
    SIMPROVISE_MODEL_SCRIPT; if that variable is not set, it will default
    to sys.argv[0]. That path may be explicitly overridden via
    :func:`set_modelscript_path`. If this is called, it must be before any
    client code reads a setting, which implies that it must be called before
    the core simtime and simlogging modules are imported (since those
    modules read configuration settings on import).
    
    TODO: a more robust approach to obtaining the model script path; the
    one outlined above is admittedly a bit fragile/awkward, since we
    cannot rely on core infrastructure (which learns the model path too late
    to set it here.)     
    """
    def __init__(self):
        """
        """
        super().__init__()
        self._initialized = False
        self._modelscript_path = os.environ.get(_MODEL_SCRIPT_ENV_VARNAME,
                                                sys.argv[0])      
                
    def _initialize(self):
        """
        If not initialized, read the configuration file(s)
        """
        if self._initialized:
            return
        self.read_files()
        self._initialized = True
        
    def set_modelscript_path(self, path):
        """
        Set the modelscript path. In order to take full effect, this must be
        called before the any other caller obtains a configuration value
        (causing the config parser to be initialized and configuration files
        read). For now, at least, we raise an exception if that happens.
        """
        if self._initialized:
            msg = "SimConfiguration - cannot set model script to {0} after configuration files have been read"
            raise SimError(_ERROR_NAME, msg, path)
        self._modelscript_path = path
                   
    def getint(self, section, option, minvalue=None, maxvalue=None, **kwargs):
        """
        Gets and returns an integer setting value. 
        """
        self._initialize()
        try:            
            strvalue = self.get(section, option, **kwargs)
            value = super().getint(section, option, **kwargs)
        except ValueError as e:
            msg = "SimConfiguration {0} {1} setting ({2}) must be an integer"
            raise SimError(_ERROR_NAME, msg, section, option, strvalue)
        except Exception as e:
            msg = "Error reading SimConfiguration setting {0} {1}: {2}"
            raise SimError(_ERROR_NAME, msg, section, option, e)
            
            
        if minvalue and value < minvalue:
            msg = "SimConfiguration {0} {1} setting ({3}) is cannot be less than {2}"
            raise SimError(_ERROR_NAME, msg, section, option, minvalue, value)
        if maxvalue and value > maxvalue:
            msg = "SimConfiguration {0} {1} setting ({3}) is cannot be greater than {2}"
            raise SimError(_ERROR_NAME, msg, section, option, maxvalue, value)
        
        return value
    
    def getboolean(self, section, option, **kwargs):
        """
        Gets and returns a boolean setting value. Behavior is identical to
        (and calls) the default parser :meth:`getboolean`, except that all
        exceptions are converted to :class:`~.simexception.SimError`
        exceptions.
        """
        self._initialize()
        try:            
            strvalue = self.get(section, option, **kwargs)
            return super().getboolean(section, option, **kwargs)
        except ValueError as e:
            msg = "SimConfiguration {0} {1} setting ({2}) must be a boolean equivalent"
            raise SimError(_ERROR_NAME, msg, section, option, strvalue)
        except Exception as e:
            msg = "Error reading SimConfiguration setting {0} {1}: {2}"
            raise SimError(_ERROR_NAME, msg, section, option, e)
        
    def getstring(self, section, option, valid_values, **kwargs):
        """
        Get and return a string setting value, after validating that
        value against a passed iterable of valid values. The validation
        is case-insensitive, and the value is returned lowercase.
        """
        self._initialize()
        try:            
            value = self.get(section, option, **kwargs)
        except Exception as e:
            msg = "Error reading SimConfiguration setting {0} {1}: {2}"
            raise SimError(_ERROR_NAME, msg, section, option, e)
        
        lvalue = value.lower()
        if lvalue in valid_values:
            return lvalue
        else:
            msg = "SimConfiguration {0} {1} setting ({2}) must be one of: {3}"
            raise SimError(_ERROR_NAME, msg, section, option, value, valid_values)
        
    def get_unvalidated_string(self, section, option, **kwargs):
        """
        """
        self._initialize()
        try:            
            return self.get(section, option, **kwargs)
        except Exception as e:
            msg = "Error reading SimConfiguration setting {0} {1}: {2}"
            raise SimError(_ERROR_NAME, msg, section, option, e)
        
    def read_files(self):
        """
        Read (if they exist) configuration files in the following order,
        where <filename>.py is the script being executed (argv[0]):
        
          - simprovise.ini in the simprovise installation directory
          - simprovise.ini in the user's working directory
          - <filename>.ini in the same directory as <filename>.py 
          - <filename>.ini in the user's working directory 
        
        Setting values in later-read files supercede those from earlier-read
        files.
        """
        install_dir = os.path.split(os.path.dirname(__file__))[0]
        #script_dir = os.path.split(sys.argv[0])[0]
         
        install_cfg_filename = os.path.join(install_dir, _SIMPROVISE_CFG_BASENAME)
        local_cfg_filename = os.path.join(os.getcwd(), _SIMPROVISE_CFG_BASENAME)
        
        script_path = self._modelscript_path     
        script_cfg_filename = os.path.splitext(script_path)[0] + _CONFIG_EXTENSION
        local_script_cfg_filename = os.path.join(os.getcwd(),
                                                 os.path.basename(script_cfg_filename))
        
        #print(script_cfg_filename, local_script_cfg_filename, install_cfg_filename, local_cfg_filename)
        # The configuration files to be read (if they exist) in the order
        # in which they should be read, starting with the default configuration
        # in the installation directory
        cfg_files = [install_cfg_filename, local_cfg_filename,
                             script_cfg_filename, local_script_cfg_filename]
        
        
        # Eliminate duplicates while maintaining order
        cfg_files = list(dict.fromkeys(cfg_files))
        
        try:
             
            files_read = self.read(cfg_files)
            files_not_read = set(cfg_files) - set(files_read)
            if files_read:
                print("Configuration files processed:", files_read)
            if files_not_read:
                print("Configuration files not found:", files_not_read)
        except Exception as e:
            msg = "Error parsing one or more simprovise configuration files {0}: {1}"
            raise SimError(_ERROR_NAME, msg, cfg_files, e)
                            

def _init():
    """
    Create and initialize a SimConfigParser singleton instance. The
    configuration files will be read lazily, on first request for a setting
    value.
    """
    config = SimConfigParser()
    return config
    
_config = _init()

def set_modelscript_path(path):
    """
    Set the simulation model script path, used to search for the last
    (and therefore highest priority) configuration .ini file.
    e.g. if the model script path is::
    
        /models/mymodel.py
    
    then then the last configuration file loaded is::
    
        /models/mymodel.ini
    
    By default, the model script path is the top-level script that was
    invoked - i.e, sys.argv[0]. This function can be used to change that
    if a different script is used to run the model. **HOWEVER**...
    
    if called, it **MUST** be done before any simprovise modules other
    than this one (``simprovise.core.configuration``) are imported because
    those other simprovise modules are likely to (directly or indirectly)
    load and read configuration values, at which point it's too late to
    modify the configuration. It will raise an exception if called after the
    configuration is read/initialized.
    
    In other words, if :meth:`set_modelscript_path` is to be called, it should
    be at the very top of the top-level script before other simprovise imports::
    
        # First simprovise import
        import simprovise.core.configuration as simconfig
        simconfig.set_modelscript_path(path)
        
        # Other simprovise imports ....

    """
    _config.set_modelscript_path(path)

#===============================================================================
# SimTime setting accessors
#===============================================================================
def get_base_timeunit():
    """
    Return the base timeunit as an integer [0-2] or None (dimensionless).
    The caller will need to convert a return integer vallue to simtime.Unit,
    since importing simtime here creates a circular import.
    """
    from simprovise.core import SimError
    
    
    unitvalue = {'seconds' : 0, 'second': 0, 
                 'minutes' : 1, 'minute': 1,
                 'hours' : 2, 'hour': 2,
                 'none' : None
                 }    
    
    unitstr = _config.get(_SIM_TIME, 'BaseTimeUnit', fallback='seconds')
    
    try:
        return unitvalue[unitstr.lower()]
    except KeyError:
        errmsg = "Invalid SimTime BaseTimeUnit: {0}"
        raise SimError(_ERROR_NAME, errmsg, unitstr)

   
#===============================================================================
# SimLogging setting accessors
#===============================================================================
def get_logging_enabled():
    """
    Return a boolean indicating whether SimLogging is enabled
    """
    return _config.getboolean(_LOGGING, 'enabled', fallback=True)
  
def get_logging_level(module_name=None):
    """
    Return a logging level setting, converted from string to a
    logging module flag value.
    
    If the passed module_name is None, we want the base/default logging
    level, found with the 'level' key.
    
    If the passed module_name is not None, is is assumed to be a
    qualified simprovise module (e.g. 'simprovise.modeling.resource');
    in that case, the module name is the key (and the value should still
    be a valid level string).
    
    The base/default fallback level is WARNING (which probably should
    not be encountered). For modules, the fallback level is NOTSET,
    which indicates that the configuration file has not specified a level
    value for that module.
    
    :param module_name: The fully qualified name module/logger whose level
                        is to be set, or None to set the base logger level
    :type module_name:  ``str`` or ``None``
    
    """
    logging_level = {'debug': logging.DEBUG, 
                     'info': logging.INFO,
                     'warning': logging.WARNING,
                     'error': logging.ERROR,
                     'critical': logging.CRITICAL,
                     'notset': logging.NOTSET}
                     
    valid_values = logging_level.keys()
    
    if module_name is None:
        levelstr = _config.getstring(_LOGGING, 'level', valid_values,
                                     fallback='warning')
    else:
        levelstr = _config.getstring(_LOGGING, module_name, valid_values,
                                     fallback='notset')     
 
    return logging_level[levelstr], levelstr

#===============================================================================
# SimRandom setting accessors
#===============================================================================
def get_PRNstreams_per_run():
    """
    Return the number of independent pseudo-random number streams available
    for each model run
    """
    return _config.getint(_SIM_RANDOM, 'StreamsPerRun', minvalue=1, fallback=1)

def get_max_replications():
    """
    Return the maximum number of replications to support - the same as the
    maximum run number.
    """
    return _config.getint(_SIM_RANDOM, 'MaxReplications', minvalue=1, fallback=1)

   
#===============================================================================
# SimTrace setting accessors
#===============================================================================
def get_trace_enabled():
    """
    Return a boolean indicating whether simulation tracing is enabled.
    """
    return _config.getboolean(SIM_TRACE, 'enabled', fallback=True)
   
def get_tracetype():
    """
    Return the tracetype as a string - either 'table' or 'csv'.
    Raises if the setting is not one of those values (case-insensitive)
    """
    valid_values = ('table', 'csv')
    return _config.getstring(SIM_TRACE, 'TraceType', valid_values, fallback='table')

def get_trace_maxevents():
    """
    Return the maximum number of events to include in the trace. Must be 
    non-negative. A value of zero indicates no limit.
    """
    return _config.getint(SIM_TRACE, 'MaxEvents', minvalue=0, fallback=100)
   
def get_trace_destination():
    """
    Return the trace output destination as a string - either 'stdout' or 'file'.
    Raises if the setting is not one of those values (case-insensitive)
    """
    valid_values = ('stdout', 'file')
    return _config.getstring(SIM_TRACE, 'Destination', valid_values, fallback='stdout')

#===============================================================================
# Output Report setting accessors
#===============================================================================
def get_output_report_destination():
    """
    Return the output summary report destination as a string - either 'stdout'
    or 'file'.
    Raises if the setting is not one of those values (case-insensitive)
    """
    valid_values = ('stdout', 'file')
    return _config.getstring(_OUTPUT_REPORT, 'Destination', valid_values, fallback='stdout')


#===============================================================================
# Data Collection setting accessors
#===============================================================================
def get_element_data_collection_disabled(element_id):
    """
    Returns ``True`` if data collection should be disabled for the element
    identified by the passed element ID (based on values for the
    Data Collection `Disable Elements` option).
    """
    option_value = _config.get_unvalidated_string(_DATA_COLLECTION,
                                                  'Disable Elements').strip()
    
    if not option_value:
        return False
    
    patterns = option_value.split(',')
    matches = [fnmatchcase(element_id, pattern.strip()) for pattern in patterns]
    return True in matches

def get_dataset_data_collection_disabled(element_id, dataset_name):
    """
    Returns ``True`` if data collection should be disabled for the dataset
    identified by the passed element ID and dataset name (based on values for the
    Data Collection `Disable Datasets` option).
    
    The option value consists of zero or more comma-delimited entries;
    Each entry should consist of one or two whitespace delimited patterns
    to be used by :func:`fnmatchcase`.
    
    If there are two patterns, we match the first against the element ID
    and the second against the dataset ID. If there is just one pattern, we
    match it only against the dataset ID - the element ID does not matter.
    
    Entries without a pattern are ignored; entries with more than two
    patterns are ignored after a warning is issued.
    """
    option_value = _config.get_unvalidated_string(_DATA_COLLECTION,
                                                  'Disable Datasets').strip()
    
    if not option_value:
        return False
    
    entries = [value.split() for value in option_value.split(',')]
    
    # Validate entry length - we'll just ignore empty entries (two commas
    # in a row with just whitespace). If we get an entry with three or more
    # tokens, we'll issue a warning and move on, skipping that entry.
    invalid_entries = [entry for entry in entries if len(entry) > 2]
    if invalid_entries:
        msg = "SimConfiguration - Invalid Disable Datasets entry %s; comma-delimited entries must contain two patterns or less"
        logging.warn(msg, option_value)
        # Raising an exception here seems a bit extreme.
        #raise SimError(_ERROR_NAME, msg, option_value)
    
    # If there is only one pattern in the entry, we match just the dataset ID;
    # we're looking for datasets that match in any element.
    matches1 = [entry for entry in entries
                if len(entry) == 1 and fnmatchcase(dataset_name, entry[0])]
    
    # If there are two patterns, the first pattern matches the element ID,
    # the second the dataset ID
    matches2 = [entry for entry in entries
                if len(entry) == 2 and fnmatchcase(element_id, entry[0])
                and fnmatchcase(dataset_name, entry[1])]
            
    return bool(matches1 or matches2)


if __name__ == '__main__':
    try:
        scriptpath = "..\\demos\\mm_1.py"
        set_modelscript_path(scriptpath)
        print("base time unit:", get_base_timeunit())
        print("logging enabled:", get_logging_enabled())
        print("logging level:", get_logging_level())
        print("PRN streams/run:", get_PRNstreams_per_run())
        print("max replications:", get_max_replications())
        print("trace enabled:", get_trace_enabled())
        print("trace type:", get_tracetype())
        print("data collection element:", get_element_data_collection_disabled('TestLoc3.server'))
        print("data collection dataset:", get_dataset_data_collection_disabled('TestLoc3.server', 'DownTime'))
        print("data collection dataset:", get_dataset_data_collection_disabled('TestLoc3.server', 'ProcessTime'))
        print("data collection dataset:", get_dataset_data_collection_disabled('TestLoc3.server', 'TestProcessTime'))
        
        # This should raise
        set_modelscript_path(scriptpath)
    except Exception as e:
        print(e)