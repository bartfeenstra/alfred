import operator
from typing import Callable
from unittest import TestCase

from contracts import contract

from alfred.functools import dispatch, classproperty


class SomeClass:
    def __init__(self):
        self.results = []

    @dispatch()
    def foo(self):
        self.results = []
        self.results.append('foo')

    @foo.register()
    def handler1(self):
        self.results.append('handler1')

    @foo.register()
    def handler2(self):
        self.results.append('handler2')


class SomeChildClass(SomeClass):
    @SomeClass.foo.register()
    def handler3(self):
        self.results.append('someChildHandler')


class SomeOtherChildClass(SomeClass):
    @SomeClass.foo.register()
    def handler4(self):
        self.results.append('someOtherChildHandler')


class InstanceMethodDispatchTest(TestCase):
    def testDispatch(self):
        # Test twice for idempotency.
        for _ in range(2):
            sut = SomeClass()
            result = sut.foo()
            self.assertEquals(result, None)
            self.assertEquals(sut.results, ['foo', 'handler1', 'handler2'])

    def testDispatchExecutesOwnedHandlersOnly(self):
        """
        Ensures method handlers on other classes are not invoked.
        :return:
        """
        sut = SomeChildClass()
        # Test for idempotency by running everything twice.
        for _ in range(2):
            result = sut.foo()
            self.assertEquals(result, None)
            self.assertEquals(
                sut.results,
                ['foo', 'handler1', 'handler2', 'someChildHandler'])


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
        # Test twice for idempotency.
        for _ in range(2):
            result = sut.foo()
            self.assertEquals(result,
                              ['fooResult', 'handler1Result',
                               'handler2Result'])

    def testDispatchExecutesOwnedHandlersOnly(self):
        """
        Ensures method handlers on other classes are not invoked.
        :return:
        """
        sut = SomeReducedChildClass()
        # Test twice for idempotency.
        for _ in range(2):
            result = sut.foo()
            self.assertEquals(result, [
                'fooResult', 'handler1Result', 'handler2Result',
                'someReducedChildHandler'])


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
        # Test twice for idempotency.
        for _ in range(2):
            result = foo()
            self.assertEquals(
                result, ['fooResult', 'handler1Result', 'handler2Result'])


class InstanceMethodFactoryDispatchTest(TestCase):
    class SomeClass:
        def __init__(self):
            self.results = []
            self._factoried = []

        @contract
        def _factory(self, handler: Callable):
            self._factoried.append(handler)
            return handler

        @dispatch(factory=_factory)
        def foo(self):
            self.results.append('foo')

        @foo.register(factory=True)
        def handler1(self):
            self.results.append('handler1')

    def testDispatch(self):
        sut = self.SomeClass()
        result = sut.foo()
        self.assertEquals(result, None)
        self.assertEquals(
            sut.results, ['foo', 'handler1'])
        self.assertEquals(sut._factoried, [self.SomeClass.handler1])


class ClasspropertyTest(TestCase):
    class FooMeta(type):
        _bar = 'Bar'

        @classproperty
        def bar(cls):
            return cls._bar

    class Foo(metaclass=FooMeta):
        pass

    def testGet(self):
        self.assertEquals(self.Foo.bar, 'Bar')

    def testSet(self):
        with self.assertRaises(AttributeError):
            self.Foo.bar = 'Not bar'

    def testDelete(self):
        with self.assertRaises(AttributeError):
            del self.Foo.bar
