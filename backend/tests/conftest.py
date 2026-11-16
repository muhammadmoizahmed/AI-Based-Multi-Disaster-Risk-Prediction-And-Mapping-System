import os
import sys

import os

os.environ.setdefault("EARTHQUAKE_STORE_PREDICTIONS", "false")
os.environ.setdefault("FLOOD_LSTM_STORE_PREDICTIONS", "false")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
