import json
from unittest.mock import patch

from alfred_maison.tests import MaisonTestCase


class GetStageLightEndpointTest(MaisonTestCase):
    def testEndpointShouldReturnResource(self):
        resource_id = 'stage_1'
        response = self.request('device', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(200, response)
        data = json.loads(response.body.content)
        self.assertEqual(data['id'], resource_id)


class AlterStageLightEndpointTest(MaisonTestCase):
    @patch('subprocess.call')
    def testEndpointShouldAlterResource(self, mock_call):
        resource_id = 'stage_1'
        powered = True
        color = '#123456'
        luminosity = 0.73
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
        data = json.loads(response.body.content)
        self.assertEqual(data['id'], resource_id)
        self.assertEqual(data['powered'], powered)
        self.assertEqual(data['color'], color)
        mock_call.assert_any_call(['ola_set_dmx', '-u', '1', '-d', '18,52,86'])
        self.assertAlmostEqual(data['luminosity'], luminosity, places=0)
        mock_call.assert_any_call(
            ['ola_set_dmx', '-u', '1', '-d', '18,52,86,186'])

        # Confirm we can retrieve the resource we just altered.
        response = self.request('device', parameters={
            'id': resource_id,
        })
        self.assertResponseStatus(200, response)
        data = json.loads(response.body.content)
        self.assertEqual(data['id'], resource_id)
        self.assertEqual(data['powered'], powered)
        self.assertEqual(data['color'], color)
        self.assertAlmostEqual(data['luminosity'], luminosity, places=0)
