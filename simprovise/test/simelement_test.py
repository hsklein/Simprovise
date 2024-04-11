#===============================================================================
# MODULE simcounter_test
#
# Copyright (C) 2024 Howard Klein - All Rights Reserved
#
# TODO these tests are all to be removed - create new tests for
# SimProcess/EntityElement classes. Need SimModel tests as well, possibly
# in its own module
#
# Unit tests for SimCounter class
#===============================================================================
import os
from simprovise.core import *
import unittest

class MockEntity(SimEntity):
    ""

class MockLocation(SimLocation):
    ""


class SimElementDefinitionGraphicFileTests(unittest.TestCase):
    "Tests handling of SimElementDefinition graphicFile initialization"
    def testFileURL(self):
        "Test: SimElementDefinition with file URL"
        url = "file:///test.svg"
        elementDef = SimElementDefinition(SimLocation,
                                          animationClass=SimAnimatedStaticObject,
                                          graphicFile=url)
        self.assertEqual(elementDef.graphicFile, url)


   def testAbsoluteFile(self):
        "Test: SimElementDefinition with absolute graphic file"
        file = "empty.svg"
        thisdir = os.path.dirname(os.path.abspath(__file__))
        absfile = os.path.join(thisdir, file)
        url = SimUtility.abspathToFileURL(absfile)
        elementDef = SimElementDefinition(MockLocation,
                                          animationClass=SimAnimatedStaticObject,
                                          graphicFile=absfile)
        self.assertEqual(elementDef.graphicFile, url)


class SimElementDefinitionCoreLocationAttributeTests(unittest.TestCase):
    "Tests SimElementDefinition attributes for a SimLocation element, without merging"
    def setUp(self):
        self.url = "file:///test.svg"
        animcls = SimAnimatedStaticObject
        self.elementDef = SimElementDefinition(SimLocation,
                                               animationClass=animcls,
                                               graphicFile=self.url,
                                               svgElementID="location")

    def testElementClass(self):
        "Test: SimElementDefinition elementClass attribute"
        self.assertEqual(self.elementDef.elementClass, SimLocation)

    def testElementDefaultTypeName(self):
        "Test: SimElementDefinition typeName attribute default value (class name)"
        self.assertEqual(self.elementDef.typeName, "SimLocation")

    def testElementSetTypeName(self):
        "Test: SimElementDefinition typeName attribute when explicitly set"
        self.elementDef = SimElementDefinition(SimLocation,
                                               typeName="BaseLocation",
                                               animationClass=SimAnimatedStaticObject,
                                               graphicFile=self.url,
                                               svgElementID="location")
        self.assertEqual(self.elementDef.typeName, "BaseLocation")

    def testElementSvgElementID(self):
        "Test: SimElementDefinition svgElementID attribute"
        self.assertEqual(self.elementDef.svgElementID, "location")

    def testElementDefaultGraphicPrototype(self):
        "Test: SimElementDefinition graphicPrototypeName attribute default None"
        self.assertIsNone(self.elementDef.graphicPrototypeName)

    def testElementGraphicFile(self):
        "Test: SimElementDefinition graphicFile attribute"
        self.assertEqual(self.elementDef.graphicFile, self.url)

    def testElementIsCore(self):
        "Test: SimElementDefinition isCore attribute - true for SimLocation element"
        self.assertTrue(self.elementDef.isCore)

    def testElementIsStatic(self):
        "Test: SimElementDefinition isStatic attribute - true for SimLocation element"
        self.assertTrue(self.elementDef.isStatic)

    def testElementIsEntity(self):
        "Test: SimElementDefinition isEntity attribute - false for SimLocation element"
        self.assertFalse(self.elementDef.isEntity)


