import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../bin')))

from ltbox.device import DeviceController

class TestDeviceOutputParsing:

    def test_parse_adb_devices_online(self):
        output = """List of devices attached
12345678    device
"""
        pass

    def test_parse_adb_unauthorized(self):
        output = """List of devices attached
12345678    unauthorized
"""
        pass

    def test_parse_fastboot_getvar(self):
        output = """(bootloader) current-slot:a
(bootloader) has-slot:boot:yes
(bootloader) slot-count:2
all: Done!!
"""
        pass
