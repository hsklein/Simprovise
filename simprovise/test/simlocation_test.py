#===============================================================================
# MODULE simlocation_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# Unit tests for SimLocation and SimTransientObject classes
#===============================================================================
from simprovise.modeling import *
from simprovise.modeling.simobject import SimTransientObject
from simprovise.modeling.location import SimStaticObject
from simprovise.core.datacollector import SimDataCollector
from simprovise.core.simclock import SimClock
from simprovise.core.simtime import SimTime
from simprovise.core.model import SimModel
from simprovise.core import SimError
import unittest

class TestLocation(SimLocation):
    def __init__(self, name, locationObj=None, entryPointName=None):
        super().__init__(name, locationObj, entryPointName)
        self.enterCount = 0
        self.exitCount = 0
        
    def on_enter_impl(self, enteringObj): 
        self.enterCount += 1
        
    def on_exit_impl(self, exitingObj): 
        self.exitCount += 1
        
class MockSource(SimEntitySource):
    def __init__(self):
        super().__init__("MockSource")
        

class MockEntity(SimEntity):
    ""
  
class MockProcess(SimProcess):
    ""

# TestTransient and MockNamedObject need to inherit from SimEntity
# to pass assertion (since SimEntities are the only SimTransientObjects
# currently allowed)
class TestTransient(SimEntity):
    def __init__(self, name, source=None):
        super().__init__(source, MockProcess())
        self.name = name
        
class MockNamedObject(TestTransient):
    ""
    
def reinitialize():
    SimDataCollector.reinitialize()
    SimClock.initialize()
    # Hack to allow recreation of static objects for each test case
    SimModel.model().clear_registry_partial()

   