class SimElementDefinitionDerivedLocationAttributeTests(unittest.TestCase):
    "Tests SimElementDefinition attributes for a derived MockLocation element, without merging"
    def setUp(self):
        self.url = "file:///test.svg"
        animcls = SimAnimatedStaticObject
        self.elementDef = SimElementDefinition(MockLocation,
                                               animationClass=animcls,
                                               graphicFile=self.url,
                                               svgElementID="location")

    def testElementClass(self):
        "Test: SimElementDefinition elementClass attribute"
        self.assertEqual(self.elementDef.elementClass, MockLocation)

    def testElementDefaultTypeName(self):
        "Test: SimElementDefinition typeName attribute default value (class name)"
        self.assertEqual(self.elementDef.typeName, "MockLocation")

    def testElementSetTypeName(self):
        "Test: SimElementDefinition typeName attribute when explicitly set"
        self.elementDef = SimElementDefinition(MockLocation,
                                               typeName="DerivedLocation",
                                               animationClass=SimAnimatedStaticObject,
                                               graphicFile=self.url,
                                               svgElementID="location")
        self.assertEqual(self.elementDef.typeName, "DerivedLocation")

    def testElementSvgElementID(self):
        "Test: SimElementDefinition svgElementID attribute"
        self.assertEqual(self.elementDef.svgElementID, "location")

    def testElementDefaultGraphicPrototype(self):
        "Test: SimElementDefinition graphicPrototypeName attribute default None"
        self.assertIsNone(self.elementDef.graphicPrototypeName)

    def testElementGraphicFile(self):
        "Test: SimElementDefinition graphicFile attribute"
        self.assertEqual(self.elementDef.graphicFile, self.url)

    def testElementIsCore(self):
        "Test: SimElementDefinition isCore attribute - false for MockLocation element"
        self.assertFalse(self.elementDef.isCore)

    def testElementIsStatic(self):
        "Test: SimElementDefinition isStatic attribute - true for MockLocation element"
        self.assertTrue(self.elementDef.isStatic)

    def testElementIsEntity(self):
        "Test: SimElementDefinition isEntity attribute - false for MockLocation element"
        self.assertFalse(self.elementDef.isEntity)


class SimElementDefinitionCoreEntityAttributeTests(unittest.TestCase):
    "Tests SimElementDefinition attributes for a SimEntity element, without merging"
    def setUp(self):
        self.url = "file:///test.svg"
        animcls = SimAnimatedTransientObject
        self.elementDef = SimElementDefinition(SimEntity,
                                               animationClass=animcls,
                                               graphicPrototypeName="entity")

    def testElementClass(self):
        "Test: SimElementDefinition elementClass attribute"
        self.assertEqual(self.elementDef.elementClass, SimEntity)

    def testElementDefaultTypeName(self):
        "Test: SimElementDefinition typeName attribute default value (class name)"
        self.assertEqual(self.elementDef.typeName, "SimEntity")

    def testElementSetTypeName(self):
        "Test: SimElementDefinition typeName attribute when explicitly set"
        self.elementDef = SimElementDefinition(SimEntity,
                                               typeName="Entity",
                                               animationClass=SimAnimatedTransientObject,
                                               graphicPrototypeName="entity")
        self.assertEqual(self.elementDef.typeName, "Entity")

    def testElementGraphicPrototype(self):
        "Test: SimElementDefinition graphicPrototypeName attribute"
        self.assertIs(self.elementDef.graphicPrototypeName, "entity")

    def testElementGraphicFile(self):
        "Test: SimElementDefinition graphicFile attribute"
        self.assertIsNone(self.elementDef.graphicFile)

    def testElementIsCore(self):
        "Test: SimElementDefinition isCore attribute - true for SimEntity element"
        self.assertTrue(self.elementDef.isCore)

    def testElementIsStatic(self):
        "Test: SimElementDefinition isStatic attribute - false for SimEntity element"
        self.assertFalse(self.elementDef.isStatic)

    def testElementIsEntity(self):
        "Test: SimElementDefinition isEntity attribute - true for SimEntity element"
        self.assertTrue(self.elementDef.isEntity)


