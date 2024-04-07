from simprovise.core import *
import unittest

class TestLocation(SimLocation):
    def __init__(self, name, locationObj=None, animationObj=None, 
                 entryPointName=None):
        super().__init__(name, locationObj, animationObj, entryPointName)
        self.enterCount = 0
        self.exitCount = 0
        
    def onEnterImpl(self, enteringObj): 
        self.enterCount += 1
        
    def onExitImpl(self, exitingObj): 
        self.exitCount += 1
        
class TestTransient(SimTransientObject):
    def __init__(self, name, locationObj=None):
        super().__init__(locationObj)
        self.name = name
        
class MockNamedObject(object):
    def __init__(self, name):
        self.name = name
        
class MockAnimationObject(object):
    def __init__(self, name):
        self.name = name
        self.position = (100,100)
        self.simulationObject = None
    def addToAnimation(self, atTime):
        pass  
    
def reinitialize():
    SimDataCollector.reinitialize()
    SimClock.initialize()
    #SimAnimatableObject.setAnimating(False)
    



   
class SimEmptyLocationTests(unittest.TestCase):
    """
    Tests several variations of initial, empty SimLocations (one root, one child)
    """
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc
        
        # variation 1: parent/child where child is the entry point for the parent
        self.parentLoc = TestLocation("Parent", rootLoc, None, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        
        # variation 2: parent/child where parent specifies a non-existent child as 
        # entry point
        self.parentLoc2 = TestLocation("Parent2", rootLoc, None, "NonExistent")
        self.childLoc2 = TestLocation("Child2", self.parentLoc2)
        
        # variation 3: parent/child where the root does not specify an entry point
        self.parentLoc3 = TestLocation("Parent3", rootLoc)
        self.childLoc3 = TestLocation("Child3", self.parentLoc3)
        
    def testParentElementID1(self):
        "Test: parent elementID is specified parent name"
        self.assertEqual(self.parentLoc.element_id, "Parent")
        
    def testParentElementID2(self):
        "Test: parent elementID is same as parent elementName"
        self.assertEqual(self.parentLoc.element_id, self.parentLoc.elementName)
        
    def testChildElementID1(self):
        "Test: child elementID is specified <parent name>.<child name>"
        self.assertEqual(self.childLoc.element_id, "Parent.Child")
        
    def testChildElementID2(self):
        "Test: child elementID is NOT same as child elementName"
        self.assertNotEqual(self.childLoc.element_id, self.childLoc.elementName)

    def testParentParent(self):
        "Test: parent's parent is root" 
        self.assertIs(self.parentLoc.parent, self.root)

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
        self.assertTrue(self.parentLoc.isAncestorOf(self.childLoc))

    def testChildParent(self):
        "Test: parent location is parent of child" 
        self.assertIs(self.childLoc.parent, self.parentLoc)

    def testParentEntryPoint(self):
        "Test: parent location entry point is the child location" 
        self.assertIs(self.parentLoc.entry_point, self.childLoc)

    def testChildEntryPoint(self):
        "Test: child location entry point is itself" 
        self.assertIs(self.childLoc.entry_point, self.childLoc)

    def testParent2EntryPoint(self):
        "Test: parent location 2 entry point is None (as entry point name is invalid)" 
        self.assertIsNone(self.parentLoc2.entry_point)

    def testParent3EntryPoint(self):
        "Test: parent location 3 entry point is None (as entry point name is not set)" 
        self.assertIsNone(self.parentLoc3.entry_point)
         
    def testDuplicateAddRaises(self):
        "Test: re-adding the child location to the parent raises an error"
        self.assertRaises(SimError, lambda: self.parentLoc.addChild(self.childLoc))
        
    def testAddNotStaticChildRaises(self):
        "Test: addChild() with a non-static animatable object raises and error"
        testObj = TestTransient("test", self.parentLoc)
        self.assertRaises(SimError, lambda: self.parentLoc.addChild(testObj))
        
                       
class SimParentLocationEntryTests(unittest.TestCase):
    "Tests entry initial, empty SimLocations (one parent, one child)"
    def setUp(self):
        reinitialize()
        rootLoc = SimRootLocation()
        self.root = rootLoc

        self.parentLoc = TestLocation("Parent", rootLoc, None, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [MockNamedObject(name) for name in names]

    def testParentEnter1(self):
        "Test: add five entries to parent location, entries == 5"
        for i in range(5):
            self.parentLoc.on_enter(self.testObj[i])
        self.assertEqual(self.parentLoc.entries, 5)

    def testParentEnter2(self):
        "Test: add five entries to parent location, Test class entercount"
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
        
        self.parentLoc = TestLocation("Parent", rootLoc, None, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [MockNamedObject(name) for name in names]
        
        for i in range(5):
            self.parentLoc.on_enter(self.testObj[i])
        SimClock.advanceTo(SimTime(5))
        self.parentLoc.on_exit(self.testObj[0], self.exitToLoc)
        self.parentLoc.on_exit(self.testObj[1], self.exitToLoc)
        SimClock.advanceTo(SimTime(10))
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
    
        self.parentLoc = TestLocation("Parent", rootLoc, None, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [MockNamedObject(name) for name in names]
        
        self.parentLoc.on_enter(self.testObj[0])
        self.childLoc.on_enter(self.testObj[1])

    def testChildEntries(self):
        "Test: child location entries = 1"
        self.assertEqual(self.childLoc.entries, 1)

    def testChildEnterCount(self):
        "Test: child location enterCount = 1"
        self.assertEqual(self.childLoc.enterCount, 1)

    def testParentEntries(self):
        "Test: parent location entries = 2"
        self.assertEqual(self.parentLoc.entries, 2)

    def testChildEnterCount(self):
        "Test: parent location enterCount = 2"
        self.assertEqual(self.parentLoc.enterCount, 2)

    def testChildExits(self):
        "Test: child location exits = 1"
        self.assertEqual(self.childLoc.exits, 0)

    def testParentExits(self):
        "Test: parent location exits = 2"
        self.assertEqual(self.parentLoc.exits, 0)

    def testChildPopulation(self):
        "Test: child location currentPopulation = 1"
        self.assertEqual(self.childLoc.current_population, 1)

    def testParentPopulation(self):
        "Test: parent location currentPopulation = 1"
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
    
        self.parentLoc = TestLocation("Parent", rootLoc, None, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [MockNamedObject(name) for name in names]

        self.parentLoc.on_enter(self.testObj[0])
        self.childLoc.on_enter(self.testObj[1])
        SimClock.advanceTo(SimTime(2))
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
        "Test: parent location currentPopulation = 1"
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
    
        self.parentLoc = TestLocation("Parent", rootLoc, None, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc)
        self.childLoc2 = TestLocation("Child2", self.parentLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [MockNamedObject(name) for name in names]

        self.parentLoc.on_enter(self.testObj[0])
        self.childLoc.on_enter(self.testObj[1])
        self.childLoc.on_enter(self.testObj[2])
        self.childLoc.on_enter(self.testObj[3])
        SimClock.advanceTo(SimTime(2))
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
    
        self.parentLoc = TestLocation("Parent", rootLoc, None, "Child")
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
        self.childLoc = TestLocation("Child", self.parentLoc, None, "InvalidEntryPt")
        self.grandchildLoc = TestLocation("GrandChild", self.childLoc)
        self.entryLoc = TestLocation("EntryLoc", rootLoc)
        self.exitToLoc = TestLocation("ExitLoc", rootLoc)
        
        names = ["Bert", "Ernie", "Oscar", "Kermit", "Elmo"]
        self.testObj = [TestTransient(name, self.entryLoc) for name in names]
        self.staticTestObj = SimStaticObject("FixedTest", self.parentLoc)
               
    def testLocation(self):
        "Test: non-static test object location property"
        self.assertIs(self.testObj[0].location, self.entryLoc)
        
    def testIsStatic(self):
        "Test: non-static test object isStatic property"
        self.assertFalse(self.testObj[0].isStatic)
        
    def testEntryLocEntries(self):
        "Test: entryLoc entries is 5"
        self.assertEqual(self.entryLoc.entries, 5)

    def testEntryLocPopulation(self):
        "Test: entryLoc current population is 5"
        self.assertEqual(self.entryLoc.current_population, 5)
        
    def testParentEntries(self):
        "Test: parent entries is 0"
        self.assertEqual(self.parentLoc.entries, 0)
        
    def testParentPopulation(self):
        "Test: parent current population is 0"
        self.assertEqual(self.parentLoc.current_population, 0)
        
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
        self.parentLoc = TestLocation("Parent", rootLoc, None, "RootEntryPoint")
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
                
        SimClock.advanceTo(SimTime(2))
        
        self.testObj[0].move_to(self.exitToLoc)
        self.testObj[1].move_to(self.childLoc)
        self.testObj[2].move_to(self.childLoc2)
        self.testObj[3].move_to(self.exitToLoc)
        self.testObj[4].move_to(self.parentLoc)
                
        SimClock.advanceTo(SimTime(4))
                      
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
        
    def testParentMeanPopulation(self):
        "Test: parent location meanPopulation = 4"
        self.assertEqual(self.parentLoc.meanPopulation, 4)
        
    def testParentEntryPointMeanPopulation(self):
        "Test: parent entry point location meanPopulation = 1.5"
        self.assertEqual(self.parentEntryPoint.meanPopulation, 1.5)
        
    def testChildMeanPopulation(self):
        "Test: child location meanPopulation = 2"
        self.assertEqual(self.childLoc.meanPopulation, 2)
        
    def testChild2MeanPopulation(self):
        "Test: child2 location meanPopulation = 0.5"
        self.assertEqual(self.childLoc2.meanPopulation, 0.5)
        
    def testExitToLocMeanPopulation(self):
        "Test: exit-to location meanPopulation = 1"
        self.assertEqual(self.exitToLoc.meanPopulation, 1)
        
    def testParentMaxPopulation(self):
        "Test: parent location maxPopulation = 5"
        self.assertEqual(self.parentLoc.maxPopulation, 5)
        
    def testParentEntryPointMaxPopulation(self):
        "Test: parent entry point location maxPopulation = 2"
        self.assertEqual(self.parentEntryPoint.maxPopulation, 2)
        
    def testChildMaxPopulation(self):
        """
        Test: child location maxPopulation = 4 (obj1 moves in 
        at time 2 before others move out)
        """
        self.assertEqual(self.childLoc.maxPopulation, 4)
        
    def testChild2MaxPopulation(self):
        "Test: child2 location maxPopulation = 1"
        self.assertEqual(self.childLoc2.maxPopulation, 1)
        
    def testExitToLocMaxPopulation(self):
        "Test: exit-to location maxPopulation = 2"
        self.assertEqual(self.exitToLoc.maxPopulation, 2)

    def testParentMeanTimeInResidence(self):
        "Test: parent location meanTimeInResidence = 2"
        self.assertEqual(self.parentLoc.meanTimeInResidence, SimTime(2))
        
    def testParentEntryPointMeanTimeInResidence(self):
        "Test: parent entry point location meanTimeInResidence = 2"
        self.assertEqual(self.parentEntryPoint.meanTimeInResidence, SimTime(2))
        
    def testChildMeanTimeInResidence(self):
        "Test: child location meanTimeInResidence = 2"
        self.assertEqual(self.childLoc.meanTimeInResidence, SimTime(2))
        
    def testChild2MeanTimeInResidence(self):
        "Test: child2 location meanTimeInResidence is None"
        self.assertEqual(self.childLoc2.meanTimeInResidence, None)
        
    def testExitToLocMeanTimeInResidence(self):
        "Test: exit-to location meanTimeInResidence is None"
        self.assertEqual(self.exitToLoc.meanTimeInResidence, None)

               
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
        self.parentLoc = TestLocation("Parent", rootLoc, None, "Child.GC")
        self.childLoc = TestLocation("Child", self.parentLoc, None, "GC")
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
        self.parentLoc = TestLocation("Parent", rootLoc, None, "Child")
        self.childLoc = TestLocation("Child", self.parentLoc, None, "GC")
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
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SimEmptyLocationTests))
    suite.addTest(unittest.makeSuite(SimParentLocationEntryTests))
    suite.addTest(unittest.makeSuite(SimParentLocationExitTests))
    suite.addTest(unittest.makeSuite(SimChildLocationEntryTests1))
    suite.addTest(unittest.makeSuite(SimChildLocationEntryTests2))
    suite.addTest(unittest.makeSuite(SimChildLocationExitTests1))
    suite.addTest(unittest.makeSuite(SimStaticLocatableBaseTests))
    suite.addTest(unittest.makeSuite(SimLocatableBaseTests))
    suite.addTest(unittest.makeSuite(SimLocatableMoveTests))
    suite.addTest(unittest.makeSuite(SimLocationEntryPointTests1))
    suite.addTest(unittest.makeSuite(SimLocationEntryPointTests2))
    return suite            

        
if __name__ == '__main__':
    unittest.main()
 