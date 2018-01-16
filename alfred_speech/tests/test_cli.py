import subprocess
from unittest import TestCase

import os
import tempfile


class RunTest(TestCase):
    def test(self):
        root_path = os.path.dirname(os.path.abspath(__file__ + '/../..'))
        process_arguments = 'printf \'Alfred\nHelp\' | %s/bin/listen -c ' \
                            '%s/examples/alfred_speech.json' % (root_path,
                                                                root_path)
        # Use temporary file handles to run the subprocess in isolation.
        with tempfile.TemporaryFile() as stdin:
            actual_output = subprocess.check_output(process_arguments,
                                                    stdin=stdin,
                                                    shell=True,
                                                    universal_newlines=True)
            expected_output = 'Say something:Yes?\nSay something:You have 4 ' \
                              'options: What day is it?, or, What time is ' \
                              'it?, or, Alfred, or, Help.\nSay something:'
            self.assertEqual(actual_output, expected_output)
