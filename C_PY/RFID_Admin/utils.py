import os
import sys


def get_base_path() -> str:
    """
    Returns the base application path, handling both frozen (PyInstaller)
    and standard script execution environments.

    Returns:
        str: Absolute path to the application directory.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))
