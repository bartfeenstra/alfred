from alfred.app import App
from alfred_openapi.extension import OpenApiExtension
from alfred_rest.extension import RestExtension

alfred = App()
# @todo Make the extensions configurable.
alfred.add_extension(OpenApiExtension)
alfred.add_extension(RestExtension)
app = alfred.service('http', 'flask')
