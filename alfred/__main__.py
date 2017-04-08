from flask import Flask
from flask import request
from flask import Response
from alfred.graphql import Schema
import json
from flask_cors import cross_origin

app = Flask(__name__)


@app.route('/', methods=['POST'])
@cross_origin()
def graphql():
    # Parse and validate the request.
    try:
        request_data = json.loads(request.get_data())
    except ValueError:
        return Response(status=400, response='The request body contains no (valid) JSON.')
    if type(request_data) is not dict:
        return Response(status=400, response='The request body is no object.')
    if 'query' not in request_data:
        return Response(status=400, response='The request body does not contain the `query` property.')
    if type(request_data['query']) is not str and type(request_data['query']) is not unicode:
        return Response(status=400, response='The `query` property is no GraphQL query string.')
    query = request_data['query']
    if 'variables' in request_data:
        if type(request_data['variables']) is not dict:
            return Response(status=400, response='The `variables` property is no object.')
        variables = request_data['variables']
    else:
        variables = None

    result = Schema().execute(query, variable_values=variables)
    errors = map(lambda error: {
        'message': str(error)
    }, result.errors)
    response_data = json.dumps({
        'data': result.data,
        'errors': errors,
    })
    return Response(response=response_data, mimetype='application/json')

if __name__ == '__main__':
    app.run()