#===============================================================================
# MODULE configuration
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Defines the SimConfigParser class and related functions. The functions are
# the primary public interface; they access a SimConfigParser singleton that
# is created and initialized when this module is loaded.
#===============================================================================
import sys, os, configparser, logging
from simprovise.core import SimError

_CONFIG_EXTENSION = '.ini'
_SIMPROVISE_CFG_BASENAME = 'simprovise.ini'

# ENV variable name for model local_cfg_filename?

# Configuration .ini file section names
_SIM_TIME = 'SimTime'
_LOGGING = 'Logging'
_SIM_RANDOM = 'SimRandom'
SIM_TRACE = 'SimTrace'

_ERROR_NAME = 'SimConfiguration Error'

def testset():
    print("**** configuration testset() *****")

class SimConfigParser(configparser.ConfigParser):
    """
    A subclass of ConfigParser that overloads the :meth:`getint` and
    :meth:`getboolean` methods and provides an additional :meth:`getstring`
    method.
    
    All of these methods raise SimError exceptions (in place of the exceptions
    raised by the default ConfigParser). :meth:`getint` adds the ability
    to specify the minimum and/or maximum valid integer values. :meth:`getstring`
    validates the string setting value against an iterable of valid string
    values.
    """
    def getint(self, section, option, minvalue=None, maxvalue=None, **kwargs):
        """
        Gets and returns an integer setting value. 
        """
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
                       

def _init():
    """
    Create and initialize a SimConfigParser singleton instance. Right now,
    reads (if they exist) configuration files in the following order,
    where <filename>.py is the script being executed (argv[0]):
    
      - simprovise.ini in the simprovise installation directory
      - simprovise.ini in the caller's working directory
      - <filename>.ini in the same directory as <filename>.py 
      - <filename>.ini in the caller's working directory 
    
    Setting values in later-read files supercede those from earlier-read
    files.
    
    TODO:
    We'd actually like to read configuration file's based on the
    name of the model script, which may not be the same as thescript being executed
    via the command line or equivalent - e.g., if our main script calls
    simulation.execute_script(). Unfortunately, as currently built,
    the configuration is read at the time that the simtime and simlogging
    modules are loaded (in order to properly configure those modules) and
    the filename is not available until after that point.
    
    The fix: while a refactoring/reorganization of the simprovise.core module
     may be a good idea regardless -in order to reduce the number of modules 
    that get imported on first touch (and reduce/eliminate the imports in __init__.py),
    that probably won't be sufficient to solve this problem completely, since
    execute_script() runs the model script in-process and requires SimTime
    arguments. The only "easy" option that comes to mind is a bit of a hack:
    communicate the model (or other) configuration filename out-of-band,
    e.g. via environment variable before importing any simprovise modules.
    A __slightly__ less hacky mechanism would require reorganizing so that
    this module can be imported without creating an import of simtime/simlogging;
    then the filename could be communicated via function call rather than
    environment variable. That would also require lazily initialization here.

    """
    install_dir = os.path.split(os.path.dirname(__file__))[0]
    script_dir = os.path.split(sys.argv[0])[0]
     
    install_cfg_filename = os.path.join(install_dir, _SIMPROVISE_CFG_BASENAME)
    local_cfg_filename = os.path.join(os.getcwd(), _SIMPROVISE_CFG_BASENAME)
    script_cfg_filename = os.path.splitext(sys.argv[0])[0] + _CONFIG_EXTENSION
    local_script_cfg_filename = os.path.join(os.getcwd(),
                                             os.path.basename(script_cfg_filename))
    
    #print(script_cfg_filename, local_script_cfg_filename, install_cfg_filename, local_cfg_filename)
    config = SimConfigParser()
    
    try:
        # The configuration files to be read (if they exist) in the order
        # in which they should be read, starting with the default configuration
        # in the installation directory
        cfg_files = [install_cfg_filename, local_cfg_filename,
                     script_cfg_filename, local_script_cfg_filename]
        # Eliminate duplicates while maintaining order
        cfg_files = list(dict.fromkeys(cfg_files))
        
        files_read = config.read(cfg_files)
        files_not_read = set(cfg_files) - set(files_read)
        if files_read:
            print("Configuration files processed:", files_read)
        if files_not_read:
            print("Configuration files not found:", files_not_read)
    except Exception as e:
        msg = "Error parsing one or more simprovise configuration files {0}: {1}"
        raise SimError(_ERROR_NAME, msg, cfg_files, e)
    
    return config
    
_config = _init()

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
  
def get_logging_level():
    """
    Return the the logging level setting, converted from string to a
    logging module flag value.
    """
    logging_level = {'debug': logging.DEBUG, 
                     'info': logging.INFO,
                     'warning': logging.WARNING,
                     'error': logging.ERROR,
                     'critical': logging.CRITICAL}
    valid_values = logging_level.keys()
    
    levelstr = _config.getstring(_LOGGING, 'level', valid_values,
                                 fallback='warning')
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
    return _config.getstring(SIM_TRACE, 'Destination', valid_values, fallback='table')

def get_max_trace_events():
    """
    Return the maximum number of trace events to show/log.
    """
    return _config.getint(_SIM_RANDOM, 'MaxReplications', minvalue=0, fallback=100)

#def get_warmuplength():
    #"""
    #Return the Run Control warmup length as a SimTime
    #"""
    #value = _config.get(RUN_CONTROL, 'WarmupLength', fallback='0')
    #return _get_simtime(value, 'WarmupLength')

#def get_batchlength():
    #"""
    #Return the Run Control warmup length as a SimTime
    #"""
    #value = _config.get(RUN_CONTROL, 'BatchLength')
    #return _get_simtime(value, 'BatchLength')

#def get_numbatches():
    #"""
    #"""
    #return _config.getint(RUN_CONTROL, 'NumBatches', fallback=1)

#def _get_simtime(value, option):
    #"""
    #Convert a SimTime string to a SimTime. The string should consist of
    #an 
    #"""
    #def to_number(string):
        #try:
            #return int(string)
        #except ValueError:
            #pass
        #try:
            #return float(string)
        #except ValueError:
            #exceptstr = "First value for configuration {0} is non-numeric: {1}"
            #raise Exception(exceptstr.format(option, value))
            
    #from simprovise.core.simtime import SimTime
    #valuestr = value.split()
    
    #if len(valuestr) == 0 or len(valuestr) > 2:
        #exceptstr = "configuration option {0} must have one or two values: {1}"
        #raise Exception(exceptstr.format(option, value))
    
    #timevalue = to_number(valuestr[0])
    #if timevalue < 0:
        #exceptstr = "First value for configuration {0} is negative: {1}"
        #raise Exception(exceptstr.format(option, value))
        
    #if len(valuestr) == 2:
        #timeunit = _timeunit_from_str(valuestr[1], option)
        #return SimTime(timevalue, timeunit)
    #else:       
        #return SimTime(timevalue)



if __name__ == '__main__':
    try:
        print("base time unit:", get_base_timeunit())
        print("logging enabled:", get_logging_enabled())
        print("logging level:", get_logging_level())
        print("PRN streams/run:", get_PRNstreams_per_run())
        print("max replications:", get_max_replications())
        print("trace enabled:", get_trace_enabled())
        print("trace type:", get_tracetype())
    except Exception as e:
        print(e)