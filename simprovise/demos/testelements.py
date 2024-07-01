from simprovise.core import SimSimpleResource
from simprovise.configuration import simelement

print("running testelements")

def testdecorator(cls):
    print("testdecorator", cls.__name__)
    return cls

class testdecorator2(object):
    def __init__(self, name):
        print("testdecorator 2", name)

    def __call__(self, cls):
        return cls

class TestClass(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b


@simelement()
class TestResource(SimSimpleResource):
    """
    """

@testdecorator2("Test 2")
class MyTest(TestClass):
    """
    """

