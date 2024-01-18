import glob
import time


# See https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing/software
class DS18B20:
	def __init__(self):
		# This will only work on Raspberry Pi (that's why I'm using this try block)
		try:
			base_dir = '/sys/bus/w1/devices/'
			device_folder = glob.glob(base_dir + '28*')[0]
			self.device_file = device_folder + '/w1_slave'
		except IndexError:
			pass
			# print("No DS18B20 found")

	def __read_temp_raw(self) -> list[str]:
		f = open(self.device_file, 'r')
		lines = f.readlines()
		f.close()
		return lines

	def read_temp(self) -> float:
		lines = self.__read_temp_raw()
		while lines[0].strip()[-3:] != 'YES':
			time.sleep(0.2)
			lines = self.__read_temp_raw()
		equals_pos = lines[1].find('t=')
		if equals_pos != -1:
			temp_string = lines[1][equals_pos + 2:]
			temp_c = float(temp_string) / 1000.0
			return temp_c
			# temp_f = temp_c * 9.0 / 5.0 + 32.0
			# return temp_c, temp_f
