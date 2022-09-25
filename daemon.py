import sys
import time
import platform
import binascii
import configparser
import logging
from datetime import datetime
from serial import Serial
from serial.tools import list_ports
from stupidArtnet import StupidArtnet

# Logs
logging.basicConfig(
    format='%(asctime)s:%(levelname)s:%(message)s',
    # filename=f"logs/{'{:%Y-%m-%d}.log'.format(datetime.now())}",
    level=logging.DEBUG)

PLATFORM = platform.system()  # Darwin for OSX, Linux, Windows, MSYS* and CYGWIN*

# Config parser
config = configparser.ConfigParser()
config.read('dev_remote.ini')
CFG = {section_name: dict(config[section_name]) for section_name in config.sections()}

# Load keys config
actions = CFG.get('ACTIONS')

# Serial setup
serial_settings = CFG.get('SERIAL')
BAUDRATE = int(serial_settings.get('baudrate'))
PID = int(serial_settings.get('pid'))  # PID of the receiver
VID = int(serial_settings.get('vid'))  # VID of the receiver

# Artnet setup
artnet_settings = CFG.get('ARTNET')
target_ip = artnet_settings.get('ip')  # typically in 2.x or 10.x range
universe = int(artnet_settings.get('universe'))
packet_size = int(artnet_settings.get('packet_size'))  # it is not necessary to send whole universe
artnet = StupidArtnet(target_ip, universe, packet_size, 30, True, True)
artnet.start()

# Logs
logging.debug(f"Config: {CFG.get('NAME').get('name')}")
logging.debug("Trying to find receiver. Waiting to connect...")


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
            logging.debug('No remote found')

    def find_port(self):
        """
        :return: Founded port by PID and VID
        """
        if self.port:
            return self.port


def execute(action):
    """
    Handle packet and set ArtNet channel to 255
    :param action: Action num form config INI. This is UNIVERSE 2 ArtNet channel.
    :return: None
    """
    logging.debug(f"Action: {action}")
    artnet.set_single_value(int(action), 255)
    artnet.show()
    time.sleep(0.01)
    artnet.blackout()


def connect():
    while True:
        try:
            remote = Remote()
            port = remote.find_port()
            serial_port = Serial(port=port, baudrate=BAUDRATE)

            if port:
                logging.debug(f"Starting to receive a messages on port {serial_port.port}")
                read_messages(serial_port)
            else:
                time.sleep(1)

        except Exception as e:
            logging.debug(f"Retrying...")
            time.sleep(1)


def read_messages(serial_port):
    # Recieve in loop
    while True:
        try:
            data = serial_port.read(6)
            packet = binascii.hexlify(bytearray(data)).decode('ascii')
            # LOG PACKETS
            logging.debug(packet)
            if packet in actions.values():
                recv_action = [k for k, v in actions.items() if v == packet][0]
                execute(recv_action)
            else:
                # print(packet)
                pass
        except Exception as e:
            logging.debug(f"Unable to fetch a data from {serial_port.port}... \n"
                          f"Trying to find receiver. Waiting to connect...")
            serial_port.close()
            del serial_port
            connect()
            break


if __name__ == '__main__':
    # Start fetching data
    connect()
