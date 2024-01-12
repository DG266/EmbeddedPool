try:
    import RPi.GPIO as GPIO
    import Adafruit_DHT
except ImportError:
    import mock.GPIO as GPIO
    import mock.Adafruit_DHT as Adafruit_DHT
import unittest
from LCDError import LCDError
from DHTError import DHTError
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
    @patch.object(GPIO, "input")
    def test_check_environment_temperature_and_humidity_with_both_correct(self, mock_input, mock_read_retry):
        # Water temperature
        mock_input.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [27.00, 28.00]

        self.ep.check_water_temperature()
        self.ep.check_environment_temperature_and_humidity()

        self.assertEqual(True, self.ep.correct_humidity)
        self.assertEqual(True, self.ep.correct_environment_temperature)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(GPIO, "input")
    def test_check_environment_temperature_and_humidity_with_both_wrong(self, mock_input, mock_read_retry):
        # Water temperature
        mock_input.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [30.00, 29.00]

        self.ep.check_water_temperature()
        self.ep.check_environment_temperature_and_humidity()

        self.assertEqual(False, self.ep.correct_humidity)
        self.assertEqual(False, self.ep.correct_environment_temperature)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(GPIO, "input")
    def test_check_environment_temperature_and_humidity_with_wrong_temperature(self, mock_input, mock_read_retry):
        # Water temperature
        mock_input.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [27.00, 30.00]

        self.ep.check_water_temperature()
        self.ep.check_environment_temperature_and_humidity()

        self.assertEqual(True, self.ep.correct_humidity)
        self.assertEqual(False, self.ep.correct_environment_temperature)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(GPIO, "input")
    def test_check_environment_temperature_and_humidity_with_wrong_humidity(self, mock_input, mock_read_retry):
        # Water temperature
        mock_input.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [40.00, 28.00]

        self.ep.check_water_temperature()
        self.ep.check_environment_temperature_and_humidity()

        self.assertEqual(False, self.ep.correct_humidity)
        self.assertEqual(True, self.ep.correct_environment_temperature)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(GPIO, "input")
    def test_check_environment_temperature_and_humidity_with_failed_reading(self, mock_input, mock_read_retry):
        # Water temperature
        mock_input.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [None, None]

        self.ep.check_water_temperature()

        self.assertRaises(DHTError, self.ep.check_environment_temperature_and_humidity)

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
    @patch.object(GPIO, "input")
    def test_control_windows_with_humidity_too_high(self, mock_input, mock_read_retry):
        # Water temperature
        mock_input.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [31.50, 28.00]

        self.ep.check_water_temperature()
        self.ep.check_environment_temperature_and_humidity()
        self.ep.control_windows()

        self.assertEqual(True, self.ep.are_windows_open)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(GPIO, "input")
    def test_control_windows_with_good_humidity(self, mock_input, mock_read_retry):
        # Water temperature
        mock_input.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [29.94, 27.70]

        self.ep.check_water_temperature()
        self.ep.check_environment_temperature_and_humidity()
        self.ep.control_windows()

        self.assertEqual(False, self.ep.are_windows_open)

    @patch.object(ADS1115, "read_voltage")
    def test_check_turbidity_with_good_turbidity(self, mock_read_voltage):
        mock_read_voltage.return_value = 4300

        self.ep.check_turbidity()

        self.assertEqual(True, self.ep.is_acceptable_turbidity)

    @patch.object(ADS1115, "read_voltage")
    def test_check_turbidity_with_bad_turbidity(self, mock_read_voltage):
        mock_read_voltage.return_value = 2500

        self.ep.check_turbidity()

        self.assertEqual(False, self.ep.is_acceptable_turbidity)

    def test_turn_on_lcd_backlight(self):
        self.ep.turn_on_lcd_backlight()

        self.assertEqual(True, self.ep.is_lcd_backlight_on)

    def test_turn_on_lcd_backlight_when_it_is_already_on(self):
        self.ep.turn_on_lcd_backlight()

        self.assertRaises(LCDError, self.ep.turn_on_lcd_backlight)

    def test_turn_off_lcd_backlight(self):
        self.ep.turn_on_lcd_backlight()
        self.ep.turn_off_lcd_backlight()

        self.assertEqual(False, self.ep.is_lcd_backlight_on)

    def test_turn_off_lcd_backlight_when_it_is_already_off(self):
        self.assertRaises(LCDError, self.ep.turn_off_lcd_backlight)
