import operator
from unittest import TestCase

from alfred.dispatch import dispatch


class SomeClass:
    def __init__(self):
        self._results = []

    @dispatch()
    def foo(self):
        self._results.append('foo')

    @foo.register()
    def handler1(self):
        self._results.append('handler1')

    @foo.register()
    def handler2(self):
        self._results.append('handler2')


class SomeChildClass(SomeClass):
    @SomeClass.foo.register()
    def handler3(self):
        self._results.append('someChildHandler')


class SomeOtherChildClass(SomeClass):
    @SomeClass.foo.register()
    def handler4(self):
        self._results.append('someOtherChildHandler')


class InstanceMethodDispatchTest(TestCase):
    def testDispatch(self):
        sut = SomeClass()
        result = sut.foo()
        self.assertEquals(result, None)
        self.assertEquals(sut._results, ['foo', 'handler1', 'handler2'])

    def testDispatchExecutesOwnedHandlersOnly(self):
        """
        Ensures method handlers on other classes are not invoked.
        :return:
        """
        sut = SomeChildClass()
        result = sut.foo()
        self.assertEquals(result, None)
        self.assertEquals(
            sut._results, ['foo', 'handler1', 'handler2', 'someChildHandler'])


class SomeReducedClass:
    @dispatch(reducer=operator.concat)
    def foo(self):
        return ['fooResult']

    @foo.register()
    def handler1(self):
        return ['handler1Result']

    @foo.register()
    def handler2(self):
        return ['handler2Result']


class SomeReducedChildClass(SomeReducedClass):
    @SomeReducedClass.foo.register()
    def handler3(self):
        return ['someReducedChildHandler']


class SomeReducedOtherChildClass(SomeReducedClass):
    @SomeReducedClass.foo.register()
    def handler4(self):
        return ['someReducedOtherChildHandler']


class ReducedInstanceMethodDispatchTest(TestCase):
    def testDispatch(self):
        sut = SomeReducedClass()
        result = sut.foo()
        self.assertEquals(result,
                          ['fooResult', 'handler1Result', 'handler2Result'])

    def testDispatchExecutesOwnedHandlersOnly(self):
        """
        Ensures method handlers on other classes are not invoked.
        :return:
        """
        sut = SomeReducedChildClass()
        result = sut.foo()
        self.assertEquals(result, [
                          'fooResult', 'handler1Result', 'handler2Result', 'someReducedChildHandler'])


@dispatch(reducer=operator.concat)
def foo():
    return ['fooResult']


@foo.register()
def handler1():
    return ['handler1Result']


@foo.register()
def handler2():
    return ['handler2Result']


class ReducedFunctionDispatchTest(TestCase):
    def testDispatch(self):
        result = foo()
        self.assertEquals(
            result, ['fooResult', 'handler1Result', 'handler2Result'])
