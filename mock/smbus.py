class SMBus(object):
    def block_process_call(self, addr, cmd, vals=None):
        pass

    def close(self):
        pass

    def open(self, bus):
        pass

    def process_call(self, addr, cmd, val):
        pass

    def read_block_data(self, addr, cmd):
        pass

    def read_byte(self, addr):
        pass

    def read_byte_data(self, addr, cmd):
        pass

    def read_i2c_block_data(self, addr, cmd, len=32):
        pass

    def read_word_data(self, addr, cmd):
        pass

    def write_block_data(self, addr, cmd, vals=None):
        pass

    def write_byte(self, addr, val):
        pass

    def write_byte_data(self, addr, cmd, val):
        pass

    def write_i2c_block_data(self, addr, cmd, vals=None):
        pass

    def write_quick(self, addr):
        pass

    def write_word_data(self, addr, cmd, val):
        pass

    def __init__(self, bus=None):
        pass
