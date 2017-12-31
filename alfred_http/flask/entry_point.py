from alfred.app import App
from alfred_device.extension import DeviceExtension
from alfred_openapi.extension import OpenApiExtension
from alfred_rest.extension import RestExtension
from alfred_rest.tests import RestTestExtension

alfred = App()
# @todo Make the extensions configurable.
alfred.add_extension(OpenApiExtension)
alfred.add_extension(RestExtension)
alfred.add_extension(RestTestExtension)
alfred.add_extension(DeviceExtension)
app = alfred.service('http', 'flask')
