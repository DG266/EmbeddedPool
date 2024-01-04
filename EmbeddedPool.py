from libs.DFRobot_ADS1115 import ADS1115
from mock import GPIO


class EmbeddedPool:
    TEMPERATURE_WATER_PIN=11
    TEMPERATURE_ENVIRONMENT_PIN=12
    def __init__(self):
        self.number = 7
        self.correct_water_temperature=False
        self.current_water_temperature=-1
        self.correct_environment_temperature=False
        self.current_environment_temperature=-1

        # ADC Setup
        self.ads1115 = ADS1115()
        self.ads1115.set_addr_ADS1115(0x48)
        self.ads1115.set_gain(0x00)

    def print_number(self):
        print(self.number)

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