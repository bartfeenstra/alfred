import json

from jsonschema import validate

from alfred_http import base64_encodes
from alfred_json import json_schema
from alfred_rest.tests import RestTestCase


class JsonSchemaEndpointTest(RestTestCase):
    def testEndpointShouldReturnSchema(self):
        content_type = 'application/schema+json'
        response = self.request('schema', headers={
            'Accept': content_type,
        })
        self.assertResponseStatus(200, response)
        self.assertResponseContentType(content_type, response)
        actual_schema = response.json()
        validate(actual_schema, json_schema())
        expected_response_schema = {
            '$ref': 'http://127.0.0.1:5000/about/json/external-schema/aHR0cDovL2pzb24tc2NoZW1hLm9yZy9kcmFmdC0wNC9zY2hlbWE%3D'
        }
        self.assertIn('definitions', actual_schema)
        self.assertIn('response', actual_schema['definitions'])
        self.assertIn('schema', actual_schema['definitions']['response'])
        self.assertEquals(actual_schema['definitions']['response']
                          ['schema'], expected_response_schema)


class ExternalJsonSchemaEndpointTest(RestTestCase):
    def setUp(self):
        super().setUp()

    def testEndpointShouldReturnSchema(self):
        external_schema_url = 'http://json-schema.org/draft-04/schema#'

        content_type = 'application/schema+json'
        response = self.request('external-schema', parameters={
            'id': base64_encodes(external_schema_url),
        }, headers={
            'Accept': content_type,
        })
        self.assertResponseStatus(200, response)
        self.assertResponseContentType(content_type, response)
        actual_schema = response.json()
        expected_schema = self._app.service(
            'json', 'schema_rewriter').rewrite(json_schema())
        self.assertEquals(actual_schema, expected_schema)

    def testEndpointShouldHandleMissingSchema(self):
        external_schema_url = 'http://example.com/schema#'

        content_type = 'application/schema+json'
        response = self.request('external-schema', parameters={
            'id': base64_encodes(external_schema_url),
        }, headers={
            'Accept': content_type,
        })
        self.assertResponseStatus(404, response)
        self.assertResponseContentType('', response)


class GetResourceEndpointTest(RestTestCase):
    def testEndpointShouldReturnResource(self):
        resource_id = 'foo'
        response = self.request('rest-test', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(200, response)
        data = response.json()
        self.assertEqual(data['id'], resource_id)

    def testEndpointShouldNotFoundForUnknownResource(self):
        resource_id = 'BAZ'
        response = self.request('rest-test', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(404, response)


class GetResourcesEndpointTest(RestTestCase):
    def testEndpointShouldReturnResources(self):
        expected_ids = ['foo', 'Bar']
        response = self.request('rest-tests')
        self.assertResponseStatus(200, response)
        data = response.json()
        actual_ids = []
        for resource_data in data:
            actual_ids.append(resource_data['id'])
        self.assertCountEqual(actual_ids, expected_ids)


class AddResourceEndpointTest(RestTestCase):
    def testEndpointShouldAddResource(self):
        resource_id = 'qux'
        resource_label = 'QuX'
        body = json.dumps({
            'id': resource_id,
            'label': resource_label,
        })
        response = self.request('rest-test-add', body=body, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        self.assertResponseStatus(200, response)
        data = response.json()
        self.assertEqual(data['id'], resource_id)
        self.assertEqual(data['label'], resource_label)

        # Confirm we can retrieve the resource we just added.
        response = self.request('rest-test', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(200, response)
        data = response.json()
        self.assertEqual(data['id'], resource_id)
        self.assertEqual(data['label'], resource_label)

    def testEndpointShouldBadRequestForInvalidResource(self):
        body = json.dumps({})
        response = self.request('rest-test-add', body=body, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        self.assertResponseStatus(400, response)

    def testEndpointShouldUnsupportedMediaTypeForInvalidContentType(self):
        resource_id = 'qux'
        resource_label = 'QuX'
        body = '%s (%s)' % (resource_label, resource_id)
        response = self.request('rest-test-add', body=body, headers={
            'Content-Type': 'text/plain',
            'Accept': 'application/json',
        })
        self.assertResponseStatus(415, response)

    def testEndpointShouldNotAcceptableForInvalidAccept(self):
        resource_id = 'qux'
        resource_label = 'QuX'
        body = json.dumps({
            'id': resource_id,
            'label': resource_label,
        })
        response = self.request('rest-test-add', body=body, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/octet-stream',
        })
        self.assertResponseStatus(406, response)


class ReplaceResourceEndpointTest(RestTestCase):
    def testEndpointShouldReplaceResource(self):
        resource_id = 'foo'
        resource_label = 'QuX'
        body = json.dumps({
            'id': resource_id,
            'label': resource_label,
        })
        response = self.request('rest-test-replace', parameters={
            'id': resource_id,
        }, body=body, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        self.assertResponseStatus(200, response)
        data = response.json()
        self.assertEqual(data['id'], resource_id)
        self.assertEqual(data['label'], resource_label)

        # Confirm we can retrieve the resource we just replaced.
        response = self.request('rest-test', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(200, response)
        data = response.json()
        self.assertEqual(data['id'], resource_id)
        self.assertEqual(data['label'], resource_label)

    def testEndpointShouldBadRequestForInvalidResource(self):
        resource_id = 'foo'
        body = json.dumps({})
        response = self.request('rest-test-replace', parameters={
            'id': resource_id,
        }, body=body, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        self.assertResponseStatus(400, response)

    def testEndpointShouldUnsupportedMediaTypeForInvalidContentType(self):
        resource_id = 'foo'
        resource_label = 'QuX'
        body = '%s (%s)' % (resource_label, resource_id)
        response = self.request('rest-test-replace', parameters={
            'id': resource_id,
        }, body=body, headers={
            'Content-Type': 'text/plain',
            'Accept': 'application/json',
        })
        self.assertResponseStatus(415, response)

    def testEndpointShouldNotAcceptableForInvalidAccept(self):
        resource_id = 'foo'
        resource_label = 'QuX'
        body = json.dumps({
            'id': resource_id,
            'label': resource_label,
        })
        response = self.request('rest-test-replace', parameters={
            'id': resource_id,
        }, body=body, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/octet-stream',
        })
        self.assertResponseStatus(406, response)

    def testEndpointShouldNotFoundForUnknownResource(self):
        resource_id = 'BAZ'
        resource_label = 'QuX'
        body = json.dumps({
            'id': resource_id,
            'label': resource_label,
        })
        response = self.request('rest-test-replace', parameters={
            'id': resource_id,
        }, body=body, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        self.assertResponseStatus(404, response)


class DeleteResourceEndpointTest(RestTestCase):
    def testEndpointShouldDeleteResource(self):
        resource_id = 'foo'
        response = self.request('rest-test-delete', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(200, response)

        # Confirm we can no longer retrieve the resource we just deleted.
        response = self.request('rest-test', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(404, response)

        # Confirm the deletion is idempotent.
        resource_id = 'foo'
        response = self.request('rest-test-delete', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(200, response)

    def testEndpointShouldOKForUnknownResource(self):
        resource_id = 'BAZ'
        response = self.request('rest-test-delete', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(200, response)
