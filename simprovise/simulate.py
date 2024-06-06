#===============================================================================
# MODULE simmain
#
# Copyright (C) 2014-2017 Howard Klein - All Rights Reserved
#
# Implements the command line interface to the simulator.
#===============================================================================
import os, argparse
import logging
from simprovise.core.simtime import Unit as tu
from simprovise.core.apidoc import apidoc, apidocskip

_SECOND_UNITS = ('s', 'sec', 'secs', 'second', 'seconds')
_MINUTE_UNITS = ('m', 'min', 'mins', 'minute', 'minutes')
_HOUR_UNITS = ('h', 'hr', 'hrs', 'hour', 'hours')
_VALID_UNIT_STRINGS = (_SECOND_UNITS, _MINUTE_UNITS, _HOUR_UNITS)

_SCRIPT_EXTENSION = '.py'
_OUTPUT_DB_EXTENSION = '.simoutput'
_CSV_EXTENSION = '.csv'

# Customized usage strings for both the execute and load commands

_EXECUTE_USAGE = """
usage: %(prog)s <model path>
                [-h/--help]
                [-wl/--warmuplength n {secs, mins, hrs}]
                [-bl/--batchlength n {secs, mins, hrs}]
                [-nb/--nbatches n]
                [-r/--run <run number> [to run number]]
                [-v/--verbosity {error, warn, info, debug}]
                [-r/--report]
                [-rt/--rangetype {total, iqr}]
                [-csv]
                [-s/--savedb]
"""

_LOAD_USAGE = """
usage: %(prog)s <simoutput database path>
                [-h/--help]
                [-v/--verbosity {error, warn, info, debug}]
                [-r/--report]
                [-rt/--rangetype {total, iqr}]
                [-csv]
"""


def _getfilepath(inpath, requiredExt, mode):
    """
    Return an absolute file path based on an input path (which may be
    relative to the current working directory) and extension. If the input
    path does not include an extension, the returned path is based on the
    input path plus the specified extension. If the input path does include
    an extension, it it must be the same as the specified extension.

    Before returning a path, the function confirms that it is accessable
    in the specified mode ('r' or 'w') via os.access.

    This function is intended to be part of an ArgParse type specification
    function. As such, if any the path is not valid/accessable or the
    extension is wrong, it raises an ArgumentTypeError.
    """
    assert requiredExt and requiredExt[0] == '.'
    root, ext = os.path.splitext(inpath)
    if not ext or ext == '.':
        path = os.path.abspath(root + requiredExt)
    elif ext == requiredExt:
        path = os.path.abspath(inpath)
    else:
        msg = 'path extension, if supplied, must be {0}'.format(requiredExt)
        raise argparse.ArgumentTypeError(msg)

    if os.access(path, mode):
        return path
    else:
        modestr = 'writable' if mode is os.W_OK else 'readable'
        msg = 'path {0} is not a {1} file'.format(path, modestr)
        raise argparse.ArgumentTypeError(msg)

# ArgParse type specification functions
@apidocskip
def modelpath(argstring):
    return _getfilepath(argstring, _SCRIPT_EXTENSION, os.R_OK)

@apidocskip
def dbpath(argstring):
    return _getfilepath(argstring, _OUTPUT_DB_EXTENSION, os.R_OK)

def _getoutputfilepath(inputpath, outputextension, parser):
    """
    Construct and test a path for an output file. The output file path is be
    placed in the current working directory; it has the same filename as the
    passed input path and a passed extension.

    This function will confirm that the output file can be written by opening
    it. If the file does not already exist, it is then deleted to minimize
    the trash.
    """
    outputdir = os.getcwd()
    root = os.path.splitext(inputpath)[0]
    inputdir, fname = os.path.split(root)
    if outputdir:
        p = os.path.join(outputdir, fname + outputextension)
        outputpath = os.path.abspath(p)
    else:
        outputpath = os.path.abspath(root + outputextension)

    exists = os.path.exists(outputpath)
    try:
        f = open(outputpath, 'w')
        f.close()
        if not exists:
            os.remove(outputpath)
        return outputpath
    except OSError:
        msg = 'cannot write to path {0}'.format(outputpath)
        parser.error(msg)

