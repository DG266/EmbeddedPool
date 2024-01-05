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
		print(f"INFO: The water pH is equal to {embedded_system.water_ph}")
		time.sleep(1)


if __name__ == '__main__':
	try:
		loop()
	except KeyboardInterrupt:
		GPIO.cleanup()
