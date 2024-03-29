try:
    import RPi.GPIO as GPIO
    import Adafruit_DHT
except ImportError:
    import mock.GPIO as GPIO
    import mock.Adafruit_DHT as Adafruit_DHT
import time
import threading
import logging
from LCDError import LCDError
from DHTError import DHTError
from libs.DFRobot_ADS1115 import ADS1115
from libs.DFRobot_PH import DFRobot_PH
from libs.PCF8574 import PCF8574_GPIO
from libs.Adafruit_LCD1602 import Adafruit_CharLCD
from libs.DS18B20 import DS18B20


class EmbeddedPool:
    # Raspberry BCM GPIO pins
    WATER_TEMPERATURE_PIN = 4  # Not necessary
    DHT_PIN = 26
    SERVO_PIN = 18
    BUTTON_PREV_PIN = 5
    BUTTON_NEXT_PIN = 21
    WATER_LEVEL_PIN = 17
    LED_PIN = 24

    # ADC pins
    PH_SENSOR_PIN = 0
    TURBIDITY_SENSOR_PIN = 1
    ENV_LIGHT_SENSOR_PIN = 2
    ORP_SENSOR_PIN = 3

    # Servo motor stuff
    DC_OPEN = (180 / 18) + 2
    DC_CLOSED = (0 / 18) + 2

    # Thresholds
    WATER_TEMP_MIN = 25.5
    WATER_TEMP_MAX = 27.7
    HUMIDITY_MIN = 25.56
    HUMIDITY_MAX = 29.94
    PH_MIN = 7.2
    PH_MAX = 7.6
    ORP_MIN = 750
    ORP_MAX = 770
    TURBIDITY_MIN = 0
    TURBIDITY_MAX = 0.5
    LUX_MIN = 200
    LUX_MAX = 400

    FIRST_SCREEN = 0
    LAST_SCREEN = 4

    def __init__(self, log_level=None):
        if log_level == "Info":
            logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

        GPIO.setmode(GPIO.BCM)  # Use Broadcom GPIO numbers
        GPIO.setwarnings(True)

        # ADC setup
        self.ads1115 = ADS1115()
        self.ads1115.set_addr_ADS1115(0x48)
        self.ads1115.set_gain(0x00)

        # Water temperature sensor setup
        self.ds18b20 = DS18B20()

        # DHT11 setup
        self.dht_type = Adafruit_DHT.DHT11

        # pH sensor setup
        self.ph_helper = DFRobot_PH()

        # Liquid level sensor setup
        GPIO.setup(self.WATER_LEVEL_PIN, GPIO.IN)

        # Servo motor setup
        GPIO.setup(self.SERVO_PIN, GPIO.OUT)
        self.p = GPIO.PWM(self.SERVO_PIN, 50)
        self.p.start(0)
        # self.p.ChangeDutyCycle(2)

        # LED setup
        GPIO.setup(self.LED_PIN, GPIO.OUT)

        # LCD setup (0x27 is the I2C address of the PCF8574 chip)
        self.pcf = PCF8574_GPIO(0x27)
        self.lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4, 5, 6, 7], GPIO=self.pcf)
        self.lcd.begin(16, 2)  # Set number of LCD columns and rows
        self.current_screen = 0
        self.current_lcd_text = None

        # Buttons setup
        GPIO.setup(self.BUTTON_PREV_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.BUTTON_NEXT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.BUTTON_PREV_PIN, GPIO.FALLING, callback=self.button_prev_event, bouncetime=500)
        GPIO.add_event_detect(self.BUTTON_NEXT_PIN, GPIO.FALLING, callback=self.button_next_event, bouncetime=500)

        self.current_screen_lock = threading.Lock()

        # Instance variables - booleans
        self.correct_water_temperature = None
        self.correct_humidity = None
        self.correct_environment_temperature = None
        self.is_acceptable_ph = None
        self.is_acceptable_orp = None
        self.is_acceptable_turbidity = None
        self.is_acceptable_light = None
        self.is_water_level_good = None

        self.are_windows_open = False
        self.is_led_on = False
        self.is_lcd_backlight_on = False

        # Instance variables - values
        self.water_temperature = None
        self.humidity = None
        self.environment_temperature = None
        self.water_ph = None
        self.orp = None
        self.water_turbidity = None
        self.environment_light = None

        logging.info("The embedded system has been initialized")

    def check_water_temperature(self) -> None:
        """
        Check the water temperature using the DS18B20 sensor.

        Reads the current water temperature and updates the internal state variable.
        Additionally, checks if the water temperature is within the specified optimal range.

        :return: None
        """
        logging.info("START check_water_temperature")
        self.water_temperature = self.ds18b20.read_temp()
        if self.WATER_TEMP_MIN <= self.water_temperature <= self.WATER_TEMP_MAX:
            self.correct_water_temperature = True
        else:
            self.correct_water_temperature = False
        logging.info(
            "END   check_water_temperature (value = %.2f°C, correct = %s)",
            self.water_temperature, self.correct_water_temperature
        )

    def check_humidity_and_environment_temperature(self) -> None:
        """
        Check humidity and environment temperature using the DHT11 sensor.

        Reads the current humidity and environment temperature and updates the internal state variables.
        Checks if the environment temperature is within a specified range relative to the water temperature.
        Also, verifies if the humidity is within the optimal range.

        Remember to read water temperature before calling this method!

        :return: None
        :raises DHTError: If failed to read data from the DHT sensor.
        """
        logging.info("START check_humidity_and_environment_temperature")
        self.humidity, self.environment_temperature = Adafruit_DHT.read_retry(self.dht_type, self.DHT_PIN)

        # You should always check water temperature before proceeding

        if self.humidity is not None and self.environment_temperature is not None:
            if self.environment_temperature > (self.water_temperature + 2):
                self.correct_environment_temperature = False
            elif self.environment_temperature <= (self.water_temperature + 2):
                self.correct_environment_temperature = True

            if self.HUMIDITY_MIN <= self.humidity <= self.HUMIDITY_MAX:
                self.correct_humidity = True
            else:
                self.correct_humidity = False
        else:
            raise DHTError("Failed to read from DHT sensor.")
        logging.info(
            "END   check_humidity_and_environment_temperature Hum(value = %.2f%%, correct = %s)"
            " Temp(value = %.2f°C, correct = %s)",
            self.humidity, self.correct_humidity,
            self.environment_temperature, self.correct_environment_temperature
        )

    def check_water_ph(self) -> None:
        """
        Check the pH level of the water using the pH sensor.

        Reads the voltage from the pH sensor, converts it to pH using the DFRobot pH library,
        and updates the internal state variable for water pH.
        Verifies if the water pH is within the optimal range.

        :return: None
        """
        logging.info("START check_water_ph")
        # Read the voltage from the ADC (where the pH probe is connected)
        voltage = self.ads1115.read_voltage(self.PH_SENSOR_PIN)
        # Use the DFRobot pH library to convert voltage to pH
        self.water_ph = self.ph_helper.read_PH(voltage, None)

        if self.PH_MIN < self.water_ph < self.PH_MAX:
            self.is_acceptable_ph = True
        else:
            self.is_acceptable_ph = False

        logging.info(
            "END   check_water_ph (value = %.2f, correct = %s)",
            self.water_ph, self.is_acceptable_ph
        )

    def check_orp(self) -> None:
        """
        Check the Oxidation-Reduction Potential (ORP) level of the water using the ORP sensor.

        Reads the voltage from the ORP sensor, converts it to ORP using a formula,
        and updates the internal state variable for ORP.
        Verifies if the water ORP is within the optimal range.

        :return: None
        """
        logging.info("START check_orp")
        voltage = self.ads1115.read_voltage(self.ORP_SENSOR_PIN)
        voltage = voltage / 1000  # from mV to V
        system_voltage = 5.00
        offset = 0

        self.orp = int(((30 * system_voltage * 1000) - (75 * voltage * 1000)) / 75 - offset)

        if self.ORP_MIN <= self.orp <= self.ORP_MAX:
            self.is_acceptable_orp = True
        else:
            self.is_acceptable_orp = False
        logging.info(
            "END   check_orp (value = %.2f mV, correct = %s)",
            self.orp, self.is_acceptable_orp
        )

    def check_turbidity(self) -> None:
        """
        Check the turbidity level of the water using the turbidity sensor.

        Reads the voltage from the turbidity sensor, converts it to NTU (Nephelometric Turbidity Units)
        using a specified formula, and updates the internal state variable for water turbidity.
        Verifies if the water turbidity is within the optimal range.

        :return: None
        """
        logging.info("START check_turbidity")
        # See https://wiki.dfrobot.com/Turbidity_sensor_SKU__SEN0189
        voltage = self.ads1115.read_voltage(self.TURBIDITY_SENSOR_PIN)
        voltage = voltage / 1000  # from mV to V
        ntu_val = (-1120.4 * (voltage ** 2)) + (5742.3 * voltage) - 4352.9

        # In clean water, the sensor reads 4.3/4.4 volts,
        # but, in that case, the formula above returns a negative NTU value.
        # The value of NTU cannot be negative, so we set it equal to zero.
        if ntu_val < 0:
            self.water_turbidity = 0
        else:
            self.water_turbidity = ntu_val

        if self.TURBIDITY_MIN <= self.water_turbidity <= self.TURBIDITY_MAX:
            self.is_acceptable_turbidity = True
        else:
            self.is_acceptable_turbidity = False
        logging.info(
            "END   check_turbidity (value = %.2f NTU, correct = %s)",
            self.water_turbidity, self.is_acceptable_turbidity
        )

    def check_environment_light_level(self) -> None:
        """
        Check the light level in the environment using the light sensor.

        Reads the voltage from the light sensor, converts it to lux using a specified formula,
        and updates the internal state variable for environment light level.
        Verifies if the environment light level is within the optimal range.

        :return: None
        """
        logging.info("START check_environment_light_level")
        voltage = self.ads1115.read_voltage(self.ENV_LIGHT_SENSOR_PIN)
        lux_val = int((((voltage - 206) * 358) / 1184) + 15)  # This formula is not very good

        # Cannot be negative
        if lux_val < 0:
            self.environment_light = 0
        else:
            self.environment_light = lux_val

        if self.LUX_MIN <= self.environment_light <= self.LUX_MAX:
            self.is_acceptable_light = True
        else:
            self.is_acceptable_light = False
        logging.info(
            "END   check_environment_light_level (value = %d lux, correct = %s)",
            self.environment_light, self.is_acceptable_light
        )

    def check_water_level(self):
        """
        Check the water level in the pool using a liquid level sensor.

        Reads the digital signal from the liquid level sensor, interprets it as the water level,
        and updates the internal state variable for water level.
        Verifies if the water level is within the acceptable range.

        :return: None
        """
        logging.info("START check_water_level")
        result = GPIO.input(self.WATER_LEVEL_PIN)
        if result == 1:
            self.is_water_level_good = True
        else:
            self.is_water_level_good = False
        logging.info("END   check_water_level (is_water_level_good = %s)", self.is_water_level_good)

    def control_windows(self) -> None:
        """
        Control the windows in the pool area based on humidity levels.

        Checks the current humidity level in the environment.
        If the humidity exceeds the maximum threshold and the windows are not already open,
        opens the windows using a servo motor.
        If the humidity is within the acceptable range and the windows are open,
        closes the windows using a servo motor.

        :return: None
        """
        logging.info("START control_windows")
        if (self.humidity > self.HUMIDITY_MAX) and not self.are_windows_open:
            self.change_servo_angle(self.DC_OPEN)
            self.are_windows_open = True
        elif (self.humidity <= self.HUMIDITY_MAX) and self.are_windows_open:
            self.change_servo_angle(self.DC_CLOSED)
            self.are_windows_open = False
        logging.info("END   control_windows (are_windows_open = %s)", self.are_windows_open)

    def change_servo_angle(self, duty_cycle: float) -> None:
        """
        Change the angle of the servo motor.

        Controls the servo motor by setting the duty cycle based on the provided angle.
        The GPIO pin associated with the servo motor is activated, the duty cycle is adjusted,
        and after a short delay, the pin is deactivated.

        :param duty_cycle: The duty cycle representing the desired angle of the servo motor.
        :type duty_cycle: float

        :return: None
        """
        GPIO.output(self.SERVO_PIN, GPIO.HIGH)
        self.p.ChangeDutyCycle(duty_cycle)
        time.sleep(1)
        GPIO.output(self.SERVO_PIN, GPIO.LOW)
        self.p.ChangeDutyCycle(0)

    def control_led(self) -> None:
        """
        Control the LED based on the environment light level.

        Checks the environment light level and turns on the LED if it falls below a certain threshold.
        Otherwise, turns off the LED.

        :return: None
        """
        logging.info("START control_led")
        if self.environment_light < self.LUX_MIN:
            GPIO.output(self.LED_PIN, GPIO.HIGH)
            self.is_led_on = True
        else:
            GPIO.output(self.LED_PIN, GPIO.LOW)
            self.is_led_on = False
        logging.info("END   control_led (is_led_on = %s)", self.is_led_on)

    def turn_on_lcd_backlight(self):
        """
        Turn on the LCD backlight.

        If the LCD backlight is not already on, this method turns it on. Otherwise, it raises an LCDError
        indicating that the LCD is already on.

        :return: None

        :raises LCDError: If the LCD backlight is already on.
        """
        if not self.is_lcd_backlight_on:
            self.pcf.output(3, 1)  # Turn on LCD backlight
            self.is_lcd_backlight_on = True
        else:
            raise LCDError("The LCD is already on.")

    def turn_off_lcd_backlight(self):
        """
        Turn off the LCD backlight.

        If the LCD backlight is currently on, this method turns it off. Otherwise, it raises an LCDError
        indicating that the LCD is already off.

        :return: None

        :raises LCDError: If the LCD backlight is already off.
        """
        if self.is_lcd_backlight_on:
            self.pcf.output(3, 0)  # Turn off LCD backlight
            self.is_lcd_backlight_on = False
        else:
            raise LCDError("The LCD is already off.")

    def lcd_print(self, message):
        """
        Print a message on the LCD.

        This method sets the cursor to the top-left corner of the LCD and prints the provided message.

        :param str message: The message to be displayed on the LCD.

        :return: None
        """
        self.lcd.setCursor(0, 0)
        self.lcd.message(message)

    def lcd_clear(self):
        """
        Clear the content of the LCD.

        This method clears the content displayed on the LCD screen.

        :return: None
        """
        self.lcd.clear()

    def update_current_screen_text(self):
        """
        Update the text content for the current LCD screen.

        This method updates the text content based on the current screen index and sensor readings.
        It includes warning symbols (#) for parameters outside the optimal range.

        :return: None
        """
        if self.current_screen == 0:
            warning_1 = " " if self.correct_environment_temperature else "#"
            warning_2 = " " if self.correct_humidity else "#"
            self.current_lcd_text = f"EnvTmp {self.environment_temperature: >5.2f}{chr(223)}C " + warning_1 + "\n" \
                                    f"Hum {self.humidity: >9.2f}% " + warning_2
        elif self.current_screen == 1:
            warning_1 = " " if self.correct_water_temperature else "#"
            water_level_text = "Water Level:  OK" if self.is_water_level_good else "Water Level: BAD"
            self.current_lcd_text = (f"WatTmp {self.water_temperature: >5.2f}{chr(223)}C " + warning_1 + "\n"
                                     + water_level_text)
        elif self.current_screen == 2:
            warning_1 = " " if self.is_acceptable_ph else "#"
            warning_2 = " " if self.is_acceptable_orp else "#"
            self.current_lcd_text = f"pH {self.water_ph: >11.2f} " + warning_1 + "\n" \
                                    f"ORP {self.orp: >7} mV " + warning_2
        elif self.current_screen == 3:
            warning = " " if self.is_acceptable_light else "#"
            self.current_lcd_text = f"Env. Light      \n{self.environment_light: >10} lux " + warning
        elif self.current_screen == 4:
            warning = " " if self.is_acceptable_turbidity else "#"
            self.current_lcd_text = f"Water Turbidity \n{self.water_turbidity: >10.2f} NTU " + warning

    def lcd_update(self):
        """
        Update the LCD screen with the current sensor readings.

        This method locks the current screen to prevent concurrent updates and updates the LCD
        screen content with the information from the current sensor readings.

        :return: None
        """
        logging.info("START lcd_update")
        with self.current_screen_lock:
            self.update_current_screen_text()
            self.lcd_print(self.current_lcd_text)
        logging.info("END   lcd_update")

    def button_prev_event(self, channel):
        """
        Event handler for the button press to navigate to the previous screen.

        This method is triggered when the button connected to the specified GPIO channel
        for the 'previous' action is pressed. It updates the current screen index, ensuring
        it wraps around to the last screen if the first screen is exceeded. Then, it updates
        the LCD screen with the new content based on the updated screen index.

        :param channel: The GPIO channel to which the button for the 'previous' action is connected.
        :type channel: int
        :return: None
        """
        logging.info("BUTTON_PREV (GPIO %d)", channel)
        with self.current_screen_lock:
            self.current_screen = self.current_screen - 1
            if self.current_screen < self.FIRST_SCREEN:
                self.current_screen = self.LAST_SCREEN

            self.update_current_screen_text()
            self.lcd_clear()
            self.lcd_print(self.current_lcd_text)

    def button_next_event(self, channel):
        """
        Event handler for the button press to navigate to the next screen.

        This method is triggered when the button connected to the specified GPIO channel
        for the 'next' action is pressed. It updates the current screen index, ensuring
        it wraps around to the first screen if the last screen is exceeded. Then, it updates
        the LCD screen with the new content based on the updated screen index.

        :param channel: The GPIO channel to which the button for the 'next' action is connected.
        :type channel: int
        :return: None
        """
        logging.info("BUTTON_NEXT (GPIO %d)", channel)
        with self.current_screen_lock:
            self.current_screen = self.current_screen + 1
            if self.current_screen > self.LAST_SCREEN:
                self.current_screen = self.FIRST_SCREEN

            self.update_current_screen_text()
            self.lcd_clear()
            self.lcd_print(self.current_lcd_text)

    def turn_off(self):
        """
        Perform cleanup and shutdown procedures for the embedded system.

        This method is called when the system is being turned off. It ensures that the
        windows are closed, clears the LCD screen, turns off the LCD backlight, stops the
        servo motor, and cleans up GPIO resources.

        :return: None
        """
        if self.are_windows_open:
            self.change_servo_angle(self.DC_CLOSED)
        self.lcd_clear()
        self.turn_off_lcd_backlight()
        self.p.stop()
        GPIO.cleanup()
