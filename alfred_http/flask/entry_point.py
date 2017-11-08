from flask_cors import CORS

from alfred_http.flask.app import FlaskApp
from alfred_openapi.extension import OpenApiExtension

app = FlaskApp([OpenApiExtension])
CORS(app)
