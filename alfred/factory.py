from contracts import contract

from alfred import qualname
from alfred.app import AppAwareFactory, App


class ClassInstantiationError(BaseException):
    pass


class ClassFactory:
    @contract
    def __init__(self, app: App):
        self._app = app

    def new(self, cls: type):
        requirements = []
        if issubclass(cls, AppAwareFactory):
            return cls.new_from_app(self._app)
        else:
            requirements.append('%s must extend %s' % (
                qualname(cls), qualname(AppAwareFactory)))

        try:
            return cls()
        except Exception as e:
            requirements.append(
                '%s.__init__() must take no required arguments (%s)' % (
                    qualname(cls), e))

        message = 'Could not instantiate %s. Fix this by meeting one of the following requirements: %s.' % (  # noqa: E501
            qualname(cls),
            ' OR '.join(requirements),
        )
        raise ClassInstantiationError(message)
