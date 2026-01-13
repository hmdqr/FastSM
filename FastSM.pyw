import application
from application import get_app
import platform
import sys
sys.dont_write_bytecode=True
if platform.system()!="Darwin":
	f=open("errors.log","a")
	sys.stderr=f
import shutil
import os
if os.path.exists(os.path.expandvars("%temp%\gen_py")):
	shutil.rmtree(os.path.expandvars("%temp%\gen_py"))
import wx
wx_app = wx.App(redirect=False)

import speak
from GUI import main
fastsm_app = get_app()
fastsm_app.load()
if fastsm_app.prefs.window_shown:
	main.window.Show()
else:
	speak.speak("Welcome to FastSM! Main window hidden.")
wx_app.MainLoop()
