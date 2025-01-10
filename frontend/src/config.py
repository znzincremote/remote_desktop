import os
import sys
from configparser import ConfigParser

# Determine the base path
if getattr(sys, 'frozen', False):
    # If bundled with PyInstaller
    base_path = sys._MEIPASS
else:
    # When running as a normal script
    base_path = os.path.abspath(".")

# Construct the full path to the data file
env_file_path = os.path.join(base_path, 'config.ini')
config = ConfigParser()
config.read(env_file_path)

SIGNALING_SERVER = config['DEFAULT']['SIGNALING_SERVER']
RECONNECTION_DELAY = config['DEFAULT']['RECONNECTION_DELAY']
LIVE_URL = config['DEFAULT']['LIVE_URL']
API_KEY = config['DEFAULT']['API_KEY']