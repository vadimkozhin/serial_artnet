import os
import sys
import tkinter as tk

import platform
from pprint import pprint
from serial.tools import list_ports
from serial.threaded import ReaderThread, Protocol
from serial import Serial
import binascii
import configparser
from stupidArtnet import StupidArtnet
import time

DEBUG = True

# Config parser
config = configparser.ConfigParser()
config.read('dev_remote.ini')
CFG = {section_name: dict(config[section_name]) for section_name in config.sections()}

# Artnet setup
artnet_settings = CFG.get('ARTNET')
target_ip = '255.255.255.255'  # typically in 2.x or 10.x range
universe = int(artnet_settings.get('universe'))
packet_size = int(artnet_settings.get('packet_size'))  # it is not necessary to send whole universe
artnet = StupidArtnet(target_ip, universe, packet_size, 30, True, True)
artnet.start()

# Serial setup
serial_settings = CFG.get('SERIAL')
BAUDRATE = int(serial_settings.get('baudrate'))
PID = int(serial_settings.get('pid'))  # PID of the receiver
VID = int(serial_settings.get('vid'))  # VID of the receiver

PLATFORM = platform.system()  # Darwin for OSX, Linux, Windows, MSYS* and CYGWIN*

class Remote:
    """
    Identify Remote
    """
    def __init__(self):
        self.port = self.find_address()

    def find_address(self):
        """
        Find serial port address by PID and VID
        :return: port address
        """
        all_ports = list(list_ports.comports())

        if all_ports:
            for coms in all_ports:
                # TODO: Handle multiple recievers
                if coms.pid == PID and coms.vid == VID:
                    return coms.device
        else:
            print('No remote found')

    def find_port(self):
        """
        :return: Founded port by PID and VID
        """
        return self.port

class TextOut(tk.Text):
    """
    Console output to Tk
    """
    def write(self, s):
        self.insert(tk.CURRENT, s)

    def flush(self):
        pass

class SerialReaderProtocolRaw():

    def connection_made(self, transport):
        """Called when reader thread is started"""
        pass

    def data_received(self, data):
        """Called with snippets received from the serial port"""
        packet = binascii.hexlify(bytearray(data)).decode('ascii')
        actions = CFG.get('ACTIONS')

        # DEBUG mode for catching remote codes
        if DEBUG:
            if len(packet) > 1 and packet != '\n':
                print(packet)
                pass
        # Find action by remote transmitted code
        if not DEBUG:
            if packet in actions.values():
                recv_action = [k for k, v in actions.items() if v == packet][0]
                execute(recv_action)


def execute(action):
    """
    Handle packet and set ArtNet channel to 255
    :param action: Action num form config INI. This is UNIVERSE 2 ArtNet channel.
    :return: None
    """
    print(action)
    artnet.set_single_value(int(action), 255)
    artnet.show()
    time.sleep(0.1)
    artnet.blackout()


def start_fetching():
    # Initiate serial port
    remote = Remote()
    port = remote.find_port()
    serial_port = Serial(port=port, baudrate=BAUDRATE)

    if serial_port.is_open:
        # Initiate ReaderThread
        reader = ReaderThread(serial_port, SerialReaderProtocolRaw)

        # Start reader
        reader.start()

        print(f"[{serial_port.port}] connected, ready to receive data...")
    else:
        print("-------------------")
        print("Can't open the port")
        print("-------------------")
        pprint(serial_port)


if __name__ == '__main__':
    app = tk.Tk()
    app.title(f"Remote to onPC2 - Config: {str(CFG.get('NAME').get('name'))}")

    # On mac Os Tk is black TODO: Do something about it
    # if PLATFORM != 'Darwin':
    #     text = TextOut(app)
    #     sys.stdout = text
    #     text.pack(expand=False)

    try:
        print(f'"{CFG.get("NAME").get("name")}" config loaded')
        start_fetching()
        app.mainloop()
        artnet.stop()

    except Exception as e:
        print(e)
        artnet.stop()
