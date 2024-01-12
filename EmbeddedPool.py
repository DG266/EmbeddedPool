import time

try:
    import RPi.GPIO as GPIO
    import Adafruit_DHT
except ImportError:
    import mock.GPIO as GPIO
    import mock.Adafruit_DHT as Adafruit_DHT
from libs.DFRobot_ADS1115 import ADS1115
from libs.DFRobot_PH import DFRobot_PH


class EmbeddedPool:
    # Raspberry BCM GPIO pins
    TEMPERATURE_WATER_PIN = 27
    DHT_PIN = 26
    SERVO_PIN = 20

    # ADC pins
    PH_SENSOR_PIN = 0
    TURBIDITY_SENSOR_PIN = 1
    CHOLORIN_SENSOR_PIN = 3

    # Servo motor stuff
    DC_OPEN = (180 / 18) + 2
    DC_CLOSED = (0 / 18) + 2

    # Values
    WATER_TEMP_MIN = 25.5
    WATER_TEMP_MAX = 27.7
    HUMIDITY_MIN = 25.56
    HUMIDITY_MAX = 29.94
    PH_MIN = 7.2
    PH_MAX = 7.6
    CHLORINE_MIN = 1
    CHLORINE_MAX = 1.5
    TURBIDITY_MIN = 0
    TURBIDITY_MAX = 0.5

    def __init__(self):
        # Use Broadcom GPIO numbers
        GPIO.setmode(GPIO.BCM)

        # ADC setup
        self.ads1115 = ADS1115()
        self.ads1115.set_addr_ADS1115(0x48)
        self.ads1115.set_gain(0x00)

        # DHT11 setup
        self.dht_type = Adafruit_DHT.DHT11

        # pH sensor setup
        self.ph_helper = DFRobot_PH()

        # Servo motor setup
        GPIO.setup(self.SERVO_PIN, GPIO.OUT)
        self.servo = GPIO.PWM(self.SERVO_PIN, 50)
        self.servo.start(0)
        self.servo.ChangeDutyCycle(2)

        # Instance variables
        self.correct_water_temperature = None
        self.current_water_temperature = None
        self.correct_environment_temperature = None
        self.current_environment_temperature = None
        self.is_acceptable_ph = None
        self.water_ph = None
        self.is_acceptable_cholorin = None
        self.water_cholorin = None
        self.correct_humidity = None
        self.humidity_level = None
        self.is_acceptable_turbidity = None
        self.current_turbidity = None
        self.are_windows_open = None

    def check_water_temperature(self) -> None:
        result = GPIO.input(self.TEMPERATURE_WATER_PIN)
        if self.WATER_TEMP_MIN <= result <= self.WATER_TEMP_MAX:
            self.correct_water_temperature = True
        else:
            self.correct_water_temperature = False

    def check_environment_temperature(self) -> None:
        humidity, temperature_environment = Adafruit_DHT.read_retry(self.dht_type, self.DHT_PIN)
        if temperature_environment > (self.current_water_temperature + 2):
            self.correct_environment_temperature = False
        elif temperature_environment <= (self.current_water_temperature + 2):
            self.correct_environment_temperature = True

    def check_water_ph(self) -> None:
        # Read the voltage from the ADC (where the pH probe is connected)
        voltage = self.ads1115.read_voltage(self.PH_SENSOR_PIN)
        # Use the DFRobot pH library to convert voltage to pH
        result = self.ph_helper.read_PH(voltage, None)

        if self.PH_MIN < result < self.PH_MAX:
            self.is_acceptable_ph = True
        else:
            self.is_acceptable_ph = False

        # Update the pH value in the instance variable
        self.water_ph = result

    def check_cholorin_level(self) -> None:
        voltage = self.ads1115.read_voltage(self.CHOLORIN_SENSOR_PIN)
        orp_value = ((30 * voltage * 1000) - (voltage * 1000))

        if orp_value > self.CHLORINE_MAX:
            self.is_acceptable_cholorin = False
        elif orp_value <= self.CHLORINE_MIN:
            self.is_acceptable_cholorin = False
        elif self.CHLORINE_MIN <= orp_value < self.CHLORINE_MAX:
            self.is_acceptable_cholorin = True

    def check_humidity_level(self) -> None:
        humidity, environment_temperature = Adafruit_DHT.read_retry(self.dht_type, self.DHT_PIN)
        if self.HUMIDITY_MIN <= humidity <= self.HUMIDITY_MAX:
            self.correct_humidity = True
        else:
            self.correct_humidity = False

    def check_turbidity(self) -> None:
        # See https://wiki.dfrobot.com/Turbidity_sensor_SKU__SEN0189
        voltage = self.ads1115.read_voltage(self.TURBIDITY_SENSOR_PIN)
        voltage = voltage / 1000  # from mV to V
        ntu_val = (-1120.4 * (voltage ** 2)) + (5742.3 * voltage) - 4352.9

        # In clean water, the sensor reads 4.3/4.4 volts,
        # but, in that case, the formula above returns a negative NTU value.
        # The value of NTU cannot be negative, so we set it equal to zero.
        if ntu_val <= 0:
            self.current_turbidity = 0
        else:
            self.current_turbidity = ntu_val

        if self.TURBIDITY_MIN <= self.current_turbidity <= self.TURBIDITY_MAX:
            self.is_acceptable_turbidity = True
        else:
            self.is_acceptable_turbidity = False

    def control_windows(self) -> None:
        if not self.correct_humidity:
            self.change_servo_angle(self.DC_OPEN)
            self.are_windows_open = True
        else:
            self.change_servo_angle(self.DC_CLOSED)
            self.are_windows_open = False

    def change_servo_angle(self, duty_cycle: float) -> None:
        GPIO.output(self.SERVO_PIN, GPIO.HIGH)
        self.servo.ChangeDutyCycle(duty_cycle)
        time.sleep(1)
        GPIO.output(self.SERVO_PIN, GPIO.LOW)
        self.servo.ChangeDutyCycle(0)