class SimElementDefinitionMergeTests(unittest.TestCase):
    "Tests SimElementDefinition attributes for a derived MockLocation element, without merging"
    def setUp(self):
        self.url = "file:///test.svg"
        animcls = SimAnimatedStaticObject
        self.baseElementDef = SimElementDefinition(SimLocation,
                                                   typeName='Base',
                                                   animationClass=animcls,
                                                   graphicFile=self.url,
                                                   svgElementID="location")
        self.mergedElementDef = SimElementDefinition(MockLocation,
                                                      graphicFile=self.url,
                                                      svgElementID="derivedlocation")
        self.mergedElementDef.merge(self.baseElementDef)
        self.mergedElementDef2 = SimElementDefinition(MockLocation)
        self.mergedElementDef2.merge(self.baseElementDef)

    def testMergedElementClass(self):
        "Test: Merged SimElementDefinition elementClass attribute"
        self.assertEqual(self.mergedElementDef.elementClass, MockLocation)

    def testMergedIsCore(self):
        "Test: Merged SimElementDefinition isCore attribute - still false for MockLocation element"
        self.assertFalse(self.mergedElementDef.isCore)

    def testMergedIsStatic(self):
        "Test: Merged SimElementDefinition isStatic attribute - still true for MockLocation element"
        self.assertTrue(self.mergedElementDef.isStatic)

    def testMergedIsEntity(self):
        "Test: Merged SimElementDefinition isEntity attribute - still false for MockLocation element"
        self.assertFalse(self.mergedElementDef.isEntity)

    def testMergedTypeName(self):
        "Test: Merged SimElementDefinition typeName attribute is NOT inherited"
        self.assertNotEqual(self.mergedElementDef.typeName, "Base")

    def testMergedAnimationClass(self):
        "Test: Merged SimElementDefinition animation class attribute is inherited when not defined in derived element"
        self.assertEqual(self.mergedElementDef.animationClass, SimAnimatedStaticObject)

    def testMergedGraphicFile1(self):
        "Test: Merged SimElementDefinition graphicFile attribute"
        self.assertEqual(self.mergedElementDef.graphicFile, self.url)

    def testMergedSvgElementID1(self):
        "Test: Merged SimElementDefinition svgElementID attribute"
        self.assertEqual(self.mergedElementDef.svgElementID, "derivedlocation")

    def testMergedGraphicFile2(self):
        "Test: Merged SimElementDefinition graphicFile attribute inherited when not defined"
        self.assertEqual(self.mergedElementDef2.graphicFile, self.url)

    def testMergedSvgElementID2(self):
        "Test: Merged SimElementDefinition svgElementID attribute inherited when not defined"
        self.assertEqual(self.mergedElementDef2.svgElementID, "location")

    def testMergedEntityElementDef(self):
        "Test: Merged Entity SimElementDefinition inherits graphicPrototypeName attribute"
        animcls = SimAnimatedTransientObject
        baseElementDef = SimElementDefinition(SimEntity,
                                              animationClass=animcls,
                                              graphicPrototypeName="entity")
        mergedElementDef = SimElementDefinition(MockEntity)
        mergedElementDef.merge(baseElementDef)
        self.assertEqual(mergedElementDef.graphicPrototypeName, "entity")


