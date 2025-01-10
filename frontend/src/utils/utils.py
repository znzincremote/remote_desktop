import cv2
import time
from aiortc import VideoStreamTrack
from av import VideoFrame
import numpy as np
from mss import mss
time_start = None

# -------------------- Tkinter keys strings to keyboard keys mapping -----------------------
KEYBOARD_KEYS_MAPPING = {
    'exclam': '!',
    'at': '@',
    'numbersign': '#',
    'dollar': '$',
    'percent': '%',
    'asciicircum': '^',
    'ampersand': '&',
    'asterisk': '*',
    'parenleft': '(',
    'parenright': ')',
    'underscore': '_',
    'plus': '+',
    'braceleft': '{',
    'braceright': '}',
    'colon': ':',
    'quotedbl': '"',
    'greater': '>',
    'question': '?',
    'less': '<',
    'bar': '|',
    'space': ' ',
    'backslash': '\\',
    'comma': ',',
    'period': '.',
    'semicolon': ';',
    'apostrophe': "'",
    'grave': '`',
    'tilde': '~',
    'bracketleft': '[',
    'bracketright': ']',
    'slash': '/',
    'equal': '=',
    'minus': '-',
    "Control_L": "ctrl",
    "Control_R": "ctrl",
    "Shift_L": "shift",
    "Shift_R": "shift",
    'Num_Lock': 'numlock',
    'Scroll_Lock': 'scrolllock',
    'Return': 'enter',
    'Escape': 'esc',
    'BackSpace': 'backspace',
    'Tab': 'tab',
    'Caps_Lock': 'capslock',
    'Delete': 'delete',
    'Insert': 'insert',
    'Up': 'up',
    'Down': 'down',
    'Left': 'left',
    'Right': 'right',
    'Home': 'home',
    'End': 'end',
    'Prior': 'pgup',
    'Next': 'pgdn',
    'Pause': 'pause',
    'Scroll_Lock': 'scrolllock',
    'Num_Lock': 'numlock',
    'F1': 'f1',
    'F2': 'f2',
    'F3': 'f3',
    'F4': 'f4',
    'F5': 'f5',
    'F6': 'f6',
    'F7': 'f7',
    'F8': 'f8',
    'F9': 'f9',
    'F10': 'f10',
    'F11': 'f11',
    'F12': 'f12',
    'Alt_L': 'alt',
    'Alt_R': 'alt',
    'Win_L': 'winleft',
    'Win_R': 'winright',
    'Menu': 'apps',
}


class InMemoryStore:
    def __init__(self):
        self.outgoing = []
        self.incoming = []

class ScreenShareTrack(VideoStreamTrack):
    def __init__(self, blank_screen = False):
        super().__init__()
        self.sct = mss()
        self.monitor = self.sct.monitors[1]
        self.black_screen = blank_screen

    async def recv(self):
        if self.black_screen:
            return await self.blank_frame()
        return await self.captured_frame()
    
    async def captured_frame(self):
        frame = self.sct.grab(self.monitor)
        img = cv2.cvtColor(np.array(frame), cv2.COLOR_BGRA2BGR)
        pts, time_base = await self.next_timestamp()
        video_frame = VideoFrame.from_ndarray(img, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame
    
    async def blank_frame(self):
        black_screen = np.zeros((self.monitor.height, self.monitor.width, 3), dtype=np.uint8)
        pts, time_base = await self.next_timestamp()
        video_frame = VideoFrame.from_ndarray(black_screen, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame