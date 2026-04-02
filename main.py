"""Football Manager 26 - Accessible Edition
A fully text-based, screen reader friendly football management game.
"""

import sys
import os

# Ensure the game directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine_bridge import bridge
from ui import run


if __name__ == "__main__":
    status = bridge.get_status()
    print(f"Backend mode: {status.mode} - {status.message}")
    run()
