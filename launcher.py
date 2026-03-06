import webbrowser
import time
import sys
import os
import platform

URL = "https://farmacy-system.onrender.com"

def main():
    if platform.system() == "Windows":
        try:
            import win32print
        except ImportError:
            import subprocess
            subprocess.call([sys.executable, "-m", "pip", "install", "pywin32"])
    
    time.sleep(2)
    webbrowser.open(URL)

if __name__ == "__main__":
    main()