class SimEmptyLocationTests(unittest.TestCase):
    """
    Tests several variations of initial, empty SimLocations (one root, one child)
    """
    def setUp(self):
        reinitialize()
        rootLoc = SimLocation.root_location()
        self.root = rootLoc
        
        # variation 1: parent/child where child is the entry point for the parent
        self.parentLoc = TestLocation("Parent", rootLoc, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        
        # variation 2: parent/child where parent specifies a non-existent child as 
        # entry point
        self.parentLoc2 = TestLocation("Parent2", rootLoc, "NonExistent")
        self.childLoc2 = TestLocation("Child2", self.parentLoc2)
        
        # variation 3: parent/child where the root does not specify an entry point
        self.parentLoc3 = TestLocation("Parent3", rootLoc)
        self.childLoc3 = TestLocation("Child3", self.parentLoc3)
        
    def testParentElementID1(self):
        "Test: parent elementID is specified parent name"
        self.assertEqual(self.parentLoc.element_id, "Parent")
        
    def testParentElementID2(self):
        "Test: parent elementID is same as parent elementName"
        self.assertEqual(self.parentLoc.element_id, self.parentLoc.element_name)
        
    def testChildElementID1(self):
        "Test: child elementID is specified <parent name>.<child name>"
        self.assertEqual(self.childLoc.element_id, "Parent.Child")
        
    def testChildElementID2(self):
        "Test: child elementID is NOT same as child elementName"
        self.assertNotEqual(self.childLoc.element_id, self.childLoc.element_name)

    def testParentParent(self):
        "Test: parent's parent is root" 
        self.assertIs(self.parentLoc.parent_location, self.root)

    def testParentLocation(self):
        "Test: parent's location is root" 
        self.assertIs(self.parentLoc.location, self.root)

    def testParentNoEntries(self):
        "Test: parent location entry count is zero" 
        self.assertEqual(self.parentLoc.entries, 0)

    def testParentNoExits(self):
        "Test: parent location exit count is zero" 
        self.assertEqual(self.parentLoc.exits, 0)

    def testParentZeroPopulation(self):
        "Test: parent location current Population is zero" 
        self.assertEqual(self.parentLoc.current_population, 0)

    def testIsAncestorOf(self):
        "Test: parent location is ancestor of child" 
        self.assertTrue(self.parentLoc.is_ancestor_of(self.childLoc))

    def testChildParent(self):
        "Test: parent location is parent of child" 
        self.assertIs(self.childLoc.parent_location, self.parentLoc)

    def testParentEntryPoint(self):
        "Test: parent location entry point is the child location" 
        self.assertIs(self.parentLoc.entry_point, self.childLoc)

    def testChildEntryPoint(self):
        "Test: child location entry point is itself" 
        self.assertIs(self.childLoc.entry_point, self.childLoc)

    def testParent2EntryPoint(self):
        "Test: parent location 2 entry point raises an error (as entry point name is invalid)" 
        self.assertRaises(SimError, lambda: self.parentLoc2.entry_point)

    def testParent3EntryPoint(self):
        "Test: parent location 3 with a child and no entry point raises an error" 
        self.assertRaises(SimError, lambda: self.parentLoc3.entry_point)
         
    def testDuplicateAddRaises(self):
        "Test: re-adding the child location to the parent raises an error"
        self.assertRaises(SimError, lambda: self.parentLoc._add_child(self.childLoc))
        
    def testAddNotStaticChildRaises(self):
        "Test: addChild() with a non-static object raises and error"
        process = MockProcess()
        source = MockSource()
        testObj = MockEntity(source, process)
        self.assertRaises(SimError, lambda: self.parentLoc._add_child(testObj))
        
                       
class SimParentLocationEntryTests(unittest.TestCase):
    "Tests entry initial, empty SimLocations (one parent, one child)"
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc

        self.parentLoc = TestLocation("Parent", rootLoc, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        self.source = MockSource()
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [MockNamedObject(name, self.source) for name in names]

    def testParentEnter1(self):
        "Test: add five entries to parent location, entries == 5"
        for i in range(5):
            self.parentLoc.on_enter(self.testObj[i])
        self.assertEqual(self.parentLoc.entries, 5)

    def testParentEnter2(self):
        "Test: add five entries to parent location, Test class enterCount"
        for i in range(5):
            self.parentLoc.on_enter(self.testObj[i])
        self.assertEqual(self.parentLoc.enterCount, 5)

    def testParentEnter3(self):
        "Test: add five entries to parent location, exits == zero"
        for i in range(5):
            self.parentLoc.on_enter(self.testObj[i])
        self.assertEqual(self.parentLoc.exits, 0)

    def testParentEnter4(self):
        "Test: add five entries to parent location, Test class exitcount"
        for i in range(5):
            self.parentLoc.on_enter(self.testObj[i])
        self.assertEqual(self.parentLoc.exitCount, 0)

    def testParentEnterCurrentPopulation(self):
        "Test: add five entries to parent location, Test currentPopulation property"
        for i in range(5):
            self.parentLoc.on_enter(self.testObj[i])
        self.assertEqual(self.parentLoc.current_population, 5)

    def testParentEnterResidentCount(self):
        "Test: add five entries to parent location, Test location resident count"
        for i in range(5):
            self.parentLoc.on_enter(self.testObj[i])
        self.assertEqual(len(list(self.parentLoc.residents)), 5)

    def testParentDuplicateEnter(self):
        "Test: duplicate entry to parent location raises SimError"
        for i in range(5):
            self.parentLoc.on_enter(self.testObj[i])
        self.assertRaises(SimError, lambda: self.parentLoc.on_enter(self.testObj[1]))
        
    def testParentEnterIn(self):
        "Test: add three entries to parent location, 'in' syntax for an entry"
        for i in range(3):
            self.parentLoc.on_enter(self.testObj[i])
        self.assertTrue(self.testObj[1] in self.parentLoc)
        
    def testParentEnterNotIn(self):
        "Test: add three entries to parent location, 'not in' syntax for an entry"
        for i in range(3):
            self.parentLoc.on_enter(self.testObj[i])
        self.assertTrue(self.testObj[3] not in self.parentLoc)
        
   
class SimParentLocationExitTests(unittest.TestCase):
    """
    Tests exit-related functions/properties on a parent location object
    Setup:  Five objects enter at time zero, two exit at time 5, two
    more exit at time 10.
    """
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc
        
        self.parentLoc = TestLocation("Parent", rootLoc, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        self.source = MockSource()
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [MockNamedObject(name, self.source) for name in names]
        
        for i in range(5):
            self.parentLoc.on_enter(self.testObj[i])
        SimClock.advance_to(SimTime(5))
        self.parentLoc.on_exit(self.testObj[0], self.exitToLoc)
        self.parentLoc.on_exit(self.testObj[1], self.exitToLoc)
        SimClock.advance_to(SimTime(10))
        self.parentLoc.on_exit(self.testObj[2], self.exitToLoc)
        self.parentLoc.on_exit(self.testObj[3], self.exitToLoc)

    def testParentExit1(self):
        "Test entries property"
        self.assertEqual(self.parentLoc.entries, 5)

    def testParentExit2(self):
        "Test exits property"
        self.assertEqual(self.parentLoc.exits, 4)

    def testParentExit3(self):
        "Test current population property"
        self.assertEqual(self.parentLoc.current_population, 1)

    def testParentExit4(self):
        "Test current residents length"
        self.assertEqual(len(list(self.parentLoc.residents)), 1)
      
    def testParentExitIn(self):
        "Test 'in' for object still in location after exits"
        self.assertTrue(self.testObj[4] in self.parentLoc)
        
    def testParentExitNotIn(self):
        "Test 'in' for object that has exited location"
        self.assertFalse(self.testObj[1] in self.parentLoc)
        
    def testParentExitDuplicate(self):
        "Test attempt to onExit with an object that has already exited raises"
        self.assertRaises(SimError, 
                lambda: self.parentLoc.on_exit(self.testObj[1], self.exitToLoc))
            
    def testParentReEntry(self):
        "Test that object can re-enter location after exiting"
        self.parentLoc.on_enter(self.testObj[1])
        self.assertTrue(self.testObj[1] in self.parentLoc)

# TODO Child location onEnter/onExit tests
        
               
class SimChildLocationEntryTests1(unittest.TestCase):
    """
    Tests parent and child location state after one object has entered the 
    parent location and one object has entered the child location
    """
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc
    
        self.parentLoc = TestLocation("Parent", rootLoc, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        self.source = MockSource()
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [MockNamedObject(name, self.source) for name in names]
        
        self.parentLoc.on_enter(self.testObj[0])
        self.childLoc.on_enter(self.testObj[1])

    def testChildEntries(self):
        "Test: child location entries = 1"
        self.assertEqual(self.childLoc.entries, 1)

    def testChildEnterCount(self):
        "Test: child location enterCount = 1"
        self.assertEqual(self.childLoc.enterCount, 1)

    def testChildResidentCount(self):
        "Test: child location residents count = 1"
        self.assertEqual(len(list(self.childLoc.residents)), 1)

    def testParentEntries(self):
        "Test: parent location entries = 2"
        self.assertEqual(self.parentLoc.entries, 2)

    def testParentResidentCount(self):
        "Test: parent location residents count = 2"
        self.assertEqual(len(list(self.parentLoc.residents)), 2)

    def testChildEnterCount(self):
        "Test: parent location enterCount = 2"
        self.assertEqual(self.parentLoc.enterCount, 2)

    def testChildExits(self):
        "Test: child location exits = 0"
        self.assertEqual(self.childLoc.exits, 0)

    def testParentExits(self):
        "Test: parent location exits = 0"
        self.assertEqual(self.parentLoc.exits, 0)

    def testChildPopulation(self):
        "Test: child location currentPopulation = 1"
        self.assertEqual(self.childLoc.current_population, 1)

    def testParentPopulation(self):
        "Test: parent location currentPopulation = 2"
        self.assertEqual(self.parentLoc.current_population, 2)

    def test1IsInChild(self):
        "Test: test object 1 in child location"
        self.assertTrue(self.testObj[1] in self.childLoc)

    def test1IsInParent(self):
        "Test: test object 1 in child location"
        self.assertTrue(self.testObj[1] in self.parentLoc)

    def test0NotInChild(self):
        "Test: test object 0 not in child location"
        self.assertFalse(self.testObj[0] in self.childLoc)

    def test0InParent(self):
        "Test: test object 0 is in parent location"
        self.assertTrue(self.testObj[0] in self.parentLoc)
        
               
class SimChildLocationEntryTests2(unittest.TestCase):
    """
    Tests parent and child location state after one object has entered the 
    parent location and one object has entered the child location, and (after
    simulated time (2) passes), the object that entered the parent location
    enters the child location.
    """
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc
    
        self.parentLoc = TestLocation("Parent", rootLoc, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        self.source = MockSource()
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [MockNamedObject(name, self.source) for name in names]

        self.parentLoc.on_enter(self.testObj[0])
        self.childLoc.on_enter(self.testObj[1])
        SimClock.advance_to(SimTime(2))
        self.childLoc.on_enter(self.testObj[0])
        
    def testChildEntries(self):
        "Test: child location entries = 2"
        self.assertEqual(self.childLoc.entries, 2)

    def testChildEnterCount(self):
        "Test: child location enterCount = 2"
        self.assertEqual(self.childLoc.enterCount, 2)

    def testParentEntries(self):
        "Test: parent location entries = 2"
        self.assertEqual(self.parentLoc.entries, 2)

    def testParentEnterCount(self):
        "Test: parent location enterCount = 2"
        self.assertEqual(self.parentLoc.enterCount, 2)

    def testParentResidentCount(self):
        "Test: parent location residents count = 2"
        self.assertEqual(len(list(self.parentLoc.residents)), 2)

    def testChildExits(self):
        "Test: child location exits = 0"
        self.assertEqual(self.childLoc.exits, 0)

    def testParentExits(self):
        "Test: parent location exits = 0"
        self.assertEqual(self.parentLoc.exits, 0)

    def testChildPopulation(self):
        "Test: child location currentPopulation = 2"
        self.assertEqual(self.childLoc.current_population, 2)

    def testParentPopulation(self):
        "Test: parent location currentPopulation = 2"
        self.assertEqual(self.parentLoc.current_population, 2)

    def test1IsInChild(self):
        "Test: test object 1 in child location"
        self.assertTrue(self.testObj[1] in self.childLoc)

    def test1IsInParent(self):
        "Test: test object 1 in parent location"
        self.assertTrue(self.testObj[1] in self.parentLoc)

    def test0InChild(self):
        "Test: test object 0 not in child location"
        self.assertTrue(self.testObj[0] in self.childLoc)

    def test0InParent(self):
        "Test: test object 0 is in parent location"
        self.assertTrue(self.testObj[0] in self.parentLoc)

               
class SimChildLocationExitTests1(unittest.TestCase):
    """
    Creates four locations - a parent with two children, and a second parent
    (exitToLoc).
    Tests parent and child location state after the following onEnter and
    onExit calls:
    
    - object 0 enters the parent location
    - objects 1, 2 and 3 enter the first child location
    - The simulation clock is advanced two units
    - object 0 exits the parent location, nextLoc = exitToLoc
    - object 1 exits the child location , nextLoc = exitToLoc
    - object 2 exits the child location, nextLoc = second child location
    - object 3 exits the child location, nextLoc = the parent location  
    - object 4 enters the child location
    """
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc
    
        self.parentLoc = TestLocation("Parent", rootLoc, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        self.childLoc2 = TestLocation("Child2", self.parentLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        self.source = MockSource()
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [MockNamedObject(name, self.source) for name in names]

        self.parentLoc.on_enter(self.testObj[0])
        self.childLoc.on_enter(self.testObj[1])
        self.childLoc.on_enter(self.testObj[2])
        self.childLoc.on_enter(self.testObj[3])
        SimClock.advance_to(SimTime(2))
        self.childLoc.on_enter(self.testObj[4])
        self.parentLoc.on_exit(self.testObj[0], self.exitToLoc)
        self.childLoc.on_exit(self.testObj[1], self.exitToLoc)
        self.childLoc.on_exit(self.testObj[2], self.childLoc2)
        self.childLoc.on_exit(self.testObj[3], self.parentLoc)
        
    def testChildEntries(self):
        "Test: child location entries = 4"
        self.assertEqual(self.childLoc.entries, 4)

    def testChildEnterCount(self):
        "Test: child location enterCount = 4"
        self.assertEqual(self.childLoc.enterCount, 4)

    def testChild2Entries(self):
        "Test: child2 location entries = 0 "
        self.assertEqual(self.childLoc2.entries, 0)

    def tesParentEntries(self):
        "Test: root location entries = 5"
        self.assertEqual(self.parentLoc.entries, 5)

    def testParentEnterCount(self):
        "Test: root location enterCount = 5"
        self.assertEqual(self.parentLoc.enterCount, 5)

    def testChildExits(self):
        "Test: child location exits = 3"
        self.assertEqual(self.childLoc.exits, 3)

    def testChild2Exits(self):
        "Test: child2 location exits = 0"
        self.assertEqual(self.childLoc2.exits, 0)

    def testParentExits(self):
        "Test: parent location exits = 2"
        self.assertEqual(self.parentLoc.exits, 2)

    def testChildPopulation(self):
        "Test: child location currentPopulation = 1"
        self.assertEqual(self.childLoc.current_population, 1)

    def testChild2Population(self):
        "Test: child2 location currentPopulation = 0"
        self.assertEqual(self.childLoc2.current_population, 0)

    def testParentPopulation(self):
        "Test: parent location currentPopulation = 3"
        self.assertEqual(self.parentLoc.current_population, 3)

    def testExitLocPopulation(self):
        "Test: exitLoc location currentPopulation = 0"
        self.assertEqual(self.exitToLoc.current_population, 0)

    def test0NotInParent(self):
        "Test: test object 0 is not in parent location"
        self.assertFalse(self.testObj[0] in self.parentLoc)

    def test1IsNotInChild(self):
        "Test: test object 1 in child location"
        self.assertFalse(self.testObj[1] in self.childLoc)

    def test1IsInNotParent(self):
        "Test: test object 1 not in parent location"
        self.assertFalse(self.testObj[1] in self.parentLoc)

    def test1IsNotInExitLoc(self):
        "Test: test object 1 in exitTo location"
        self.assertFalse(self.testObj[1] in self.exitToLoc)

    def test2NotInChild(self):
        "Test: test object 2 not in child location"
        self.assertFalse(self.testObj[2] in self.childLoc)

    def test2InChild2(self):
        "Test: test object 2 not in child location2"
        self.assertFalse(self.testObj[2] in self.childLoc2)

    def test2InParent(self):
        "Test: test object 2 in parent location"
        self.assertTrue(self.testObj[2] in self.parentLoc)

    def test3NotInChild(self):
        "Test: test object 3 not in child location"
        self.assertFalse(self.testObj[3] in self.childLoc)

    def test3InParent(self):
        "Test: test object 3 in parent location"
        self.assertTrue(self.testObj[3] in self.parentLoc)

    def test4InChild(self):
        "Test: test object 3 not in child location"
        self.assertTrue(self.testObj[4] in self.childLoc)

    def test4NotInChild2(self):
        "Test: test object 4 not in child location 2"
        self.assertFalse(self.testObj[4] in self.childLoc2)

    def test4InParent(self):
        "Test: test object 4 in parent location"
        self.assertTrue(self.testObj[4] in self.parentLoc)
               
class SimStaticLocatableBaseTests(unittest.TestCase):
    """
    Creates a static (locatable) object with a specified location. Tests
    related location and locatable properties and methods.
    """
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc
    
        self.parentLoc = TestLocation("Parent", rootLoc, "Child")
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        self.staticTestObj = SimStaticObject("FixedTest", self.parentLoc)
                      
    def testLocation(self):
        "Test: fixed test object location property"
        self.assertIs(self.staticTestObj.location, self.parentLoc)
        
    def testParentEntries(self):
        "Test: parent entries is 0"
        self.assertEqual(self.parentLoc.entries, 0)
        
    def testParentPopulation(self):
        "Test: parent current population is 0"
        self.assertEqual(self.parentLoc.current_population, 0)
        
    def testStaticMoveRaises(self):
        "Test: attempt to move a static locatable object raises an error"
        self.assertRaises(SimError, lambda: self.staticTestObj.move_to(self.exitToLoc))
 
                   
class SimLocatableBaseTests(unittest.TestCase):
    """
    Creates five transient Locatable objects, with initial location entryLoc
    Also creates a static/fixed Locatable object at the root location.
    Tests state before any moves.
    """
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc
    
        self.parentLoc = TestLocation("Parent", rootLoc, None)
        self.childLoc = TestLocation("Child", self.parentLoc, "InvalidEntryPt")
        self.grandchildLoc = TestLocation("GrandChild", self.childLoc)
        self.entryLoc = TestLocation("EntryLoc", rootLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [TestTransient(name, self.entryLoc) for name in names]
        self.staticTestObj = SimStaticObject("FixedTest", self.parentLoc)
               
    def testLocation(self):
        "Test: non-static test object location property"
        self.assertIs(self.testObj[0].location, self.entryLoc)
        
    def testEntryLocEntries(self):
        "Test: entryLoc entries is 5"
        self.assertEqual(self.entryLoc.entries, 5)

    def testEntryLocPopulation(self):
        "Test: entryLoc current population is 5"
        self.assertEqual(self.entryLoc.current_population, 5)

    def testEntryLocResidents(self):
        "Test: entryLoc has 5 residents"
        self.assertEqual(len(list(self.entryLoc.residents)), 5)
        
    def testParentEntries(self):
        "Test: parent entries is 0"
        self.assertEqual(self.parentLoc.entries, 0)
        
    def testParentPopulation(self):
        "Test: parent current population is 0"
        self.assertEqual(self.parentLoc.current_population, 0)
        
    def testParentResidents(self):
        "Test: parentLoc has 5 residents"
        self.assertEqual(len(list(self.parentLoc.residents)), 0)
        
    def testMoveToTransientRaises(self):
        "Test: moving a locatable object to a transient (non-fixed) locatable raises an error"
        self.assertRaises(SimError, lambda: self.testObj[1].move_to(self.testObj[2]))
                
    def testMoveToCurrentLocationRaises(self):
        "Test: moving a locatable object to it's current location raises an error"
        self.assertRaises(SimError, lambda: self.testObj[1].move_to(self.entryLoc))
                
    def testMoveToParentRaises(self):
        """
        Test: moving a locatable object to a location with children and
        no defined entry point raises an error
        """
        self.assertRaises(SimError, lambda: self.testObj[1].move_to(self.childLoc))
                
    def testMoveToParentRaises(self):
        """
        Test: moving a locatable object to a location with children and
        an invalid entry point name (no such child object) raises an error
        """
        self.assertRaises(SimError, lambda: self.testObj[1].move_to(self.parentLoc))
    
               
class SimLocatableMoveTests(unittest.TestCase):
    """
    Creates five transient Locatable objects, with initial location entryLoc
    Also creates a static/fixed Locatable object at the parent location.  Then
    executes the following test locatable object moves:
    
    Time (0)
    - object 0 from entry to parent
    - object 1 from entry to parent
    - object 2 from entry to child
    - object 3 from entry to child
    - object 4 from entry to child
    
    Time (2)
    - object 0 from parent to exit
    - object 1 from parent to child
    - object 2 from child to child2
    - object 3 from child to exit
    - object 4 from child to parent
    
    """
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc
    
        self.entryLoc = TestLocation("EntryLoc", rootLoc)
        self.parentLoc = TestLocation("Parent", rootLoc, "RootEntryPoint")
        self.parentEntryPoint = TestLocation("RootEntryPoint", self.parentLoc)
        self.childLoc = TestLocation("Child", self.parentLoc)
        self.childLoc2 = TestLocation("Child2", self.parentLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
       
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [TestTransient(name, self.entryLoc) for name in names]
        self.staticTestObj = SimStaticObject("FixedTest", self.parentLoc)
                
        self.testObj[0].move_to(self.parentLoc)
        self.testObj[1].move_to(self.parentLoc)
        self.testObj[2].move_to(self.childLoc)
        self.testObj[3].move_to(self.childLoc)
        self.testObj[4].move_to(self.childLoc)
                
        SimClock.advance_to(SimTime(2))
        
        self.testObj[0].move_to(self.exitToLoc)
        self.testObj[1].move_to(self.childLoc)
        self.testObj[2].move_to(self.childLoc2)
        self.testObj[3].move_to(self.exitToLoc)
        self.testObj[4].move_to(self.parentLoc)
                
        SimClock.advance_to(SimTime(4))
                      
    def testLocation0(self):
        "Test: object 0 located at exit"
        self.assertIs(self.testObj[0].location, self.exitToLoc)
                      
    def testLocation1(self):
        "Test: object 1 located at child"
        self.assertIs(self.testObj[1].location, self.childLoc)
                      
    def testLocation1a(self):
        "Test: object 1 located at child entry point (which should equal child)"
        self.assertIs(self.testObj[1].location, self.childLoc.entry_point)
                      
    def testLocation2(self):
        "Test: object 2 located at child 2"
        self.assertIs(self.testObj[2].location, self.childLoc2)
                      
    def testLocation3(self):
        "Test: object 3 located at exit"
        self.assertIs(self.testObj[3].location, self.exitToLoc)
                      
    def testLocation4(self):
        "Test: object 4 located at parent entry point"
        self.assertIs(self.testObj[4].location, self.parentLoc.entry_point)
        
    def testObj0InExit(self):
        "Test: object 0 in exitTo location"
        self.assertTrue(self.testObj[0] in self.exitToLoc)
        
    def testObj0NotInParent(self):
        "Test: object 0 not in parent location"
        self.assertTrue(self.testObj[0] not in self.parentLoc)
        
    def testObj1InParent(self):
        "Test: object 1 in parent location"
        self.assertTrue(self.testObj[1] in self.parentLoc)
        
    def testObj1InChild(self):
        "Test: object 1 in child location"
        self.assertTrue(self.testObj[1] in self.childLoc)
        
    def testObj1NotInChild2(self):
        "Test: object 1 in child location"
        self.assertTrue(self.testObj[1] not in self.childLoc2)
        
    def testObj1NotInExit(self):
        "Test: object 1 in child location"
        self.assertTrue(self.testObj[1] not in self.exitToLoc)
        
    def testObj2InParent(self):
        "Test: object 2 in parent location"
        self.assertTrue(self.testObj[2] in self.parentLoc)
        
    def testObj2InChild2(self):
        "Test: object 2 in child location"
        self.assertTrue(self.testObj[2] in self.childLoc2)
        
    def testObj2NotInChild(self):
        "Test: object 2 in child location"
        self.assertTrue(self.testObj[2] not in self.childLoc)
        
    def testObj2NotInExit(self):
        "Test: object 2 in child location"
        self.assertTrue(self.testObj[2] not in self.exitToLoc)

    def testObj3InExit(self):
        "Test: object 3 in exit location"
        self.assertTrue(self.testObj[3] in self.exitToLoc)
        
    def testObj3NotInChild2(self):
        "Test: object 3 not in child location"
        self.assertTrue(self.testObj[3] not in self.childLoc)
        
    def testObj3NotInParent(self):
        "Test: object 3 not in parent location"
        self.assertTrue(self.testObj[3] not in self.parentLoc)
        
    def testEntryCurrentPopulation(self):
        "Test: entry location current population = zero"
        self.assertEqual(self.entryLoc.current_population, 0)
        
    def testParentCurrentPopulation(self):
        "Test: parent location current population = 3"
        self.assertEqual(self.parentLoc.current_population, 3)
        
    def testParentEntryPointCurrentPopulation(self):
        "Test: parent entry point location current population = 1"
        self.assertEqual(self.parentEntryPoint.current_population, 1)
        
    def testChildCurrentPopulation(self):
        "Test: child location current population = 1"
        self.assertEqual(self.childLoc.current_population, 1)
        
    def testChild2CurrentPopulation(self):
        "Test: child2 location current population = 1"
        self.assertEqual(self.childLoc2.current_population, 1)
        
    def testExitLocCurrentPopulation(self):
        "Test: exitToLoc location current population = 2"
        self.assertEqual(self.exitToLoc.current_population, 2)
        
    def testParentEntries(self):
        "Test: parent location entries = 5"
        self.assertEqual(self.parentLoc.entries, 5)
        
    def testParentEntryPointEntries(self):
        "Test: parent entry point location entries = 3"
        self.assertEqual(self.parentEntryPoint.entries, 3)
        
    def testChildEntries(self):
        "Test: child location entries = 4"
        self.assertEqual(self.childLoc.entries, 4)
        
    def testChild2Entries(self):
        "Test: child2 location entries = 1"
        self.assertEqual(self.childLoc2.entries, 1)
        
    def testExitToLocEntries(self):
        "Test: exit-to location entries = 2"
        self.assertEqual(self.exitToLoc.entries, 2)
        
    def testParentExits(self):
        "Test: parent location exits = 2"
        self.assertEqual(self.parentLoc.exits, 2)
        
    def testParentEntryPointExits(self):
        "Test: parent entry point location exits = 2"
        self.assertEqual(self.parentEntryPoint.exits, 2)
        
    def testChildExits(self):
        "Test: child location exits = 3"
        self.assertEqual(self.childLoc.exits, 3)
        
    def testChild2Exits(self):
        "Test: child2 location exits = 0"
        self.assertEqual(self.childLoc2.exits, 0)
        
    def testExitToLocExits(self):
        "Test: exit-to location exits = 0"
        self.assertEqual(self.exitToLoc.exits, 0)        
    
               
class SimLocationEntryPointTests1(unittest.TestCase):
    """
    Tests location entry point functionality in a multi-level location
    hierarchy.  Creates parent, child and grandchild objects, where the entry
    points for both the parent and child are the grandchild, and moves one object
    to the parent, and another to the child.
    """
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc
    
        self.entryLoc = TestLocation("EntryLoc", rootLoc)
        self.parentLoc = TestLocation("Parent", rootLoc, "Child.GC")
        self.childLoc = TestLocation("Child", self.parentLoc, "GC")
        self.grandchildLoc = TestLocation("GC", self.childLoc)
    
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [TestTransient(name, self.entryLoc) for name in names]        
         
        self.testObj[0].move_to(self.parentLoc)
        self.testObj[1].move_to(self.childLoc)
                       
    def testParentEntryPoint(self):
        "Test: parent location entry point is grandchild"
        self.assertIs(self.parentLoc.entry_point, self.grandchildLoc)
                       
    def testChildEntryPoint(self):
        "Test: child location entry point is grandchild"
        self.assertIs(self.childLoc.entry_point, self.grandchildLoc)
                       
    def testGrandChildEntryPoint(self):
        "Test: grandcchild location entry point is grandchild"
        self.assertIs(self.grandchildLoc.entry_point, self.grandchildLoc)
                       
    def testLocation0(self):
        "Test: object 0 located at grandchild"
        self.assertIs(self.testObj[0].location, self.grandchildLoc)
                       
    def testLocation1(self):
        "Test: object 1 located at grandchild"
        self.assertIs(self.testObj[1].location, self.grandchildLoc)
               
class SimLocationEntryPointTests2(unittest.TestCase):
    """
    Tests location entry point functionality in a multi-level location
    hierarchy. A slight variation on SimLocationEntryPointTests1; the parent
    object's entry point is the child (not the grandchild), but objects
    moving to parent should still go to the grandchild, since entry points
    are determined recursively.
    """
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc
    
        self.entryLoc = TestLocation("EntryLoc", rootLoc)
        self.parentLoc = TestLocation("Parent", rootLoc, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc, "GC")
        self.grandchildLoc = TestLocation("GC", self.childLoc)
    
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [TestTransient(name, self.entryLoc) for name in names]            
                
        self.testObj[0].move_to(self.parentLoc)
        self.testObj[1].move_to(self.childLoc)
                       
    def testParentEntryPoint(self):
        "Test: parent location entry point is grandchild"
        self.assertIs(self.parentLoc.entry_point, self.grandchildLoc)
                       
    def testChildEntryPoint(self):
        "Test: child location entry point is grandchild"
        self.assertIs(self.childLoc.entry_point, self.grandchildLoc)
                       
    def testGrandChildEntryPoint(self):
        "Test: grandcchild location entry point is grandchild"
        self.assertIs(self.grandchildLoc.entry_point, self.grandchildLoc)
                       
    def testLocation0(self):
        "Test: object 0 located at grandchild"
        self.assertIs(self.testObj[0].location, self.grandchildLoc)
                       
    def testLocation1(self):
        "Test: object 1 located at grandchild"
        self.assertIs(self.testObj[1].location, self.grandchildLoc)

        
def makeTestSuite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(SimEmptyLocationTests))
    suite.addTest(loader.loadTestsFromTestCase(SimParentLocationEntryTests))
    suite.addTest(loader.loadTestsFromTestCase(SimParentLocationExitTests))
    suite.addTest(loader.loadTestsFromTestCase(SimChildLocationEntryTests1))
    suite.addTest(loader.loadTestsFromTestCase(SimChildLocationEntryTests2))
    suite.addTest(loader.loadTestsFromTestCase(SimChildLocationExitTests1))
    suite.addTest(loader.loadTestsFromTestCase(SimStaticLocatableBaseTests))
    suite.addTest(loader.loadTestsFromTestCase(SimLocatableBaseTests))
    suite.addTest(loader.loadTestsFromTestCase(SimLocatableMoveTests))
    suite.addTest(loader.loadTestsFromTestCase(SimLocationEntryPointTests1))
    suite.addTest(loader.loadTestsFromTestCase(SimLocationEntryPointTests2))
    return suite            

        
if __name__ == '__main__':
    unittest.main()
 