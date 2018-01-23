import json

from alfred_maison.tests import MaisonTestCase


class GetStageLightEndpointTest(MaisonTestCase):
    def testEndpointShouldReturnResource(self):
        resource_id = 'stage_1'
        response = self.request('device', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(200, response)
        data = response.json()
        self.assertEqual(data['id'], resource_id)


class AlterStageLightEndpointTest(MaisonTestCase):
    def testEndpointShouldAlterResource(self):
        resource_id = 'stage_1'
        powered = True
        color = '#123456'
        luminosity = 73
        body = json.dumps([
            {
                'op': 'replace',
                'path': '/powered',
                'value': powered,
            },
            {
                'op': 'replace',
                'path': '/color',
                'value': color,
            },
            {
                'op': 'replace',
                'path': '/luminosity',
                'value': luminosity,
            },
        ])
        response = self.request('device-alter', parameters={
            'id': resource_id,
        }, body=body, headers={
            'Content-Type': 'application/json-patch+json',
            'Accept': 'application/json',
        })
        self.assertResponseStatus(200, response)
        data = response.json()
        self.assertEqual(data['id'], resource_id)
        self.assertEqual(data['powered'], powered)
        self.assertEqual(data['color'], color)
        self.assertEqual(data['luminosity'], luminosity)

        # Confirm we can retrieve the resource we just altered.
        response = self.request('device', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(200, response)
        data = response.json()
        self.assertEqual(data['id'], resource_id)
        self.assertEqual(data['powered'], powered)
        self.assertEqual(data['color'], color)
        self.assertEqual(data['luminosity'], luminosity)
