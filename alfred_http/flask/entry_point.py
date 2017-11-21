from flask_cors import CORS

from alfred_http.flask.app import FlaskApp
from alfred_openapi.extension import OpenApiExtension
from alfred_rest.extension import RestExtension

app = FlaskApp([OpenApiExtension, RestExtension])
CORS(app)
