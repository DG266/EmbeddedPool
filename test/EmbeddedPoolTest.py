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
        self.ep = EmbeddedPool()

    @patch.object(GPIO, "input")
    def test_check_water_temperature_with_good_temperature(self, mock_input):
        mock_input.return_value = 26

        self.ep.check_water_temperature()

        self.assertEqual(True, self.ep.correct_water_temperature)

    @patch.object(GPIO, "input")
    def test_check_water_temperature_with_temperature_too_high(self, mock_input):
        mock_input.return_value = 28

        self.ep.check_water_temperature()

        self.assertEqual(False, self.ep.correct_water_temperature)

    @patch.object(Adafruit_DHT, "read_retry")
    def test_check_environment_temperature(self, mock_read_retry):
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [25, 28]
        self.ep.current_water_temperature = 26

        self.ep.check_environment_temperature()

        self.assertEqual(True, self.ep.correct_environment_temperature)

    @patch.object(ADS1115, "read_voltage")
    def test_check_water_ph_with_good_ph_value(self, mock_read_voltage):
        # IMPORTANT: if the voltage is 1450 mV, the pH will be 7.28 (which is good)
        mock_read_voltage.return_value = 1450

        self.ep.check_water_ph()

        self.assertEqual(True, self.ep.is_acceptable_ph)

    @patch.object(ADS1115, "read_voltage")
    def test_check_water_ph_with_bad_ph_value(self, mock_read_voltage):
        # IMPORTANT: if the voltage is 2000 mV, the pH will be 4.18 (which is bad)
        mock_read_voltage.return_value = 2000

        self.ep.check_water_ph()

        self.assertEqual(False, self.ep.is_acceptable_ph)

    @patch.object(ADS1115, "read_voltage")
    def test_check_cholorin_level(self, mock_read_voltage):
        mock_read_voltage.return_value = 2000

        self.ep.check_cholorin_level()

        self.assertEqual(False, self.ep.is_acceptable_cholorin)

    @patch.object(Adafruit_DHT, "read_retry")
    def test_check_humidity_level_with_good_humidity(self, mock_read_retry):
        mock_read_retry.return_value = [27, 28]

        self.ep.check_humidity_level()

        self.assertEqual(True, self.ep.correct_humidity)

    @patch.object(Adafruit_DHT, "read_retry")
    def test_check_humidity_level_with_humidity_too_high(self, mock_read_retry):
        mock_read_retry.return_value = [40, 28]

        self.ep.check_humidity_level()

        self.assertEqual(False, self.ep.correct_humidity)

    @patch.object(Adafruit_DHT, "read_retry")
    def test_control_windows_with_humidity_too_high(self, mock_read_retry):
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [31, 28]

        self.ep.check_humidity_level()
        self.ep.control_windows()

        self.assertEqual(True, self.ep.are_windows_open)

    @patch.object(Adafruit_DHT, "read_retry")
    def test_control_windows_with_good_humidity(self, mock_read_retry):
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [29.94, 27.7]

        self.ep.check_humidity_level()
        self.ep.control_windows()

        self.assertEqual(False, self.ep.are_windows_open)
