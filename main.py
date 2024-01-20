try:
	import RPi.GPIO as GPIO
except ImportError:
	import mock.GPIO as GPIO
import time
from datetime import datetime
from EmbeddedPool import EmbeddedPool

embedded_system = EmbeddedPool("Info")


def loop():
	check_interval = 5  # seconds
	last_check_time = datetime.now()

	embedded_system.check_water_temperature()
	embedded_system.check_humidity_and_environment_temperature()

	while True:
		current_time = datetime.now()

		# Read sensors
		if (current_time - last_check_time).seconds >= check_interval:
			embedded_system.check_water_temperature()
			embedded_system.check_humidity_and_environment_temperature()
			last_check_time = current_time
		embedded_system.check_water_ph()
		embedded_system.check_orp()
		embedded_system.check_turbidity()
		embedded_system.check_environment_light_level()
		embedded_system.check_water_level()

		# Act
		embedded_system.control_windows()
		embedded_system.control_led()
		embedded_system.lcd_update()

		print("\n")


if __name__ == '__main__':
	try:
		embedded_system.turn_on_lcd_backlight()
		loop()
	except KeyboardInterrupt:
		embedded_system.turn_off()
