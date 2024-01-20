try:
    import RPi.GPIO as GPIO
    import Adafruit_DHT
except ImportError:
    import mock.GPIO as GPIO
    import mock.Adafruit_DHT as Adafruit_DHT
import unittest
from unittest.mock import call
from LCDError import LCDError
from DHTError import DHTError
from unittest.mock import patch
from EmbeddedPool import EmbeddedPool
from libs.DFRobot_ADS1115 import ADS1115
from libs.DS18B20 import DS18B20


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.ep = EmbeddedPool()

    ''' WATER TEMPERATURE TESTS #################################################################################### '''
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

    @patch.object(DS18B20, "read_temp")
    def test_check_water_temperature_with_temperature_too_low(self, mock_read_temp):
        mock_read_temp.return_value = 18.00

        self.ep.check_water_temperature()

        self.assertEqual(False, self.ep.correct_water_temperature)

    @patch.object(DS18B20, "read_temp")
    def test_check_water_temperature_with_max_temperature(self, mock_read_temp):
        mock_read_temp.return_value = self.ep.WATER_TEMP_MAX

        self.ep.check_water_temperature()

        self.assertEqual(True, self.ep.correct_water_temperature)

    @patch.object(DS18B20, "read_temp")
    def test_check_water_temperature_with_min_temperature(self, mock_read_temp):
        mock_read_temp.return_value = self.ep.WATER_TEMP_MIN

        self.ep.check_water_temperature()

        self.assertEqual(True, self.ep.correct_water_temperature)

    ''' ENV. TEMP. + HUMIDITY TESTS ################################################################################ '''
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
    def test_check_environment_temperature_and_humidity_with_failed_reading(self, mock_read_temp, mock_read_retry):
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [None, None]

        self.ep.check_water_temperature()

        self.assertRaises(DHTError, self.ep.check_humidity_and_environment_temperature)

    ''' pH TESTS ################################################################################################### '''
    @patch.object(ADS1115, "read_voltage")
    def test_check_water_ph_with_good_ph_value(self, mock_read_voltage):
        # IMPORTANT: if the voltage is 1450 mV, the pH will be 7.28 (which is good)
        mock_read_voltage.return_value = 1450

        self.ep.check_water_ph()

        self.assertEqual(True, self.ep.is_acceptable_ph)

    @patch.object(ADS1115, "read_voltage")
    def test_check_water_ph_with_too_low_ph_value(self, mock_read_voltage):
        # IMPORTANT: if the voltage is 2000 mV, the pH will be 4.18 (which is bad)
        mock_read_voltage.return_value = 2000

        self.ep.check_water_ph()

        self.assertEqual(False, self.ep.is_acceptable_ph)

    @patch.object(ADS1115, "read_voltage")
    def test_check_water_ph_with_too_high_ph_value(self, mock_read_voltage):
        # IMPORTANT: if the voltage is 500 mV, the pH will be 12.63 (which is bad)
        mock_read_voltage.return_value = 500

        self.ep.check_water_ph()

        self.assertEqual(False, self.ep.is_acceptable_ph)

    ''' ORP/CHLORINE TESTS ######################################################################################### '''
    @patch.object(ADS1115, "read_voltage")
    def test_check_orp_with_good_orp(self, mock_read_voltage):
        # 1230 mV -> 770 mV (ORP)
        mock_read_voltage.return_value = 1230

        self.ep.check_orp()

        self.assertEqual(True, self.ep.is_acceptable_orp)

    @patch.object(ADS1115, "read_voltage")
    def test_check_orp_with_too_low_orp(self, mock_read_voltage):
        # 2000 mV -> 0 mV (ORP)
        mock_read_voltage.return_value = 2000

        self.ep.check_orp()

        self.assertEqual(False, self.ep.is_acceptable_orp)

    @patch.object(ADS1115, "read_voltage")
    def test_check_orp_with_too_high_orp(self, mock_read_voltage):
        # 800 mV -> 1200 mV (ORP)
        mock_read_voltage.return_value = 800

        self.ep.check_orp()

        self.assertEqual(False, self.ep.is_acceptable_orp)

    ''' WATER TURBIDITY TESTS ###################################################################################### '''
    @patch.object(ADS1115, "read_voltage")
    def test_check_turbidity_with_good_turbidity(self, mock_read_voltage):
        # 4300 mV -> O NTU
        mock_read_voltage.return_value = 4300

        self.ep.check_turbidity()

        self.assertEqual(True, self.ep.is_acceptable_turbidity)

    @patch.object(ADS1115, "read_voltage")
    def test_check_turbidity_with_too_high_turbidity(self, mock_read_voltage):
        # 2500 mV -> 3000.35 NTU
        mock_read_voltage.return_value = 2500

        self.ep.check_turbidity()

        self.assertEqual(False, self.ep.is_acceptable_turbidity)

    ''' ENVIRONMENT LIGHT TESTS #################################################################################### '''
    @patch.object(ADS1115, "read_voltage")
    def test_check_environment_light_level_with_good_lighting(self, mock_read_voltage):
        # 1390 mV -> 373 lux
        mock_read_voltage.return_value = 1390

        self.ep.check_environment_light_level()

        self.assertEqual(True, self.ep.is_acceptable_light)

    @patch.object(ADS1115, "read_voltage")
    def test_check_environment_light_level_with_too_low_lighting(self, mock_read_voltage):
        # 0 mV -> 0 lux
        mock_read_voltage.return_value = 0

        self.ep.check_environment_light_level()

        self.assertEqual(False, self.ep.is_acceptable_light)

    @patch.object(ADS1115, "read_voltage")
    def test_check_environment_light_level_with_too_high_lighting(self, mock_read_voltage):
        # 4930 mV -> 1443 lux
        mock_read_voltage.return_value = 4930

        self.ep.check_environment_light_level()

        self.assertEqual(False, self.ep.is_acceptable_light)

    ''' WATER LEVEL TESTS ########################################################################################## '''
    @patch.object(GPIO, "input")
    def test_check_water_level_with_correct_level(self, mock_input):
        mock_input.return_value = 1

        self.ep.check_water_level()

        self.assertEqual(True, self.ep.is_water_level_good)

    @patch.object(GPIO, "input")
    def test_check_water_level_with_wrong_level(self, mock_input):
        mock_input.return_value = 0

        self.ep.check_water_level()

        self.assertEqual(False, self.ep.is_water_level_good)

    ''' SERVO MOTOR TESTS ########################################################################################## '''
    @patch.object(GPIO, "output")
    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_control_windows_with_good_humidity(self, mock_read_temp, mock_read_retry, mock_output):
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [29.94, 27.70]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()
        self.ep.control_windows()

        mock_output.assert_not_called()
        self.assertEqual(False, self.ep.are_windows_open)

    @patch.object(GPIO, "output")
    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_control_windows_with_humidity_too_high(self, mock_read_temp, mock_read_retry, mock_output):
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [31.50, 28.00]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()
        self.ep.control_windows()

        calls = [call(self.ep.SERVO_PIN, GPIO.HIGH), call(self.ep.SERVO_PIN, GPIO.LOW)]
        mock_output.assert_has_calls(calls, any_order=True)
        self.assertEqual(True, self.ep.are_windows_open)

    @patch.object(GPIO, "output")
    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_control_windows_with_humidity_too_low(self, mock_read_temp, mock_read_retry, mock_output):
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [24.00, 28.00]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()
        self.ep.control_windows()

        mock_output.assert_not_called()
        self.assertEqual(False, self.ep.are_windows_open)

    ''' LED TESTS ################################################################################################## '''
    @patch.object(ADS1115, "read_voltage")
    @patch.object(GPIO, "output")
    def test_control_led_with_correct_lighting(self, mock_output, mock_read_voltage):
        mock_read_voltage.return_value = 1390

        self.ep.check_environment_light_level()
        self.ep.control_led()

        mock_output.assert_called_once_with(self.ep.LED_PIN, GPIO.LOW)
        self.assertEqual(False, self.ep.is_led_on)

    @patch.object(ADS1115, "read_voltage")
    @patch.object(GPIO, "output")
    def test_control_led_with_too_low_lighting(self, mock_output, mock_read_voltage):
        mock_read_voltage.return_value = 100

        self.ep.check_environment_light_level()
        self.ep.control_led()

        mock_output.assert_called_once_with(self.ep.LED_PIN, GPIO.HIGH)
        self.assertEqual(True, self.ep.is_led_on)

    @patch.object(ADS1115, "read_voltage")
    @patch.object(GPIO, "output")
    def test_control_led_with_too_high_lighting(self, mock_output, mock_read_voltage):
        mock_read_voltage.return_value = 4000

        self.ep.check_environment_light_level()
        self.ep.control_led()

        mock_output.assert_called_once_with(self.ep.LED_PIN, GPIO.LOW)
        self.assertEqual(False, self.ep.is_led_on)

    ''' LCD SCREEN + BUTTONS TESTS ################################################################################# '''
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

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_update_current_screen_text_on_screen_0_with_hum_and_envtemp_good(self, mock_read_temp, mock_read_retry):
        # Remember that the default screen is screen 0, so it's not necessary
        # self.ep.current_screen = 0
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [27.00, 28.00]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()
        self.ep.update_current_screen_text()

        self.assertEqual("EnvTmp 28.00" + chr(223) + "C  \nHum     27.00%  ", self.ep.current_lcd_text)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_update_current_screen_text_on_screen_0_with_hum_and_envtemp_bad(self, mock_read_temp, mock_read_retry):
        # Remember that the default screen is screen 0, so it's not necessary
        # self.ep.current_screen = 0
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [30.00, 29.00]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()
        self.ep.update_current_screen_text()

        self.assertEqual("EnvTmp 29.00" + chr(223) + "C #\nHum     30.00% #", self.ep.current_lcd_text)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_update_current_screen_text_on_screen_0_with_bad_hum(self, mock_read_temp, mock_read_retry):
        # Remember that the default screen is screen 0, so it's not necessary
        # self.ep.current_screen = 0
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [40.00, 28.00]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()
        self.ep.update_current_screen_text()

        self.assertEqual("EnvTmp 28.00" + chr(223) + "C  \nHum     40.00% #", self.ep.current_lcd_text)

    @patch.object(Adafruit_DHT, "read_retry")
    @patch.object(DS18B20, "read_temp")
    def test_update_current_screen_text_on_screen_0_with_bad_envtemp(self, mock_read_temp, mock_read_retry):
        # Remember that the default screen is screen 0, so it's not necessary
        # self.ep.current_screen = 0
        # Water temperature
        mock_read_temp.return_value = 26.00
        # Adafruit_DHT.read_retry returns (humidity, temperature)
        mock_read_retry.return_value = [27.00, 30.00]

        self.ep.check_water_temperature()
        self.ep.check_humidity_and_environment_temperature()
        self.ep.update_current_screen_text()

        self.assertEqual("EnvTmp 30.00" + chr(223) + "C #\nHum     27.00%  ", self.ep.current_lcd_text)

    @patch.object(GPIO, "input")
    @patch.object(DS18B20, "read_temp")
    def test_update_current_screen_text_on_screen_1_with_water_temp_and_level_good(self, mock_read_temp, mock_input):
        self.ep.current_screen = 1
        mock_read_temp.return_value = 26.00
        mock_input.return_value = 1

        self.ep.check_water_temperature()
        self.ep.check_water_level()

        self.ep.update_current_screen_text()

        self.assertEqual("WatTmp 26.00" + chr(223) + "C  \nWater Level:  OK", self.ep.current_lcd_text)

    @patch.object(GPIO, "input")
    @patch.object(DS18B20, "read_temp")
    def test_update_current_screen_text_on_screen_1_with_water_temp_and_level_bad(self, mock_read_temp, mock_input):
        self.ep.current_screen = 1
        mock_read_temp.return_value = 18.00
        mock_input.return_value = 0

        self.ep.check_water_temperature()
        self.ep.check_water_level()

        self.ep.update_current_screen_text()

        self.assertEqual("WatTmp 18.00" + chr(223) + "C #\nWater Level: BAD", self.ep.current_lcd_text)

    @patch.object(GPIO, "input")
    @patch.object(DS18B20, "read_temp")
    def test_update_current_screen_text_on_screen_1_with_bad_water_temp(self, mock_read_temp, mock_input):
        self.ep.current_screen = 1
        mock_read_temp.return_value = 18.00
        mock_input.return_value = 1

        self.ep.check_water_temperature()
        self.ep.check_water_level()

        self.ep.update_current_screen_text()

        self.assertEqual("WatTmp 18.00" + chr(223) + "C #\nWater Level:  OK", self.ep.current_lcd_text)

    @patch.object(GPIO, "input")
    @patch.object(DS18B20, "read_temp")
    def test_update_current_screen_text_on_screen_1_with_bad_water_level(self, mock_read_temp, mock_input):
        self.ep.current_screen = 1
        mock_read_temp.return_value = 26.00
        mock_input.return_value = 0

        self.ep.check_water_temperature()
        self.ep.check_water_level()

        self.ep.update_current_screen_text()

        self.assertEqual("WatTmp 26.00" + chr(223) + "C  \nWater Level: BAD", self.ep.current_lcd_text)

    @patch.object(ADS1115, "read_voltage")
    def test_update_current_screen_text_on_screen_2_with_ph_and_orp_good(self, mock_read_voltage):
        self.ep.current_screen = 2
        mock_read_voltage.side_effect = [1450, 1230]

        self.ep.check_water_ph()
        self.ep.check_orp()
        self.ep.update_current_screen_text()

        self.assertEqual("pH        7.28  \nORP     770 mV  ", self.ep.current_lcd_text)

    @patch.object(ADS1115, "read_voltage")
    def test_update_current_screen_text_on_screen_2_with_ph_and_orp_bad(self, mock_read_voltage):
        self.ep.current_screen = 2
        mock_read_voltage.side_effect = [2000, 2000]

        self.ep.check_water_ph()
        self.ep.check_orp()
        self.ep.update_current_screen_text()

        self.assertEqual("pH        4.18 #\nORP       0 mV #", self.ep.current_lcd_text)

    @patch.object(ADS1115, "read_voltage")
    def test_update_current_screen_text_on_screen_2_with_good_ph(self, mock_read_voltage):
        self.ep.current_screen = 2
        mock_read_voltage.side_effect = [1450, 2000]

        self.ep.check_water_ph()
        self.ep.check_orp()
        self.ep.update_current_screen_text()

        self.assertEqual("pH        7.28  \nORP       0 mV #", self.ep.current_lcd_text)

    @patch.object(ADS1115, "read_voltage")
    def test_update_current_screen_text_on_screen_2_with_good_orp(self, mock_read_voltage):
        self.ep.current_screen = 2
        mock_read_voltage.side_effect = [2000, 1230]

        self.ep.check_water_ph()
        self.ep.check_orp()
        self.ep.update_current_screen_text()

        self.assertEqual("pH        4.18 #\nORP     770 mV  ", self.ep.current_lcd_text)

    @patch.object(ADS1115, "read_voltage")
    def test_update_current_screen_text_on_screen_3_with_good_lighting_level(self, mock_read_voltage):
        self.ep.current_screen = 3
        mock_read_voltage.return_value = 1390

        self.ep.check_environment_light_level()
        self.ep.update_current_screen_text()

        self.assertEqual("Env. Light      \n       373 lux  ", self.ep.current_lcd_text)

    @patch.object(ADS1115, "read_voltage")
    def test_update_current_screen_text_on_screen_3_with_bad_lighting_level(self, mock_read_voltage):
        self.ep.current_screen = 3
        mock_read_voltage.return_value = 0

        self.ep.check_environment_light_level()
        self.ep.update_current_screen_text()

        self.assertEqual("Env. Light      \n         0 lux #", self.ep.current_lcd_text)

    @patch.object(ADS1115, "read_voltage")
    def test_update_current_screen_text_on_screen_4_with_good_water_turbidity(self, mock_read_voltage):
        self.ep.current_screen = 4
        mock_read_voltage.return_value = 4300

        self.ep.check_turbidity()
        self.ep.update_current_screen_text()

        self.assertEqual("Water Turbidity \n      0.00 NTU  ", self.ep.current_lcd_text)

    @patch.object(ADS1115, "read_voltage")
    def test_update_current_screen_text_on_screen_4_with_bad_water_turbidity(self, mock_read_voltage):
        self.ep.current_screen = 4
        mock_read_voltage.return_value = 2500

        self.ep.check_turbidity()
        self.ep.update_current_screen_text()

        self.assertEqual("Water Turbidity \n   3000.35 NTU #", self.ep.current_lcd_text)

    def test_button_prev_event_on_screen_0(self):
        # Remember that the default screen is screen 0, so it's not necessary
        # self.ep.current_screen = 0
        self.ep.water_turbidity = 0

        self.ep.button_prev_event(self.ep.BUTTON_PREV_PIN)

        self.assertEqual(4, self.ep.current_screen)

    def test_button_prev_event_on_screen_1(self):
        self.ep.current_screen = 1
        self.ep.humidity = 27.00
        self.ep.environment_temperature = 28.00

        self.ep.button_prev_event(self.ep.BUTTON_PREV_PIN)

        self.assertEqual(0, self.ep.current_screen)

    def test_button_prev_event_on_screen_2(self):
        self.ep.current_screen = 2
        self.ep.water_temperature = 26
        self.ep.water_turbidity = 0

        self.ep.button_prev_event(self.ep.BUTTON_PREV_PIN)

        self.assertEqual(1, self.ep.current_screen)

    def test_button_prev_event_on_screen_3(self):
        self.ep.current_screen = 3
        self.ep.water_ph = 7.283567
        self.ep.orp = 760

        self.ep.button_prev_event(self.ep.BUTTON_PREV_PIN)

        self.assertEqual(2, self.ep.current_screen)

    def test_button_prev_event_on_screen_4(self):
        self.ep.current_screen = 4
        self.ep.environment_light = 300

        self.ep.button_prev_event(self.ep.BUTTON_PREV_PIN)

        self.assertEqual(3, self.ep.current_screen)

    def test_button_next_event_on_screen_0(self):
        # Remember that the default screen is screen 0, so it's not necessary
        # self.ep.current_screen = 0
        self.ep.water_temperature = 26
        self.ep.is_water_level_good = True

        self.ep.button_next_event(self.ep.BUTTON_NEXT_PIN)

        self.assertEqual(1, self.ep.current_screen)

    def test_button_next_event_on_screen_1(self):
        self.ep.current_screen = 1
        self.ep.water_ph = 7.283567
        self.ep.orp = 760

        self.ep.button_next_event(self.ep.BUTTON_NEXT_PIN)

        self.assertEqual(2, self.ep.current_screen)

    def test_button_next_event_on_screen_2(self):
        self.ep.current_screen = 2
        self.ep.environment_light = 300

        self.ep.button_next_event(self.ep.BUTTON_NEXT_PIN)

        self.assertEqual(3, self.ep.current_screen)

    def test_button_next_event_on_screen_3(self):
        self.ep.current_screen = 3
        self.ep.water_turbidity = 0

        self.ep.button_next_event(self.ep.BUTTON_NEXT_PIN)

        self.assertEqual(4, self.ep.current_screen)

    def test_button_next_event_on_screen_4(self):
        self.ep.current_screen = 4
        self.ep.humidity = 27.00
        self.ep.environment_temperature = 28.00

        self.ep.button_next_event(self.ep.BUTTON_NEXT_PIN)

        self.assertEqual(0, self.ep.current_screen)
