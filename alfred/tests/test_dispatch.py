import operator
from unittest import TestCase

from alfred.dispatch import dispatch


class InstanceMethodDispatchTest(TestCase):
    class SomeClass:
        def __init__(self):
            self._results = []

        @dispatch()
        def foo(self):
            self._results.append('foo')
            return 'fooResult'

        @foo.register()
        def handler1(self):
            self._results.append('handler1')
            return 'handler1Result'

        @foo.register()
        def handler2(self):
            self._results.append('handler2')
            return 'handler2Result'

    def testDispatch(self):
        sut = self.SomeClass()
        result = sut.foo()
        self.assertEquals(result, None)
        self.assertEquals(sut._results, ['foo', 'handler1', 'handler2'])


class ReducedInstanceMethodDispatchTest(TestCase):
    class SomeClass:
        @dispatch(reducer=operator.concat)
        def foo(self):
            return ['fooResult']

        @foo.register()
        def handler1(self):
            return ['handler1Result']

        @foo.register()
        def handler2(self):
            return ['handler2Result']

    def testDispatch(self):
        sut = self.SomeClass()
        result = sut.foo()
        self.assertEquals(
            result, ['fooResult', 'handler1Result', 'handler2Result'])


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
