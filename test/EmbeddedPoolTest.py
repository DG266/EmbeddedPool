try:
    import RPi.GPIO as GPIO
except ImportError:
    import mock.GPIO as GPIO
import unittest
from unittest.mock import patch
from EmbeddedPool import EmbeddedPool


class MyTestCase(unittest.TestCase):
    def setUp(self)->None:
        self.es=EmbeddedPool()

    @patch.object(GPIO,"input")
    def test_water_temperature(self,mock_input):
        # Arrange
        mock_input.return_value=26

        # Act
        self.es.check_water_temperature()

        # Assert
        self.assertEqual(True,self.es.correct_water_temperature)

    @patch.object(GPIO, "input")
    def test_water_temperature_2(self, mock_input):
        # Arrange
        mock_input.return_value = 28

        # Act
        self.es.check_water_temperature()

        # Assert
        self.assertEqual(False, self.es.correct_water_temperature)

    @patch.object(GPIO, "input")
    def test_environment_temperature(self, mock_input):
        # Arrange
        mock_input.return_value = 28
        self.es.current_water_temperature = 26

        # Act
        self.es.check_environment_temperature()

        # Assert
        self.assertEqual(True, self.es.correct_environment_temperature)