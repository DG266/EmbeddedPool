try:
	import RPi.GPIO as GPIO
except ImportError:
	import mock.GPIO as GPIO
import time
from EmbeddedPool import EmbeddedPool

embedded_system = EmbeddedPool()


def loop():
	while True:
		embedded_system.check_water_ph()
		# print(f"INFO: The water pH is equal to {embedded_system.water_ph}")
		embedded_system.lcd_print(f"pH = {embedded_system.water_ph:.2f}")
		time.sleep(1)


if __name__ == '__main__':
	try:
		embedded_system.turn_on_lcd_backlight()
		loop()
	except KeyboardInterrupt:
		embedded_system.lcd_clear()
		embedded_system.turn_off_lcd_backlight()
		GPIO.cleanup()
