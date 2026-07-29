import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
# TODO: This modifies sys.path and should be replaced with proper packaging.

from main import app