class SimElementRegistryCoreTests(unittest.TestCase):
    "Tests SimElementRegistry with just Core classes, registered via registerElementClass()"
    def setUp(self):
        self.url = "file:///test.svg"
        self.staticAnimCls = SimAnimatedStaticObject
        self.transientAnimCls = SimAnimatedTransientObject
        self.registry = SimElementRegistry(registerCorePackage=False)
        self.registry.registerElementClass(SimLocation, typeName="Location",
                                           animationClass=SimAnimatedStaticObject,
                                           graphicFile=self.url,
                                           svgElementID="location")
        self.registry.registerElementClass(SimQueue, typeName="Queue",
                                           animationClass=SimAnimatedQueue,
                                           graphicFile=self.url,
                                           svgElementID="queue")
        self.registry.registerElementClass(SimEntity, typeName="Entity",
                                           animationClass=SimAnimatedEntity,
                                           graphicPrototypeName="Entity")

    def testRegisteredNames(self):
        "Test: registry.registeredNames() returns sequence of qualified names"
        expectedNames = ('simprovise.core.SimLocation',
                         'simprovise.core.SimQueue',
                         'simprovise.core.SimEntity')
        self.assertCountEqual(self.registry.registeredNames(), expectedNames)

    def testRegisteredPackages(self):
        "Test: registry.registeredPackages() returns Core package when core classes are registered"
        expectedNames = ('simprovise.core',)
        self.assertCountEqual(self.registry.registeredPackages(), expectedNames)

    def testGetClassNamesAll(self):
        "Test: registry.getClassNames() with no arguments returns same value as registeredNames()"
        self.assertCountEqual(self.registry.getClassNames(),
                              self.registry.registeredNames())

    def testGetClassNamesLocations(self):
        "Test: registry.getClassNames() filtering for locations returns SimLocation and SimQueue"
        expectedNames = ('simprovise.core.SimLocation',
                         'simprovise.core.SimQueue')
        self.assertCountEqual(self.registry.getClassNames(coretype=SimLocation),
                              expectedNames)

    def testGetClassNamesEntities(self):
        "Test: registry.getClassNames() filtering for entities returns SimEntity"
        expectedNames = ('simprovise.core.SimEntity',)
        self.assertCountEqual(self.registry.getClassNames(coretype=SimEntity),
                              expectedNames)

    def testGetStaticTypeDefDataEntity(self):
        "Test: registry.getStaticTypeDefData() returns None for a transient object"
        self.assertIsNone(self.registry.getStaticTypeDefData("simprovise.core.SimEntity"))

    def testGetStaticTypeDefDataQueue(self):
        "Test: registry.getStaticTypeDefData() for a SimQueue"
        expectedSTDD = SimStaticTypeDefData("Queue", "simprovise.core.SimQueue",
                                            {}, "Simalytix.Animation.SimAnimatedQueue",
                                            {}, [], self.url, "queue")
        staticTTD = self.registry.getStaticTypeDefData("simprovise.core.SimQueue")
        self.assertEqual(staticTTD, expectedSTDD)

    def testEntityAnimationSpecStatic(self):
        "Test: registry.getEntityAnimationSpec() for non-entity returns None"
        classname = "simprovise.core.SimQueue"
        self.assertIsNone(self.registry.getEntityAnimationSpec(classname))

    def testEntityAnimationSpec(self):
        "Test: registry.getEntityAnimationSpec() for SimEntity"
        classname = "simprovise.core.SimEntity"
        expectedspec = [classname, "Simalytix.Animation.SimAnimatedEntity",
                        "Entity", None, {}]
        self.assertEqual(self.registry.getEntityAnimationSpec(classname),
                         expectedspec)


