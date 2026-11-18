"""Where things live: bundled read-only resources vs. the user's data next to the .exe"""
import os, sys
FROZEN = getattr(sys, "frozen", False)
RES = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))          # templates, static files
DATA = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))  # config, db, generated
