from unittest import TestCase
from unittest.mock import patch

from alfred_maison.ola import DmxPanel


class DmxPanelTest(TestCase):
    def test_set_with_invalid_channel(self):
        sut = DmxPanel(1, 3)
        with self.assertRaises(ValueError):
            sut.set(0, 178)
        with self.assertRaises(ValueError):
            sut.set(4, 178)

    def test_set_with_invalid_value(self):
        sut = DmxPanel(1, 3)
        with self.assertRaises(ValueError):
            sut.set(1, -1)
        with self.assertRaises(ValueError):
            sut.set(1, 256)

    @patch('subprocess.call')
    def test_set(self, m_patch):
        universe = 3
        sut = DmxPanel(universe, 9)
        sut.set(1, 237)
        m_patch.assert_called_with(
            ['ola_set_dmx', '-u', str(universe), '-d', '237,0,0,0,0,0,0,0,0'])
        sut.set(1, 58)
        m_patch.assert_called_with(
            ['ola_set_dmx', '-u', str(universe), '-d', '58,0,0,0,0,0,0,0,0'])
        sut.set(7, 58)
        m_patch.assert_called_with(
            ['ola_set_dmx', '-u', str(universe), '-d', '58,0,0,0,0,0,58,0,0'])
        sut.set(7, 0)
        m_patch.assert_called_with(
            ['ola_set_dmx', '-u', str(universe), '-d', '58,0,0,0,0,0,0,0,0'])

    @patch('subprocess.call')
    def test_set_multiple(self, m_patch):
        universe = 3
        sut = DmxPanel(universe, 9)
        sut.set_multiple({
            1: 237,
        })
        m_patch.assert_called_with(
            ['ola_set_dmx', '-u', str(universe), '-d', '237,0,0,0,0,0,0,0,0'])
        sut.set_multiple({
            1: 58,
            5: 3,
        })
        m_patch.assert_called_with(
            ['ola_set_dmx', '-u', str(universe), '-d', '58,0,0,0,3,0,0,0,0'])
        sut.set_multiple({
            7: 58,
            6: 249,
        })
        m_patch.assert_called_with(
            ['ola_set_dmx', '-u', str(universe), '-d', '58,0,0,0,3,249,58,0,0'])
        sut.set_multiple({
            7: 0,
            6: 0,
        })
        m_patch.assert_called_with(
            ['ola_set_dmx', '-u', str(universe), '-d', '58,0,0,0,3,0,0,0,0'])

    def test_get_with_invalid_channel(self):
        sut = DmxPanel(1, 3)
        with self.assertRaises(ValueError):
            sut.get(0)
        with self.assertRaises(ValueError):
            sut.get(4)
