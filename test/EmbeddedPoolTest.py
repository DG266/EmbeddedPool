try:
    import RPi.GPIO as GPIO
    import Adafruit_DHT
except ImportError:
    import mock.GPIO as GPIO
    import mock.Adafruit_DHT as Adafruit_DHT
import unittest
from unittest.mock import patch
from EmbeddedPool import EmbeddedPool
from libs.DFRobot_ADS1115 import ADS1115


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.es = EmbeddedPool()

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

    @patch.object(Adafruit_DHT,"read_retry")
    def test_environment_temperature(self, mock_input):
        # Arrange
        mock_input.return_value = [25,28]
        self.es.current_water_temperature = 26

        # Act
        self.es.check_environment_temperature()

        # Assert
        self.assertEqual(True, self.es.correct_environment_temperature)

    @patch.object(ADS1115, "read_voltage")
    def test_check_water_ph_with_good_ph_value(self, mock_input):
        # IMPORTANT: if the voltage is 1450 mV, the pH will be 7.28 (which is good)
        mock_input.return_value = 1450
        self.es.check_water_ph()
        self.assertEqual(True, self.es.is_acceptable_ph)

    @patch.object(ADS1115, "read_voltage")
    def test_check_water_ph_with_bad_ph_value(self, mock_input):
        # IMPORTANT: if the voltage is 2000 mV, the pH will be 4.18 (which is bad)
        mock_input.return_value = 2000
        self.es.check_water_ph()
        self.assertEqual(False, self.es.is_acceptable_ph)

    @patch.object(ADS1115, "read_voltage")
    def test_check_water_cholorin_level(self, mock_input):
        mock_input.return_value = 2000
        self.es.check_cholorin_level()
        self.assertEqual(False, self.es.is_acceptable_cholorin)

    @patch.object(Adafruit_DHT, "read_retry")
    def test_humidity_level(self, mock_input):
        # Arrange
        mock_input.return_value = [27, 28]

        # Act
        self.es.check_humidity_level()

        # Assert
        self.assertEqual(True, self.es.correct_humidity)

    @patch.object(Adafruit_DHT, "read_retry")
    def test_humidity_level_2(self, mock_input):
        # Arrange
        mock_input.return_value = [40, 28]

        # Act
        self.es.check_humidity_level()

        # Assert
        self.assertEqual(False, self.es.correct_humidity)
