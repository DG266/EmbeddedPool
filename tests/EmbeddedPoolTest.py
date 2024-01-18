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
from libs.DS18B20 import DS18B20


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.ep = EmbeddedPool()

    @patch.object(DS18B20, "read_temp")
    def test_check_water_temperature_with_good_temperature(self, mock_read_temp):
        mock_read_temp.return_value = 26.00

        self.ep.check_water_temperature()

        self.assertEqual(True, self.ep.correct_water_temperature)

    @patch.object(DS18B20, "read_temp")
    def test_check_water_temperature_with_temperature_too_high(self, mock_read_temp):
        mock_read_temp.return_value = 28.00

        self.ep.check_water_temperature()

        self.assertEqual(False, self.ep.correct_water_temperature)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_check_environment_temperature_and_humidity_with_both_correct(self, mock_read_temp, mock_read_retry):
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [27.00, 28.00]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()

        self.assertEqual(True, self.ep.correct_humidity)
        self.assertEqual(True, self.ep.correct_environment_temperature)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_check_environment_temperature_and_humidity_with_both_wrong(self, mock_read_temp, mock_read_retry):
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [30.00, 29.00]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()

        self.assertEqual(False, self.ep.correct_humidity)
        self.assertEqual(False, self.ep.correct_environment_temperature)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_check_environment_temperature_and_humidity_with_wrong_temperature(self, mock_read_temp, mock_read_retry):
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [27.00, 30.00]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()

        self.assertEqual(True, self.ep.correct_humidity)
        self.assertEqual(False, self.ep.correct_environment_temperature)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_check_environment_temperature_and_humidity_with_wrong_humidity(self, mock_read_temp, mock_read_retry):
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [40.00, 28.00]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()

        self.assertEqual(False, self.ep.correct_humidity)
        self.assertEqual(True, self.ep.correct_environment_temperature)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_check_environment_temperature_and_humidity_with_failed_reading(self, mock_read_temp, mock_read_retry):
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [None, None]

        self.ep.check_water_temperature()

        self.assertRaises(DHTError, self.ep.check_humidity_and_environment_temperature)

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
    @patch.object(DS18B20, "read_temp")
    def test_control_windows_with_humidity_too_high(self, mock_read_temp, mock_read_retry):
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [31.50, 28.00]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()
        self.ep.control_windows()

        self.assertEqual(True, self.ep.are_windows_open)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_control_windows_with_good_humidity(self, mock_read_temp, mock_read_retry):
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [29.94, 27.70]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()
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

    def test_update_current_screen_text_on_screen_0(self):
        # Remember that the default screen is screen 0, so it's not necessary
        # self.ep.current_screen = 0
        self.ep.humidity = 27
        self.ep.environment_temperature = 28

        self.ep.update_current_screen_text()

        self.assertEqual("EnvTmp: 28.00\nHum: 27.00", self.ep.current_lcd_text)

    def test_update_current_screen_text_on_screen_1(self):
        self.ep.current_screen = 1
        self.ep.water_ph = 7.283567

        self.ep.update_current_screen_text()

        self.assertEqual("pH: 7.28", self.ep.current_lcd_text)

    def test_update_current_screen_text_on_screen_2(self):
        self.ep.current_screen = 2
        self.ep.water_turbidity = 0

        self.ep.update_current_screen_text()

        self.assertEqual("Turb: 0.00", self.ep.current_lcd_text)

    def test_button_prev_event_on_screen_0(self):
        # Remember that the default screen is screen 0, so it's not necessary
        # self.ep.current_screen = 0
        self.ep.water_turbidity = 0

        self.ep.button_prev_event(self.ep.BUTTON_PREV_PIN)

        self.assertEqual(2, self.ep.current_screen)

    def test_button_prev_event_on_screen_1(self):
        self.ep.current_screen = 1
        self.ep.humidity = 27.00
        self.ep.environment_temperature = 28.00

        self.ep.button_prev_event(self.ep.BUTTON_PREV_PIN)

        self.assertEqual(0, self.ep.current_screen)

    def test_button_prev_event_on_screen_2(self):
        self.ep.current_screen = 2
        self.ep.water_ph = 7.28

        self.ep.button_prev_event(self.ep.BUTTON_PREV_PIN)

        self.assertEqual(1, self.ep.current_screen)

    def test_button_next_event_on_screen_0(self):
        # Remember that the default screen is screen 0, so it's not necessary
        # self.ep.current_screen = 0
        self.ep.water_ph = 7.28

        self.ep.button_next_event(self.ep.BUTTON_NEXT_PIN)

        self.assertEqual(1, self.ep.current_screen)

    def test_button_next_event_on_screen_1(self):
        self.ep.current_screen = 1
        self.ep.water_turbidity = 0

        self.ep.button_next_event(self.ep.BUTTON_NEXT_PIN)

        self.assertEqual(2, self.ep.current_screen)

    def test_button_next_event_on_screen_2(self):
        self.ep.current_screen = 2
        self.ep.humidity = 27.00
        self.ep.environment_temperature = 28.00

        self.ep.button_next_event(self.ep.BUTTON_NEXT_PIN)

        self.assertEqual(0, self.ep.current_screen)
