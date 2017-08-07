import argparse
import json

import os
from alfred_speech.core import Environment, Listener, Configuration
from jsonschema import validate, RefResolver


def run():
    # Set up the CLI.
    parser = argparse.ArgumentParser(description='Runs Alfred.')
    parser.add_argument('-c', '--configuration', nargs=1, required=True,
                        help='The Alfred '
                             'configuration file.',
                        dest='configuration_file_path')
    parser.add_argument('-i', '--input', nargs='?', help='The ID of the '
                                                         'input to use. '
                                                         'Overrides whatever is in the configuration file.',  # noqa: E501
                        dest='input_id_override')
    parser.add_argument('-o', '--output', nargs='?', help='The ID of the output to use Overrides whatever is in the configuration file.',  # noqa: E501
                        dest='output_id_override')

    # Read the configuration file.
    configuration_file_path = parser.parse_args(

    ).configuration_file_path[0]
    configuration_file_contents = json.load(open(configuration_file_path, 'r'))

    schema_directory = os.path.realpath('./schema') + '/'
    configuration_schema_file_path = os.path.join(schema_directory,
                                                  'alfred_speech.configuration.schema.json')  # noqa: E501
    configuration_schema_reference_resolver = RefResolver(
        'file://' + schema_directory,
        configuration_schema_file_path)
    validate(configuration_file_contents,
             json.load(open(configuration_schema_file_path, 'r')),
             resolver=configuration_schema_reference_resolver)

    # Bootstrap.
    input_id = parser.parse_args().input_id_override
    if input_id is None:
        input_id = configuration_file_contents['input_id']
    output_id = parser.parse_args().output_id_override
    if output_id is None:
        output_id = configuration_file_contents['output_id']
    configuration = Configuration(input_id, output_id,
                                  configuration_file_contents['call_signs'],
                                  configuration_file_contents[
                                      'global_interaction_ids'],
                                  configuration_file_contents[
                                      'root_interaction_ids'])
    environment = Environment(configuration)
    listener = Listener(environment, environment.plugins.get(input_id))

    # Run.
    listener.listen()
