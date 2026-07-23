"""Keep tkinter discoverable when build-time Tcl initialization is unavailable."""


def pre_find_module_path(hook_api):
    # The build explicitly collects Tcl/Tk data and binaries in the spec file.
    # Do not let PyInstaller's probe hide the pure-Python tkinter package.
    return None
