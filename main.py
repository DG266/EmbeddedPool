try:
	import RPi.GPIO as GPIO
except ImportError:
	import mock.GPIO as GPIO
import time
from EmbeddedPool import EmbeddedPool

embedded_system = EmbeddedPool("Info")


def loop():
	while True:
		# Read sensors
		embedded_system.check_water_temperature()
		embedded_system.check_humidity_and_environment_temperature()
		embedded_system.check_water_ph()
		embedded_system.check_orp()
		embedded_system.check_turbidity()
		embedded_system.check_environment_light_level()

		# Act
		embedded_system.control_windows()
		embedded_system.control_led()
		embedded_system.lcd_update()

		# time.sleep(0.25)
		print("\n")


if __name__ == '__main__':
	try:
		embedded_system.turn_on_lcd_backlight()
		loop()
	except KeyboardInterrupt:
		embedded_system.turn_off()