class SimElementRegistryExtendedTests(unittest.TestCase):
    "Tests SimElementRegistry with Core and Mock classes, registered via registerElementClass()"
    def setUp(self):
        self.url = "file:///test.svg"
        self.pngurl = "file:///mockentity.png"
        self.staticAnimCls = SimAnimatedStaticObject
        self.transientAnimCls = SimAnimatedTransientObject
        self.registry = SimElementRegistry(registerCorePackage=False)
        self.registry.registerElementClass(SimLocation, typeName="Location",
                                           animationClass=SimAnimatedStaticObject,
                                           graphicFile=self.url,
                                           svgElementID="Location")
        self.registry.registerElementClass(MockLocation, typeName="Mocklocation")
        self.registry.registerElementClass(SimEntity, typeName="Entity",
                                           animationClass=SimAnimatedEntity,
                                           graphicPrototypeName="Entity")
        self.registry.registerElementClass(MockEntity, typeName="Entity",
                                           graphicFile=self.pngurl)

    def testRegisteredNames(self):
        "Test: registry.registeredNames() returns sequence of qualified names"
        expectedNames = ('simprovise.core.SimLocation',
                         'simprovise.core.SimEntity',
                         __name__ + '.MockEntity',
                         __name__ + '.MockLocation')
        self.assertCountEqual(self.registry.registeredNames(), expectedNames)

    def testGetClassNamesAll(self):
        "Test: registry.getClassNames() with no arguments returns same value as registeredNames()"
        self.assertCountEqual(self.registry.getClassNames(),
                              self.registry.registeredNames())

    def testGetClassNamesLocations(self):
        "Test: registry.getClassNames() filtering for locations returns SimLocation and MockLocation"
        expectedNames = ('simprovise.core.SimLocation', __name__ + '.MockLocation')
        self.assertCountEqual(self.registry.getClassNames(coretype=SimLocation),
                              expectedNames)

    def testGetClassNamesEntities(self):
        "Test: registry.getClassNames() filtering for entities returns SimEntity and MockEntity"
        expectedNames = ('simprovise.core.SimEntity', __name__ + '.MockEntity')
        self.assertCountEqual(self.registry.getClassNames(coretype=SimEntity),
                              expectedNames)

    def testGetCoreClassNames(self):
        "Test: registry.getClassNames() filtering for core module returns core classes"
        expectedNames = ('simprovise.core.SimLocation', 'simprovise.core.SimEntity')
        self.assertCountEqual(self.registry.getClassNames(module='simprovise.core'),
                              expectedNames)

    def testGetCoreWithPeriodClassNames(self):
        "Test: registry.getClassNames() filtering for core module including period at end returns core classes"
        expectedNames = ('simprovise.core.SimLocation', 'simprovise.core.SimEntity')
        self.assertCountEqual(self.registry.getClassNames(module='simprovise.core.'),
                              expectedNames)

    def testGetMockClassNames(self):
        "Test: registry.getClassNames() filtering for __main__ module returns Mock classes"
        expectedNames = ( __name__ + '.MockLocation', __name__ + '.MockEntity')
        self.assertCountEqual(self.registry.getClassNames(module=__name__),
                              expectedNames)

    def testGetBadMockClassNames(self):
        "Test: registry.getClassNames() filtering for partial mock module name returns nothing"
        self.assertCountEqual(self.registry.getClassNames(module=__name__[0:3]), ())

    def testGetBadCoretypeClassNames(self):
        "Test: registry.getClassNames() filtering for invalid coretype raises"
        expr = lambda: self.registry.getClassNames(coretype=MockEntity)
        self.assertRaises(SimError, expr)


class SimElementRegistryRegisterModuleTests(unittest.TestCase):
    "Tests SimElementRegistry with a module registered via registerModule"
    def setUp(self):
        self.registry = SimElementRegistry()
        self.moduleName = "Simalytix.Test.simelement_testpackage.testmodule"
        self.registry.registerModule(self.moduleName)

    def testRegisteredPackages(self):
        "Test: registry.registeredPackages() returns the Core and registered module name"
        expectedNames = ('simprovise.core', self.moduleName)
        self.assertCountEqual(self.registry.registeredPackages(), expectedNames)

    def testRegisteredNames(self):
        "Test: registry.registeredNames() returns expected sequence of qualified names"
        expectedNames = ('simprovise.core.SimEntitySource',
                         'simprovise.core.SimEntitySink',
                         'simprovise.core.SimLocation',
                         'simprovise.core.SimSimpleResource',
                         'simprovise.core.SimQueue',
                         'simprovise.core.SimEntity',
                         self.moduleName + '.TestProcess',
                         self.moduleName + '.TestResource',
                         self.moduleName + '.TestPersonEntity',
                         self.moduleName + '.TestLocation',
                        )
        self.assertCountEqual(self.registry.registeredNames(), expectedNames)

    def testGetCoreClassNames(self):
        "Test: registry.getClassNames() returns expected sequence of core class names"
        expectedNames = ('simprovise.core.SimEntitySource',
                         'simprovise.core.SimEntitySink',
                         'simprovise.core.SimLocation',
                         'simprovise.core.SimSimpleResource',
                         'simprovise.core.SimQueue',
                         'simprovise.core.SimEntity'
                        )
        self.assertCountEqual(self.registry.getClassNames(module='simprovise.core'),
                              expectedNames)

    def testGetTestClassNames(self):
        "Test: registry.getClassNames() returns expected sequence of test module class names"
        expectedNames = (self.moduleName + '.TestProcess',
                         self.moduleName + '.TestResource',
                         self.moduleName + '.TestPersonEntity',
                         self.moduleName + '.TestLocation',
                        )
        self.assertCountEqual(self.registry.getClassNames(module=self.moduleName),
                              expectedNames)


