from alfred.app import App
from alfred_openapi.extension import OpenApiExtension
from alfred_rest.extension import RestExtension
from alfred_rest.tests.extension import RestTestExtension

alfred = App()
# @todo Make the extensions configurable.
alfred.add_extension(OpenApiExtension)
alfred.add_extension(RestExtension)
alfred.add_extension(RestTestExtension)
app = alfred.service('http', 'flask')