def _positiveInt(string):
    """
    Helper function that converts a string to an integer, raising
    a ValueError if the string does not represent a positive
    integer.
    """
    try:
        numvalue = int(string)
    except ValueError:
        msg = 'argument must be a positive integer'
        raise argparse.ArgumentTypeError(msg)

    if numvalue <= 0:
        msg = 'argument must be greater than zero'
        raise argparse.ArgumentTypeError(msg)

    return numvalue

def _positive(string):
    """
    Helper function that converts a string to either a positive int (first
    choice) or float (if conversion to int fails). Raises a ValueError if
    either:
    a) The passed string cannot be converted to either numeric type, or
    b) The resulting value is not greater than zero

    Otherwise, returns the int or float value.
    """
    try:
        val = int(string)
    except ValueError:
        val = float(string)
    if val > 0:
        return val
    else:
        raise ValueError

class TimeAction(argparse.Action):
    """
    A custom argeparse.Action subclass that validates the two required arguments
    for a time-specification option (warmup length or batch length). The first
    argument must be a positive number; the second argument should be a string
    representing a time unit. There are multiple valid string representations
    for each of the three time units (seconds, minutes, hours). The number
    argument is converted to an int or float; the time unit is converted to to
    a lower case version of the first valid representation for that time unit.
    (e.g., 'seconds', 'secs' or 'sec' will all be converted to 's')

    If the arguments are both valid, the validated and converted arguments are
    written as a pair to the passed. argument namespace.
    """
    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, **kwargs)
        self.option_string = kwargs['metavar']

    def __call__(self, parser, namespace, values, option_string=None):
        outvalues = []
        try:
            outvalues.append(_positive(values[0]))
        except ValueError:
            msg = 'First argument supplied to {0} option must be a positive number'
            parser.error(msg.format(self.option_string))

        for unitoptions in _VALID_UNIT_STRINGS:
            if values[1].lower() in unitoptions:
                units = unitoptions[0]
                outvalues.append(units)
                setattr(namespace, self.dest, outvalues)
                return
        msg = 'Second argument supplied to {0} option must specify time unit (secs/mins/hrs)'
        parser.error(msg.format(self.option_string))

