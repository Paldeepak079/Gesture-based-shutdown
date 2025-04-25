import os
import sys
import winshell
from win32com.client import Dispatch

def create_shortcut():
    try:
        desktop = winshell.desktop()
        path = os.path.join(desktop, "Smart Shutdown.lnk")
        
        # Get absolute paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        batch_path = os.path.join(current_dir, "launch.bat")
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = batch_path
        shortcut.WorkingDirectory = current_dir
        shortcut.WindowStyle = 1  # Normal window
        shortcut.save()
        
        print("Desktop shortcut created successfully!")
    except Exception as e:
        print(f"Error creating shortcut: {str(e)}")

if __name__ == "__main__":
    create_shortcut()