import abc
from typing import Optional, Iterable, Dict

from contracts import with_metaclass, ContractsMeta, contract

from alfred import format_iter


class Device(with_metaclass(ContractsMeta)):
    @contract
    def __init__(self, device_id: str):
        self._id = device_id

    @property
    def id(self) -> str:
        return self._id


class DeviceNotFound(RuntimeError):
    def __init__(self, device_name: str,
                 available_devices: Optional[Dict] = None):
        available_devices = available_devices if available_devices is not None else {}
        if not available_devices:
            message = 'Could not find device "%s", because there are no devices.' % device_name
        else:
            message = 'Could not find device "%s". Did you mean one of the following?\n' % device_name + \
                      format_iter(available_devices.keys())
        super().__init__(message)


class DeviceRepository(with_metaclass(ContractsMeta)):
    @contract
    def get_device(self, device_id: str) -> Device:
        pass

    @contract
    def get_devices(self) -> Iterable:
        pass


class StaticDeviceRepository(DeviceRepository):
    def __init__(self):
        self._devices = {}

    @contract
    def add_device(self, device: Device):
        assert device.id not in self._devices
        self._devices[device.id] = device

    def get_device(self, device_id: str) -> Device:
        try:
            return self._devices[device_id]
        except KeyError:
            raise DeviceNotFound(device_id, self._devices)

    @contract
    def get_devices(self) -> Iterable:
        return list(self._devices.values())


class NestedDeviceRepository(DeviceRepository):
    def __init__(self):
        super().__init__()
        self._devices = None
        self._device_repositories = []

    @contract
    def add_devices(self, repositories: DeviceRepository):
        # Re-set the aggregated devices.
        self._devices = None
        self._device_repositories.append(repositories)

    def get_device(self, device_id: str):
        if self._devices is None:
            self._aggregate_devices()

        for device in self._devices:
            if device_id == device.name:
                return device
        raise DeviceNotFound(device_id, self._devices)

    def get_devices(self):
        if self._devices is None:
            self._aggregate_devices()
        return self._devices

    def _aggregate_devices(self):
        self._devices = []
        for repository in self._device_repositories:
            for device in repository.get_devices():
                self._devices.append(device)


class Powerable:
    def __init__(self):
        self._powered = None

    @property
    def powered(self) -> Optional[bool]:
        return self._powered

    def powerUp(self):
        self._powered = True

    def powerDown(self):
        self._powered = False


class RgbColor:
    @contract
    def __init__(self, red: int, green: int, blue: int):
        assert 0 <= red <= 255
        assert 0 <= green <= 255
        assert 0 <= blue <= 255
        self._red = red
        self._green = green
        self._blue = blue

    @property
    def red(self):
        return self._red

    @property
    def blue(self):
        return self._blue

    @property
    def green(self):
        return self._green


class RgbLight:
    def __init__(self):
        self._color = None

    @property
    @contract
    def color(self) -> RgbColor:
        return self._color

    @abc.abstractmethod
    @contract
    def changeColor(self, color: RgbColor):
        pass
