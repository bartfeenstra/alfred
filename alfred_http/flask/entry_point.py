from alfred.app import App
from alfred_openapi.extension import OpenApiExtension
from alfred_rest.extension import RestExtension

alfred = App()
alfred.add_extension(OpenApiExtension)
alfred.add_extension(RestExtension)
app = alfred.service('http', 'flask')