class SimulationRunAction(argparse.Action):
    """
    A custom argeparse.Action subclass that validates the run numbers specified
    as arguments to the -run option. The user may specify either one or two run
    numbers. If only one number is specified, it must be an integer in range
    1-100; in that case, it is the run number for the only simulation to be
    executed. if a second number is specified, it must be an integer greater than
    the first number and <= 100; the two numbers together specify the range
    of run numbers for a series of multiple replications. e.g., -run 20 32 will
    result in the execution of 13 replications, using run numbers 20 through 32.

    If the argument(s) are valid, they are converted to integers and saved as a
    tuple. (If a single run number argument is specified, the tuple will contain
    just one value; if a range is specified, the tuple will contain two values)
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if len(values) > 2:
            msg = '-run option argument(s) must be either a single run number or a range specified by two run numbers'
            parser.error(msg)
            return

        runs = []
        try:
            for value in values:
                run = int(value)
                if not (0 < run and run <= 100):
                    msg = 'Run numbers must be an integer in range 1-100'
                    parser.error(msg)
                    return
                elif runs and runs[0] >= run:
                    msg = 'first -run argument must be less than the second argument'
                    parser.error(msg)
                    return
                runs.append(run)
        except ValueError:
            msg = '-run argument(s) must be integers in range 1-100'
            parser.error(msg)

        setattr(namespace, self.dest, runs)

@apidocskip
def runCommandLine(inargs=None):
    """
    Parses and executes the passed arguments, or sys.argv if no arguments are
    passed. (The ability to handle passed arguments exists primarily to
    facilitate testing.) Parsing is performed via the argparse.ArgParse.

    The simulator command line supports two commands: execute (which executes
    one or more simulation replications) and load (which loads a previously
    saved simulation output database). As such, the parser creates a subparser
    for each of those commands.

    The execute command requires a command line argument specifying the path
    of the model script (.py file) to be executed. The load command requires
    a command line argument specifying the path of an existing simulation
    output database.

    The following options are available to both command subparsers:

    -r/--report:        Generate a summary statistic report (based on the
                        executed simulation or specified output database);
                        outputs are means of the statistics if the output
                        contains multiple replications or batches
    -rt/--rangetype:    Specify addition range columns on the generated report
                        when the result/output contains multiple replications
                        or batches; Rangetype may be either 'iqr' (Inter-quartile
                        range) or 'total' (lowest to highest mean)
    -csv:               Generate a CSV file of summary statistics. The
                        generated file will have the same filename as the
                        model script or loaded output database, with extension
                        .csv. It will be written to the current working
                        directory, silently overwriting any existing file.
    -v/--verbosity:     Set logging level: error, warn, info or debug
                        (defaults to warn)

    Additional options for the execute command:

    -wl/--warmuplength: Length of simulation warmup, in simulated time. Option
                        requires both a time value (positive number) and time
                        unit (seconds, minutes, or hours, which may be
                        abbreviated)
    -bl/--batchlength:  Length of each simulation batch, in simulated time.
                        Option requires similar arguments as warmuplength.
    -nb/--nbatches:     Number of batches to simulate in each simulation run.
                        Requires a positive integer argument.
    -s/--savedb:        Save the simulation output database. Database filename
                        will be the same as the model script filename, with a
                        .simoutput extension. The saved database will be put in
                        the current working directory, silently overwriting any
                        existing file.
    -run:               Specify (via argument) either the run number of the
                        single simulation run to execute, or a range of run
                        numbers (via two arguments, from and to numbers),
                        specifying multiple replications.

    If any of the warmuplength, batchlength or nbatches options are not
    specified, the value will default to the value specified (implicitly or
    explicitly) by the model script. When the run option is not specified,
    the default action will be to execute a single simulation replication for
    run number 1.
    """
    def handleExecute(args):
        if not (args.report or args.csv or args.savedb):
            parser.error("For execute, at least one of report, csv or savedb options are required")

        args.csvpath = None
        args.savedbpath = None
        if args.csv:
            args.csvpath = _getoutputfilepath(args.modelpath, _CSV_EXTENSION, parser)
        if args.savedb:
            args.savedbpath = _getoutputfilepath(args.modelpath, _OUTPUT_DB_EXTENSION,
                                                parser)
        _execute(args)

    def handleLoad(args):
        if not (args.report or args.csv):
            parser.error("For load, at least one of report or csv options are required")

        args.csvpath = None
        args.savedbpath = None
        if args.csv:
            args.csvpath = _getoutputfilepath(args.dbpath, _CSV_EXTENSION, parser)
        _load_output_database(args)

    desc = "Execute a Simalytix simulation model or load a previously generated simulation results database"
    cmdhelp = "execute <model script path> or report <simulation output database path>"
    timehelp = "optional time lengths must be > 0, optional time units are seconds, minutes or hours"
    executehelp = "execute <model path>: execute simulation script <model path>; " + timehelp
    loadhelp = "load <simulation output database path>: load previously generated simulation results"

    parser = argparse.ArgumentParser(description=desc)
    subparsers = parser.add_subparsers(help=cmdhelp, dest='cmd')
    executeparser = subparsers.add_parser('execute', aliases=['ex'],
                                          help=executehelp, usage=_EXECUTE_USAGE)
    executeparser.set_defaults(func=handleExecute)

    loadparser = subparsers.add_parser('load', aliases=['ld'],
                                       help=loadhelp, usage=_LOAD_USAGE)
    loadparser.set_defaults(func=handleLoad)

    for p in (executeparser, loadparser):
        p.add_argument('-v', '--verbosity', default='warn',
                       help="set logging verbosity; default is 'warn'",
                       choices=['error', 'warn', 'info', 'debug'])
        p.add_argument('-r', '--report', action='store_true',
                       help="generate summary statistics report for each dataset")
        p.add_argument('-rt', '--rangetype', default=None,
                       help="add statistic ranges to report; default is 'none'",
                       choices=['total', 'iqr'])
        p.add_argument('-csv', action='store_true',
                       help="generate a csv file of summary statistics by run and dataset; overwrite existing csv file, if any")

    modelpathhelp = "model script path; extension, if supplied, should be .py"
    executeparser.add_argument('modelpath', type=modelpath, help=modelpathhelp)

    executeparser.add_argument('-s', '--savedb', action='store_true',
                               help="save output database; overwrite existing database for script, if any")

    executeparser.add_argument('-wl', '--warmuplength', nargs=2, action=TimeAction,
                               default=None, metavar='warmup length',
                               help="simulation warmup length <n> [time unit]")

    executeparser.add_argument('-bl', '--batchlength', nargs=2, action=TimeAction,
                               default=None, metavar='batch length',
                               help="simulation batch length <n> [time unit]")

    executeparser.add_argument('-nb', '--nbatches', type=_positiveInt,
                               default=None, metavar='# of batches',
                               help="number of batches in simulation run")

    executeparser.add_argument('-run', nargs='+',
                               action=SimulationRunAction,
                               default=[1,],
                               help="run number to simulate, or range of range of run number replications")

    dbpathhelp = "simulation output database path; extension, if supplied, should be .simoutput"
    loadparser.add_argument('dbpath', type=dbpath, help=dbpathhelp)

    args = parser.parse_args(inargs)
    args.func(args)

def _process_sim_result(args, simResult):
    """
    Process the passed SimulationResult object by executing the operations
    specified by the passed arguments, which may include any combination of
    report, CSV file generation, or database save.
    """
    if args.report:
        simResult.print_summary(rangetype=args.rangetype)
    if args.csv:
        simResult.save_summary_csv(args.csvpath)
    if args.savedbpath:
        simResult.save_database_as(args.savedbpath)

def _set_verbosity(verbosity):
    """
    Set logging level based on verbosity argument
    """
    from Simalytix.Core import SimLogging

    level = {'error': logging.ERROR, 'warn': logging.WARN,
             'info': logging.INFO, 'debug': logging.DEBUG}

    if verbosity:
        assert verbosity in level, "Invalid verbosity specifier"
        SimLogging.set_level(level[verbosity])

def _execute(args):
    """
    Run execute command - executes one or more replications, then peforms
    user-specified processing on the result.
    """
    from Simalytix import Simulation
    from Simalytix.Core import simtime, SimTime

    TIME_UNIT = {_SECOND_UNITS[0]: tu.SECONDS,
                 _MINUTE_UNITS[0]: tu.MINUTES,
                 _HOUR_UNITS[0]: tu.HOURS,
                 }

    def makeSimTime(arg):
        if arg is None:
            return None
        assert len(arg) == 2, "Time length argument does not contain two values"
        assert arg[1] in TIME_UNIT, "Invalid time unit argument"
        return SimTime(arg[0], TIME_UNIT[arg[1]])

    _set_verbosity(args.verbosity)

    modelpath = args.modelpath
    warmupLength = makeSimTime(args.warmuplength)
    batchLength = makeSimTime(args.batchlength)
    nbatches = args.nbatches

    if len(args.run) == 1:
        run = args.run[0]
        with Simulation.execute_script(modelpath, warmupLength, batchLength,
                                      nbatches, run) as simResult:
            _process_sim_result(args, simResult)
    else:
        assert len(args.run) == 2, "More than two run numbers in args.run"
        fromRun = args.run[0]
        toRun = args.run[1]
        with Simulation.replicate(modelpath, warmupLength, batchLength,
                                  nbatches, fromRun, toRun) as simResult:
            _process_sim_result(args, simResult)

def _load_output_database(args):
    """
    Run the load command. Loads the previously saved output database into a
    SimulationResult object, and then peforms user-specified processing on
    the result.
    """
    from Simalytix import SimulationResult

    print("loading saved simulation output from", dbpath, "...")
    with SimulationResult(dbpath=args.dbpath) as simResult:
        _process_sim_result(args, simResult)

def main():
    """
    Main entry point. Invoke runCommandLine to parse sys.argv and execute the
    parsed command.
    """
    runCommandLine()



if __name__ == '__main__':
    main()
