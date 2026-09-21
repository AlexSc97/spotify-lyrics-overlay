import ctypes
from ctypes import wintypes
import time
from PyQt6.QtCore import QThread, pyqtSignal

class HotkeyListener(QThread):
    hotkey_triggered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def stop(self):
        self._running = False
        self.wait()

    def run(self):
        user32 = ctypes.windll.user32
        MOD_CONTROL = 0x0002
        MOD_ALT = 0x0001
        MOD_NOREPEAT = 0x4000
        VK_F8 = 0x77
        VK_L = 0x4C

        HOTKEY_ID_F8 = 101
        HOTKEY_ID_CTRL_ALT_L = 102

        # Registrar F8 y Ctrl+Alt+L
        user32.RegisterHotKey(None, HOTKEY_ID_F8, MOD_NOREPEAT, VK_F8)
        user32.RegisterHotKey(None, HOTKEY_ID_CTRL_ALT_L, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_L)

        msg = wintypes.MSG()
        try:
            while self._running:
                if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1): # PM_REMOVE = 1
                    if msg.message == 0x0312:  # WM_HOTKEY
                        self.hotkey_triggered.emit()
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                time.sleep(0.02)
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID_F8)
            user32.UnregisterHotKey(None, HOTKEY_ID_CTRL_ALT_L)
