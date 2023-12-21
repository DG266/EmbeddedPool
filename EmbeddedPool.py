from mock import GPIO


class EmbeddedPool:
    TEMPERATURE_WATER_PIN=11
    def __init__(self):
        self.number = 7
        self.correct_temperature=False

    def print_number(self):
        print(self.number)

    def check_temperature(self) -> None:
        result=GPIO.input(self.TEMPERATURE_WATER_PIN)
        if 25.5 <= result <= 27.7:
            self.correct_temperature=True
        else:
            self.correct_temperature=False

