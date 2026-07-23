"""Point frozen tkinter at the explicitly bundled Tcl/Tk libraries."""

import os
import sys
from pathlib import Path


bundle_root = Path(sys._MEIPASS)
os.environ["TCL_LIBRARY"] = str(bundle_root / "_tcl_data")
os.environ["TK_LIBRARY"] = str(bundle_root / "_tk_data")
