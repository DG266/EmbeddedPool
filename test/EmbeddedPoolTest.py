import unittest
from unittest.mock import patch

from EmbeddedPool import EmbeddedPool
from mock import GPIO


class MyTestCase(unittest.TestCase):
    def setUp(self)->None:
        self.es=EmbeddedPool()

    @patch.object(GPIO,"input")
    def test_water_temperature(self,mock_input):
        # Arrange
        mock_input.return_value=26

        # Act
        self.es.check_temperature()

        # Assert
        self.assertEqual(True,)

    @patch.object(GPIO, "input")
    def test_water_temperature_2(self, mock_input):
        # Arrange
        mock_input.return_value = 28

        # Act
        self.es.check_temperature()

        # Assert
        self.assertEqual(False, self.es.correct_temperature)