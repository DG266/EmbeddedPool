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
    TEMPERATURE_WATER_PIN = 11
    TEMPERATURE_ENVIRONMENT_PIN = 12
    HUMIDITY_PIN = 13

    # ADC pins
    PH_SENSOR_PIN = 0
    CHOLORIN_SENSOR_PIN = 1


    def __init__(self):
        # Use Broadcom GPIO numbers
        GPIO.setmode(GPIO.BCM)

        # ADC setup
        self.ads1115 = ADS1115()
        self.ads1115.set_addr_ADS1115(0x48)
        self.ads1115.set_gain(0x00)
        self.dht11=Adafruit_DHT.DHT11

        # pH sensor setup
        self.ph_helper = DFRobot_PH()

        # Instance variables
        self.correct_water_temperature = None
        self.current_water_temperature = None
        self.correct_environment_temperature = None
        self.current_environment_temperature = None
        self.is_acceptable_ph = None
        self.water_ph = None
        self.is_acceptable_cholorin=None
        self.water_cholorin = None
        self.correct_humidity = None
        self.humidity_level = None

    def check_water_temperature(self) -> None:
        result=GPIO.input(self.TEMPERATURE_WATER_PIN)
        if 25.5 <= result <= 27.7:
            self.correct_water_temperature=True
        else:
            self.correct_water_temperature=False

    def check_environment_temperature(self) -> None:
        hunidity,temperature_environment=Adafruit_DHT.read_retry(self.dht11,self.TEMPERATURE_ENVIRONMENT_PIN)
        if temperature_environment > (self.current_water_temperature + 2):
            # Environment temperature is too high
            self.correct_environment_temperature=False
        elif temperature_environment <= (self.current_water_temperature + 2):
            self.correct_environment_temperature=True

    def check_water_ph(self) -> None:
        # Read the voltage from the ADC (where the pH probe is connected)
        voltage = self.ads1115.read_voltage(self.PH_SENSOR_PIN)
        # Use the DFRobot pH library to convert voltage to pH
        result = self.ph_helper.read_PH(voltage, None)

        if 7.2 < result < 7.6:
            self.is_acceptable_ph = True
        else:
            self.is_acceptable_ph = False

        # Update the pH value in the instance variable
        self.water_ph = result

    def check_cholorin_level(self) -> None:
        # Read the voltage...
        voltage = self.ads1115.read_voltage(self.CHOLORIN_SENSOR_PIN)
        # Convert the voltage
        orp_value = ((30 * voltage * 1000) - (voltage * 1000))

        if orp_value > 1.5:
            self.is_acceptable_cholorin = False
        elif orp_value <= 1:
            self.is_acceptable_cholorin = False
        elif 1 <= orp_value < 1.5:
            self.is_acceptable_cholorin = True

    def check_humidity_level(self) -> None:
        result = GPIO.input(self.HUMIDITY_PIN)
        if 25.56 <= result <= 29.44:
            self.correct_humidity = True
        else:
            self.correct_humidity = False