class SimElementRegistryRegisterScriptTests(unittest.TestCase):
    "Tests SimElementRegistry with a script (with no simelement imports) registered via registerClassesInScript"
    def setUp(self):
        self.registry = SimElementRegistry()
        self.scriptModuleName = "SimMain"
        self.scriptName = "testscript.py"
        thisdir = os.path.dirname(os.path.abspath(__file__))
        scriptpath = os.path.join(thisdir, "simelement_testpackage",
                                  self.scriptName)
        self.registry.registerClassesInScript(scriptpath)
        print(self.registry.registeredPackages())

    def testRegisteredPackages(self):
        "Test: registry.registeredPackages() returns the Core and registered module name"
        expectedNames = ('simprovise.core', self.scriptModuleName)
        self.assertCountEqual(self.registry.registeredPackages(), expectedNames)

    def testRegisteredNames(self):
        "Test: registry.registeredNames() returns expected sequence of qualified names"
        expectedNames = ('simprovise.core.SimEntitySource',
                         'simprovise.core.SimEntitySink',
                         'simprovise.core.SimLocation',
                         'simprovise.core.SimSimpleResource',
                         'simprovise.core.SimQueue',
                         'simprovise.core.SimEntity',
                         self.scriptModuleName + '.TestProcess',
                         self.scriptModuleName + '.TestResource',
                         self.scriptModuleName + '.TestPersonEntity',
                         self.scriptModuleName + '.TestLocation',
                        )
        self.assertCountEqual(self.registry.registeredNames(), expectedNames)

    def testGetCoreClassNames(self):
        "Test: registry.getClassNames() returns expected sequence of core class names"
        expectedNames = ('simprovise.core.SimEntitySource',
                         'simprovise.core.SimEntitySink',
                         'simprovise.core.SimLocation',
                         'simprovise.core.SimSimpleResource',
                         'simprovise.core.SimQueue',
                         'simprovise.core.SimEntity'
                        )
        self.assertCountEqual(self.registry.getClassNames(module='simprovise.core'),
                              expectedNames)

    def testGetTestClassNames(self):
        "Test: registry.getClassNames() returns expected sequence of test module class names"
        expectedNames = (self.scriptModuleName + '.TestProcess',
                         self.scriptModuleName + '.TestResource',
                         self.scriptModuleName + '.TestPersonEntity',
                         self.scriptModuleName + '.TestLocation',
                        )
        self.assertCountEqual(self.registry.getClassNames(module=self.scriptModuleName),
                              expectedNames)


def makeTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SimElementDefinitionGraphicFileTests))
    suite.addTest(unittest.makeSuite(SimElementDefinitionCoreLocationAttributeTests))
    suite.addTest(unittest.makeSuite(SimElementDefinitionDerivedLocationAttributeTests))
    suite.addTest(unittest.makeSuite(SimElementDefinitionCoreEntityAttributeTests))
    suite.addTest(unittest.makeSuite(SimElementDefinitionMergeTests))
    suite.addTest(unittest.makeSuite(SimElementRegistryCoreTests))
    suite.addTest(unittest.makeSuite(SimElementRegistryExtendedTests))
    suite.addTest(unittest.makeSuite(SimElementRegistryRegisterModuleTests))
    suite.addTest(unittest.makeSuite(SimElementRegistryRegisterScriptTests))
    return suite

if __name__ == '__main__':
    unittest.main(verbosity=1)