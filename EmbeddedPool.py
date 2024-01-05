try:
    import RPi.GPIO as GPIO
except ImportError:
    import mock.GPIO as GPIO
from libs.DFRobot_ADS1115 import ADS1115
from libs.DFRobot_PH import DFRobot_PH


class EmbeddedPool:
    # Raspberry BCM GPIO pins
    TEMPERATURE_WATER_PIN = 11
    TEMPERATURE_ENVIRONMENT_PIN = 12

    # ADC pins
    PH_SENSOR_PIN = 0

    def __init__(self):
        # Use Broadcom GPIO numbers
        GPIO.setmode(GPIO.BCM)

        # ADC setup
        self.ads1115 = ADS1115()
        self.ads1115.set_addr_ADS1115(0x48)
        self.ads1115.set_gain(0x00)

        # pH sensor setup
        self.ph_helper = DFRobot_PH()

        # Instance variables
        self.correct_water_temperature = False
        self.current_water_temperature = -1
        self.correct_environment_temperature = False
        self.current_environment_temperature = -1
        self.is_acceptable_ph = False
        self.water_ph = -1

    def check_water_temperature(self) -> None:
        result=GPIO.input(self.TEMPERATURE_WATER_PIN)
        if 25.5 <= result <= 27.7:
            self.correct_water_temperature=True
        else:
            self.correct_water_temperature=False

    def check_environment_temperature(self) -> None:
        result=GPIO.input(self.TEMPERATURE_ENVIRONMENT_PIN)
        if result > (self.current_water_temperature + 2):
            # Environment temperature is too high
            self.correct_environment_temperature=False
        elif result <= (self.current_water_temperature + 2):
            self.correct_environment_temperature=True

    def check_water_ph(self) -> None:
        # Read the voltage from the ADC (where the pH probe is connected)
        voltage = self.ads1115.read_voltage(self.PH_SENSOR_PIN)['r']
        # Use the DFRobot pH library to convert voltage to pH
        result = self.ph_helper.read_PH(voltage, None)

        if 7.2 < result < 7.6:
            self.is_acceptable_ph = True
        else:
            self.is_acceptable_ph = False

        # Update the pH value in the instance variable
        self.water_ph = result
