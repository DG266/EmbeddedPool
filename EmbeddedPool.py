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
    WATER_LEVEL_PIN=17

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
    LAST_SCREEN = 3

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

        # Servo motor setup
        GPIO.setup(self.SERVO_PIN, GPIO.OUT)
        self.p = GPIO.PWM(self.SERVO_PIN, 50)
        self.p.start(0)
        # self.p.ChangeDutyCycle(2)

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

        self.are_windows_open = False
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
        logging.info("START check_orp")
        voltage = self.ads1115.read_voltage(self.ORP_SENSOR_PIN)
        voltage = voltage / 1000  # from mV to V
        system_voltage = 5.00
        offset = 0

        self.orp = int(((30 * system_voltage * 1000) - (75 * voltage * 1000)) / 75 - offset)
        print(self.orp)

        if self.ORP_MIN <= self.orp <= self.ORP_MAX:
            self.is_acceptable_orp = True
        else:
            self.is_acceptable_orp = False
        logging.info(
            "END   check_orp (value = %.2f mV, correct = %s)",
            self.orp, self.is_acceptable_orp
        )

    def check_turbidity(self) -> None:
        logging.info("START check_turbidity")
        # See https://wiki.dfrobot.com/Turbidity_sensor_SKU__SEN0189
        voltage = self.ads1115.read_voltage(self.TURBIDITY_SENSOR_PIN)
        voltage = voltage / 1000  # from mV to V
        ntu_val = (-1120.4 * (voltage ** 2)) + (5742.3 * voltage) - 4352.9

        # In clean water, the sensor reads 4.3/4.4 volts,
        # but, in that case, the formula above returns a negative NTU value.
        # The value of NTU cannot be negative, so we set it equal to zero.
        if ntu_val <= 0:
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
        logging.info("START check_environment_light_level")
        voltage = self.ads1115.read_voltage(self.ENV_LIGHT_SENSOR_PIN)
        self.environment_light = int((((voltage - 206) * 358) / 1184) + 15)

        if self.LUX_MIN <= self.environment_light <= self.LUX_MAX:
            self.is_acceptable_light = True
        else:
            self.is_acceptable_light = False
        logging.info(
            "END   check_environment_light_level (value = %d lux, correct = %s)",
            self.environment_light, self.is_acceptable_light
        )

    def control_windows(self) -> None:
        logging.info("START control_windows")
        if not self.correct_humidity and not self.are_windows_open:
            self.change_servo_angle(self.DC_OPEN)
            self.are_windows_open = True
        elif self.correct_humidity and self.are_windows_open:
            self.change_servo_angle(self.DC_CLOSED)
            self.are_windows_open = False
        logging.info("END   control_windows (are_windows_open = %s)", self.are_windows_open)

    def change_servo_angle(self, duty_cycle: float) -> None:
        GPIO.output(self.SERVO_PIN, GPIO.HIGH)
        self.p.ChangeDutyCycle(duty_cycle)
        time.sleep(1)
        GPIO.output(self.SERVO_PIN, GPIO.LOW)
        self.p.ChangeDutyCycle(0)

    def turn_on_lcd_backlight(self):
        if not self.is_lcd_backlight_on:
            self.pcf.output(3, 1)  # Turn on LCD backlight
            self.is_lcd_backlight_on = True
        else:
            raise LCDError("The LCD is already on.")

    def turn_off_lcd_backlight(self):
        if self.is_lcd_backlight_on:
            self.pcf.output(3, 0)  # Turn off LCD backlight
            self.is_lcd_backlight_on = False
        else:
            raise LCDError("The LCD is already off.")

    def lcd_print(self, message):
        self.lcd.setCursor(0, 0)
        self.lcd.message(message)

    def lcd_clear(self):
        self.lcd.clear()

    def update_current_screen_text(self):
        if self.current_screen == 0:
            self.current_lcd_text = f"EnvTmp: {self.environment_temperature: >6.2f}{chr(223)}C\n"\
                                    f"Hum: {self.humidity: >10.2f}%"
        elif self.current_screen == 1:
            self.current_lcd_text = f"WatTmp: {self.water_temperature: >6.2f}{chr(223)}C\n"\
                                    f"Turb: {self.water_turbidity: >6.1f} NTU"
        elif self.current_screen == 2:
            self.current_lcd_text = f"pH: {self.water_ph: >12.2f}\n"\
                                    f"ORP: {self.orp: >8} mV"
        elif self.current_screen == 3:
            self.current_lcd_text = f"Light: {self.environment_light: >5} lux"

    def lcd_update(self):
        with self.current_screen_lock:
            self.update_current_screen_text()
            self.lcd_print(self.current_lcd_text)

    def button_prev_event(self, channel):
        logging.info("BUTTON_PREV (GPIO %d)", channel)
        with self.current_screen_lock:
            self.current_screen = self.current_screen - 1
            if self.current_screen < self.FIRST_SCREEN:
                self.current_screen = self.LAST_SCREEN

            self.update_current_screen_text()
            self.lcd_clear()
            self.lcd_print(self.current_lcd_text)

    def button_next_event(self, channel):
        logging.info("BUTTON_NEXT (GPIO %d)", channel)
        with self.current_screen_lock:
            self.current_screen = self.current_screen + 1
            if self.current_screen > self.LAST_SCREEN:
                self.current_screen = self.FIRST_SCREEN

            self.update_current_screen_text()
            self.lcd_clear()
            self.lcd_print(self.current_lcd_text)

    def turn_off(self):
        if self.are_windows_open:
            self.change_servo_angle(self.DC_CLOSED)
        self.lcd_clear()
        self.turn_off_lcd_backlight()
        self.p.stop()
        GPIO.cleanup()

    def check_water_level(self):
      result =GPIO.input(self.WATER_LEVEL_PIN )
      if result==1:
          self.is_water_level_good=True

      else:
         self.is_water_level_good=False
