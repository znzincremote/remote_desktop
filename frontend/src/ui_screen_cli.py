import os
import time
import json
import threading
import asyncio

import pyautogui, platform, requests, uuid

import tkinter as tk
from tkinter import messagebox
import cv2
from PIL import Image, ImageTk

from utils.webrtc_handler import WebRTCHandler
from utils.utils import KEYBOARD_KEYS_MAPPING
from utils.secure_files_data import encrypt_data, decrypt_data

from config import LIVE_URL, API_KEY

class App:
    def __init__(self, root):
        pyautogui.FAILSAFE = False
        self.root = root
        self.root.title("RemoteDesktop")
        try:
            icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"remote_desktop_icon.ico")
            if os.path.exists(icon_dir):
                self.root.iconbitmap(icon_dir)
        except:
            # TODO : Exception for LINUX system
            ...
        self.size = pyautogui.size()
        self.root.geometry(self.get_centered_geometry())
        self.root.wm_minsize(width=600, height=400)
        self.unique_id = self.get_unique_system_id()
        self.user_id = None
        self.access_token = self.get_or_set_access_token()
        self.user_is_authenticated = False
        self.open_window()

    def show_message(self, title, type, message):
        """ Show INFO or ERROR message on window """
        if type == "INFO":
            self.show_info_message(title=title, message=message)
        elif type == "ERROR":
            self.show_error_message(title=title, message=message)
    
    def show_info_message(self, message, title="Info"):
        """ Show info message in window """
        tk.messagebox.showinfo(
            title, 
            message
        )

    def show_error_message(self, message, title="Error"):
        """ Show error message in window """
        tk.messagebox.showerror(
            title,
            message if message else "An unexpected error occured. Please try again later !"
        )
    
    def initialize_webrtc_connection(self):
        """ Initialize webrtc connection """
        webrtc_conf = {
            "show_image": self.show_image, 
            "perform_event": self.perform_event, 
            "root": self.root,
            "placeholder": self.screen_placeholder,
            "bind_system_events": self.bind_system_events,
            "get_system_hardware_info": self.get_system_hardware_info,
            "process_websocket_status": self.process_websocket_status,
            "handle_connection_request": self.handle_connection_request,
            "perform_local_system_connection_successs": self.perform_local_system_connection_successs,
            "perform_remote_system_connection_successs": self.perform_remote_system_connection_successs,
            "close_accessing": self.close_accessing,
            "show_message": self.show_message,
            "handle_start_button": self.handle_start_button
        }
        self.webrtc_handler = WebRTCHandler(**webrtc_conf)
        threading.Thread(target=self.webrtc_handler.loop.run_forever, daemon=True).start()
        self.webrtc_handler.start_web_socket_connection()

    def initialize_system_events_handlers(self):
        self.button_mapping = {1: "left", 2: "middle", 3: "right"}  # Keyboard, Touchpad buttons mapping
        self.event_handlers = {
            "move": self.move_cursor,
            "button_click": self.perform_button_click,
            "button_release": self.perform_button_release,
            "scroll": self.perform_scroll,
            "key_press": self.perform_keypress,
            "key_release": self.perform_keyrelease,
            "clipboard_change": self.perform_clipboard_change
        }
        # Add os info
        self.is_linux, self.is_windows = platform.system() == "Linux", platform.system() == "Windows"
        # Move events processing
        self.last_move_time, self.move_threshold, self.move_timer = None, 0.5, None
        # Click events processing
        self.last_click_time, self.click_threshold = None, 1
        # Key Press events processing
        self.pressed_keys = []
        # Clipboard management
        self.root.clipboard_clear() # Clear both devices clipboard for not exchanging the clipboard which was present without doing events in our software. Clear when user open this software only.
        self.last_clipboard_content = ""
        self.remote_id = None
        asyncio.run_coroutine_threadsafe(self.start_clipboard_monitoring(), self.webrtc_handler.loop)

    def get_centered_geometry(self):
        """ Get the size to set the window in center for every system when the file is run """
        width, height = self.size[0]-400, self.size[1]-200
        screen_width, screen_height = self.size[0], self.size[1]
        x_offset = (screen_width - width) // 2
        y_offset = (screen_height - height) // 2
        return f"{width}x{height}+{x_offset}+{y_offset}"
    
    def bind_system_events(self, placeholder, root):
        """
        - Bind the events to the local system only.
        - Key press and, Key will only work on the whole root window of the GUI. 
        """
        placeholder.bind("<Configure>", self.on_resize)
        placeholder.bind("<Motion>", self.on_move)
        placeholder.bind("<ButtonPress>", self.on_button_click)
        placeholder.bind("<ButtonRelease>", self.on_button_release)
        placeholder.bind("<MouseWheel>", self.on_scroll)
        root.bind("<KeyPress>", self.on_keypress)
        root.bind("<KeyRelease>", self.on_keyrelease)
        placeholder.bind("<Button-4>", self.on_scroll)  # For Linux mouse events (backward scroll)
        placeholder.bind("<Button-5>", self.on_scroll)  # For Linux mouse events (forward scroll)

    def get_system_size(self):
        """Get the system's screen width and height."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        return screen_width, screen_height
    
    def open_window(self):
        if self.is_user_authenticated():
            self.main_page()
            self.set_unique_id()
            self.initialize_webrtc_connection()
            self.initialize_system_events_handlers()
        else:
            self.login_window(self.root)

    def is_user_authenticated(self):
        if self.access_token:
            try:
                response = requests.post(url=f"{LIVE_URL}/check-authentication/", headers={
                    "Authorization" : f"Bearer {self.access_token}",
                    "API-KEY": API_KEY
                })
                if response.ok:
                    res = response.json()
                    if res["status"] is True:
                        return True
            except Exception as e:
                ...
            self.show_info_message(message="Please login first to use the app!")
        return False

    def main_page(self):
        screen_width, screen_height = self.get_system_size()

        frame = tk.Frame(self.root)  # Match the background color
        frame.pack(fill="x", padx=10, pady=10)

        # Red Circle with an "X" sign (initial state)
        self.status_circle = tk.Canvas(frame, width=70, height=70)
        self.status_circle.create_oval(10, 10, 60, 60, fill="red")  # Red circle initially
        self.status_circle.create_text(35, 35, text="✘", font=("Arial", 30, "bold"), fill="white")
        self.status_circle.pack(side="left", padx=10)

        # Hover text for the green circle
        self.status_label = tk.Label(frame, text="Status: Connected", bg="lightyellow", relief="solid", padx=5, pady=3)
        self.status_label.pack_forget()

        # Bind hover events
        self.status_circle.bind("<Enter>", self.show_status)
        self.status_circle.bind("<Leave>", self.hide_status)
 
        target_id_entry_frame = tk.Frame(frame)
        target_id_entry_frame.pack(side="left", fill="x", expand=True, padx=10)

        self.target_id_entry = tk.Entry(target_id_entry_frame, font=("Arial", 14), relief="flat")
        self.target_id_entry.insert(0, "Enter a remote address")
        self.target_id_entry.bind("<FocusIn>", lambda e: self.target_id_entry.delete(0, tk.END))  # Clear placeholder on focus
        self.target_id_entry.pack(fill="x", ipady=8, padx=5)  # Internal padding for height

        # Step 10: Create the Start button (10% of width) with lighting effect
        button_frame = tk.Frame(frame, width=60, height=40, bg="#34495e")
        button_frame.pack(side="left", padx=5)
        button_frame.pack_propagate(False)

        self.start_button = tk.Button(button_frame, text="Start", fg="white", bg="#3498db",  activebackground="#2980b9", activeforeground="white", bd=0, relief="flat", command=self.validate_target_and_connect, font=("Arial", 12, "bold"), height=1, cursor="hand2")
        self.start_button.pack(fill="both", expand=True)

        # Add shadow to the input field and start button
        self.add_shadow(self.target_id_entry)
        self.add_shadow(self.start_button)

        system_details_frame = tk.Frame(self.root)
        system_details_frame.pack(pady=10)

        # "Your ID" Label and Entry
        tk.Label(system_details_frame, text="Your ID:", font=("Arial", 14)).pack(side="left")
        self.id_display = tk.Entry(system_details_frame, state='readonly', font=("Arial", 14), width=30)
        self.id_display.pack(side="left", padx=5)

        display_id_copy = tk.Button(system_details_frame, text="Copy", fg="white", bg="#3498db", activebackground="#2980b9", activeforeground="white", bd=0, relief="flat", command=self.copy_to_clipboard, font=("Arial", 12, "bold"), height=1, cursor="hand2")
        display_id_copy.pack(fill="both", expand=True)


        # Main frame for screen display
        main_frame = tk.Frame(self.root)
        main_frame.pack(expand=True, fill="both")
        self.w_width, self.w_height = main_frame.winfo_width(), main_frame.winfo_height()

        # Full-screen frame for screen display (100% width and height)
        self.screen_frame = tk.Frame(main_frame, bg="gray", width=screen_width, height=screen_height)
        self.screen_frame.pack(side="left", fill="both", expand=True)
        self.screen_frame.pack_propagate(False)
        self.screen_placeholder = tk.Label(self.screen_frame, text="Captured Screen Area", bg="black", fg="white")
        self.screen_placeholder.place(relwidth=1, relheight=1)

    def style_entry(self, entry):
        """Apply a modern, clean look to input fields."""
        entry.config(bg="#f0f0f0", relief="flat", font=("Arial", 12), bd=2)
        entry.config(highlightthickness=1, highlightbackground="lightgray", highlightcolor="#4CAF50")
        entry.bind("<FocusIn>", lambda e: entry.config(highlightbackground="#4CAF50"))
        entry.bind("<FocusOut>", lambda e: entry.config(highlightbackground="lightgray"))

    def login_window(self, root):
        for widget in root.winfo_children():
            widget.destroy()

        # Set the background color
        root.configure(bg="#f4f4f9")
        
        # Frame to hold the login form in the center
        frame = tk.Frame(root, bg="#ffffff", padx=40, pady=30, relief="solid", bd=2, borderwidth=5)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        title = tk.Label(frame, text="Login", font=("Arial", 18, "bold"), bg="#ffffff", fg="#333")
        title.grid(row=0, column=0, columnspan=2, pady=10)

        # Username Label and Entry
        tk.Label(frame, text="Username", font=("Arial", 12), bg="#ffffff", fg="#333").grid(row=1, column=0, pady=5, sticky="e")
        username_entry = tk.Entry(frame)
        self.style_entry(username_entry)
        username_entry.grid(row=1, column=1, pady=5)

        # Password Label and Entry
        tk.Label(frame, text="Password", font=("Arial", 12), bg="#ffffff", fg="#333").grid(row=2, column=0, pady=5, sticky="e")
        password_entry = tk.Entry(frame, show="*")
        self.style_entry(password_entry)
        password_entry.grid(row=2, column=1, pady=5)

        def login_action():
            username = username_entry.get()
            password = password_entry.get()
            # Check login (You can replace this with your API or database check)
            if not username or not password:
                messagebox.showerror("Login", "Invalid username or password")
            else:
                self.login_user({"username": username, "password": password})

        tk.Button(frame, text="Login", command=login_action, font=("Arial", 12, "bold"), bg="#4CAF50", fg="white", padx=20, pady=5, relief="flat", cursor="hand2").grid(row=3, column=0, columnspan=2, pady=20)

        # Register link

        register_link = tk.Label(frame, text="Don't have an account? Register", fg="blue", cursor="hand2", font=("Arial", 10, "underline"), bg="#ffffff")
        register_link.grid(row=4, column=0, columnspan=2)
        register_link.bind("<Button-1>", lambda e: self.go_to_register())

    def register_window(self, root):
        # Clear the window
        for widget in root.winfo_children():
            widget.destroy()

        # Set the background color
        root.configure(bg="#f4f4f9")
        
        # Frame to hold the register form in the center
        frame = tk.Frame(root, bg="#ffffff", padx=40, pady=30, relief="solid", bd=2, borderwidth=5)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        title = tk.Label(frame, text="Register", font=("Arial", 18, "bold"), bg="#ffffff", fg="#333")
        title.grid(row=0, column=0, columnspan=2, pady=10)

        # First Name Label and Entry
        tk.Label(frame, text="First Name", font=("Arial", 12), bg="#ffffff", fg="#333").grid(row=1, column=0, pady=5, sticky="e")
        first_name_entry = tk.Entry(frame)
        self.style_entry(first_name_entry)
        first_name_entry.grid(row=1, column=1, pady=5)

        # Last Name Label and Entry
        tk.Label(frame, text="Last Name", font=("Arial", 12), bg="#ffffff", fg="#333").grid(row=2, column=0, pady=5, sticky="e")
        last_name_entry = tk.Entry(frame)
        self.style_entry(last_name_entry)
        last_name_entry.grid(row=2, column=1, pady=5)

        # Username Label and Entry
        tk.Label(frame, text="Username", font=("Arial", 12), bg="#ffffff", fg="#333").grid(row=3, column=0, pady=5, sticky="e")
        username_entry = tk.Entry(frame)
        self.style_entry(username_entry)
        username_entry.grid(row=3, column=1, pady=5)

        # Email Label and Entry
        tk.Label(frame, text="Email", font=("Arial", 12), bg="#ffffff", fg="#333").grid(row=4, column=0, pady=5, sticky="e")
        email_entry = tk.Entry(frame)
        self.style_entry(email_entry)
        email_entry.grid(row=4, column=1, pady=5)

        # Password Label and Entry
        tk.Label(frame, text="Password", font=("Arial", 12), bg="#ffffff", fg="#333").grid(row=5, column=0, pady=5, sticky="e")
        password_entry = tk.Entry(frame, show="*")
        self.style_entry(password_entry)
        password_entry.grid(row=5, column=1, pady=5)

        def register_action():
            first_name = first_name_entry.get()
            last_name = last_name_entry.get()
            username = username_entry.get()
            email = email_entry.get()
            password = password_entry.get()
            # Perform register logic (You can replace this with your API or database)
            if not (first_name and last_name and username and email and password):
                messagebox.showerror("Register", "All fields are required")
            else:
                self.register_user({"first_name": first_name, "last_name": last_name, "username": username, "email": email, "password": password})

        tk.Button(frame, text="Register", command=register_action, font=("Arial", 12, "bold"), bg="#4CAF50", fg="white", padx=20, pady=5, relief="flat", cursor="hand2").grid(row=6, column=0, columnspan=2, pady=20)

        # Link to go to login page
        login_link = tk.Label(frame, text="Already have an account? Login", fg="blue", cursor="hand2", font=("Arial", 10, "underline"), bg="#ffffff")
        login_link.grid(row=7, column=0, columnspan=2)
        login_link.bind("<Button-1>", lambda e: self.go_to_login())

    def go_to_login(self):
        self.login_window(self.root)

    def go_to_register(self):
        self.register_window(self.root)

    def copy_to_clipboard(self):
        text_to_copy = self.id_display.get()
        self.root.clipboard_clear()
        self.root.clipboard_append(text_to_copy)
        self.root.update()

    def add_shadow(self, widget, bg="#2c3e50", color="#2c3e50"):
        widget.config(highlightthickness=2, highlightbackground=bg, highlightcolor=color)

    def show_status(self, event):
        # Show the status label near the green circle
        self.status_label.place(x=event.x + 70, y=event.y)

    def hide_status(self, event):
        # Hide the status label when mouse leaves the circle
        self.status_label.place_forget()

    def get_system_hardware_info(self):
        """ Get system info """
        return {
            "operating_system": platform.system(),
            "unique_system_id": self.unique_id
        }

    def get_unique_system_id(self):
        file_path = "UserAppData.json"
        # Check if the file exists
        if os.path.exists(file_path):
            # Read the UUID from the file
            with open(file_path, "r") as json_file:
                try:
                    encrypted_data = json.load(json_file)
                    if encrypted_data:
                        decrypted_data = decrypt_data(encrypted_data['a1'], encrypted_data['a2'])
                        if decrypted_data:
                            unique_id = decrypted_data.get("unique_id")
                            if unique_id : return unique_id
                except json.JSONDecodeError:
                    ...
        # Generate a new UUID and save it to the file if unique_id key is not present in the file
        unique_id = str(uuid.uuid4())  # Generate a new UUID
        data = dict()
        with open(file_path, "r") as json_file:
            try:
                data = json.load(json_file)
            except json.JSONDecodeError:
                ...
        data["unique_id"] = unique_id
        encrypted_result = encrypt_data(data)
        if encrypted_result:
            try:
                with open(file_path, "w") as json_file:
                    json.dump(encrypted_result, json_file)  # Save the encrypted UUID
            except (json.JSONDecodeError, IOError) as e:
                ...
        return unique_id

    def get_or_set_access_token(self, token=None):
        file_path = "UserAppData.json"
        if token is None:
            if os.path.exists(file_path):
                try:
                    # Read the encrypted data from the file
                    with open(file_path, "r") as json_file:
                        encrypted_data = json.load(json_file)
                        if encrypted_data:
                            decrypted_data = decrypt_data(encrypted_data['a1'], encrypted_data['a2'])
                            if decrypted_data:
                                return decrypted_data.get("t", "")
                except (json.JSONDecodeError, KeyError) as e:
                    ...
        else:
            # save access token to the file
            data = {"unique_id": self.unique_id, "t": token}
            encrypted_result = encrypt_data(data)
            if encrypted_result:
                try:
                    with open(file_path, "w") as json_file:
                        json.dump(encrypted_result, json_file, indent=4)
                except (json.JSONDecodeError, IOError) as e:
                    ...
        return ""

    def register_user(self, payload: dict):
        url = f"{LIVE_URL}/register"
        response = requests.post(url, json=payload, headers={"API-KEY": API_KEY})
        res = response.json()
        if res.get("status"):
            self.show_info_message(message=res.get("message"))
            self.login_window(self.root)
        else:
            self.show_error_message(message=res.get("message"))

    def login_user(self, payload):
        """ Get access token for user authentication """
        url = f"{LIVE_URL}/login"
        response = requests.post(url, json=payload, headers={"API-KEY": API_KEY})
        res = response.json()
        if res.get("status"):
            self.show_info_message(message=res.get("message"))
            self.access_token = res.get("access_token")
            self.get_or_set_access_token(token=res.get("access_token"))
            self.user_id = res.get("user_id")
            self.user_is_authenticated = True
            self.open_window()
        else:
            self.show_error_message(message=res.get("message"))

    def set_unique_id(self):
        try:
            if not self.access_token:
                self.show_info_message(message="Please login to start application.")
                self.user_is_authenticated = False
                return
            payload = self.get_system_hardware_info()
            response = requests.post(
                url=f"{LIVE_URL}/system-info",
                json=payload, 
                headers={
                    'API-KEY': API_KEY,
                    'Content-Type': 'application/json',
                    'Authorization' : f'Bearer {self.access_token}'
                }
            )
            res = response.json()
            if not response.ok:
                if response.status_code == 401:
                    self.show_info_message(message="Please login to start application.")
                    self.user_is_authenticated = False
                    return
                self.show_error_message(message=f"Failed to set system ID. Server returned: {response.status_code}")
                return
            self.update_remote_id(res["remote_id"])
        except Exception as e:
            self.show_error_message(message=f"Failed to connect to server: {str(e)}")

    def show_image(self, img):
        # Schedule image update on the main thread
        self.root.after(0, self._show_image, img)

    def _show_image(self, img):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (self.w_width, self.w_height), interpolation=cv2.INTER_LANCZOS4)
        pil_image = Image.fromarray(img_resized)
        tk_image = ImageTk.PhotoImage(image=pil_image)
        self.screen_placeholder.config(image=tk_image)
        self.screen_placeholder.image = tk_image

    def connect(self):
        self.webrtc_handler.target_client_id = int(self.target_id_entry.get())
        self.webrtc_handler.start_webrtc_connection()
        self.start_button.config(state="disabled", text="⏳", cursor="watch")

    def handle_start_button(self, state="normal", text="", cursor="hand1"):
        """ Manage start button with state, text and cursor """
        self.start_button.config(state=state, text=text, cursor=cursor)

    def perform_local_system_connection_successs(self):
        self.start_button.config(state="normal", text="Stop", cursor="hand2", bg="#FF0000", fg="white", activebackground="#FF4C4C", activeforeground="white", relief="solid", command=lambda: self.stop_accessing("local_system"))

    def perform_remote_system_connection_successs(self):
        self.start_button.config(state="normal", text="Stop", cursor="hand2", bg="#FF0000", fg="white", activebackground="#FF4C4C", activeforeground="white", relief="solid", command=lambda: self.stop_accessing("remote_system"))

    def stop_accessing(self, system_info):
        message = json.dumps({
            "connectivity": False,
            "type": "force_close_connection",
            "ping" if system_info == "local_system" else "pong": f"Connection closed by {system_info}"
        })
        asyncio.run_coroutine_threadsafe(self.webrtc_handler.chat_channel_send(message), self.webrtc_handler.loop)
        self.close_accessing(message="Connection closed successfully")

    def close_accessing(self, message):
        self.webrtc_handler.close_webrtc_connection(), self.webrtc_handler.loop
        self.show_info_message(message=message)

    def validate_target_and_connect(self):
        try:
            target_id_entry = self.target_id_entry.get()
            if len(target_id_entry) == 10 and int(target_id_entry):
                # If length of target id is 10 and is a valid number
                if self.id_display.get() == target_id_entry:
                    return self.show_error_message(message="Local and remote address cannot be the same.")
                return self.connect()
        except ValueError:
            ...
        self.show_error_message(message="Please enter a valid remote id")

    def on_resize(self, event):
        " Handle the resize of the screen shared image|video|display "
        self.w_width, self.w_height = event.width, event.height

    def on_move(self, event):
        """ Local system move event handler """
        current_time = time.time()
        if self.move_timer:
            self.root.after_cancel(self.move_timer)
        self.move_timer = self.root.after(int(self.move_threshold * 1000), self.process_move_event, event.x, event.y)
        self.last_move_time = current_time  # Update last move time

    def process_move_event(self, x, y):
        """Process the move event after debounce time has passed"""
        # Now send the movement event to the remote system
        event_data = {
            'type': 'move',
            'x': x,
            'y': y
        }
        self.root.after(0, self.system_event, event_data)

    def on_button_click(self, event):
        """ Local system button click (Mouse, Touchpad) event handler """
        current_time = time.time()  # Get the current time
        if self.last_click_time and (current_time - self.last_click_time) <= self.click_threshold:
            self.click_count += 1
        else:
            self.click_count = 1  # Reset if too much time passed between clicks

        event_data = {
            'type': 'button_click',
            'clicks': self.click_count,
            'button': self.button_mapping.get(event.num),
            'x': event.x,
            'y': event.y
        }
        self.last_click_time = current_time
        self.click_count = 0
        self.root.after(0, self.system_event, event_data)

    def on_button_release(self, event):
        """ Local system button release event handler """
        event_data = {
            "type": "button_release",
            "button": self.button_mapping.get(event.num, ""),
            "x": event.x,
            "y": event.y,
        }
        self.root.after(0, self.system_event, event_data)

    def on_scroll(self, event):
        """ Local system scroll (top, bottom) event handler """
        delta = 0
        if self.is_windows:
            event_delta = event.delta
            delta = int((event_delta//event_delta)) if event_delta>0 else int(event_delta//(-event_delta))
        elif self.is_linux:
            if event.num == 4:  # Scroll up
                delta = 1
            elif event.num == 5:  # Scroll down
                delta = -1
            delta = delta*120
        
        event_data = {
            'type': 'scroll',
            'delta': delta,
            'x': event.x,
            'y': event.y
        }
        self.root.after(0, self.system_event, event_data)

    def on_keypress(self, event):
        """ Local system keypress (keyboard keys) event handler """
        event_data = {
            'type': 'key_press',
            'key': event.keysym
        }
        self.root.after(0, self.system_event, event_data)

    def on_keyrelease(self, event):
        """ Local system key release (keyboard keys) handler """
        event_data = {
            "type": "key_release",
            "key": event.keysym,
        }
        self.root.after(0, self.system_event, event_data)

    async def start_clipboard_monitoring(self):
        self.monitor_clipboard()

    def monitor_clipboard(self):
        """ Continuously monitor the clipboard for changes """
        try:
            current_clipboard = self.root.clipboard_get()
            if current_clipboard != self.last_clipboard_content:
                self.last_clipboard_content = current_clipboard
                self.on_clipboard_change(current_clipboard)
        except tk.TclError:
            # Clipboard might be empty; skip any errors
            pass
        finally:
            # Check again after a short delay
            self.root.after(500, self.monitor_clipboard)

    def on_clipboard_change(self, current_clipboard):
        event_data = {
            "type": "clipboard_change",
            "value": current_clipboard
        }
        self.root.after(0, self.system_event, event_data)

    def system_event(self, event_data: dict):
        """ 
        - Handler for all the local, remote system events.
        - This function will send the event data to the channel.
        """
        try:
            # Skip for those events which does not have co-ordinates
            x, y, sys_info = event_data.get("x"),  event_data.get("y"), self.webrtc_handler.system_info
            if x and y:
                event_data["x"], event_data["y"] = int((x / self.screen_placeholder.winfo_width()) * self.webrtc_handler.remote_system_width), int((y / self.screen_placeholder.winfo_height()) * self.webrtc_handler.remote_system_height)

            message = json.dumps({
                "connectivity": True,
                "ping" if sys_info == "local_system" else "pong": {
                    "system_event": event_data,
                    "system_info": sys_info
                }
            })

            asyncio.run_coroutine_threadsafe(self.webrtc_handler.chat_channel_send(message), self.webrtc_handler.loop)
        except AttributeError:
            pass
        except Exception as e:
            pass

    def perform_event(self, event : dict):
        """
        - Perform event on remote system.
        - This method is used by WebRTCHandler class in answer.
        """
        try:
            if system_event := event.get("system_event"):
                self.event_handlers.get(system_event["type"])(system_event)
        except Exception as e:
            pass

    def move_cursor(self, event : dict):
        """ Perform move event on remote system """
        x, y = event["x"], event["y"]
        pyautogui.moveTo(x=x, y=y, duration=0.1)

    def perform_button_click(self, event: dict):
        """
        - Perform click event on remote system.
        - Do clicks if clicks are greater than one
        - Hold the click button if clicks are greater than 1
        """
        if event["clicks"] > 1:
            pyautogui.click(x=event["x"], y=event["y"], button=event["button"], clicks=event["clicks"])
        else:
            pyautogui.mouseDown(x=event["x"], y=event["y"], button=event["button"])

    def perform_button_release(self, event : dict):
        """ 
        - Perform button release on remote system.
        - Release the mouse/touchpad button for remote system.
        """
        pyautogui.mouseUp(x=event["x"], y=event["y"], button=event["button"])

    def perform_scroll(self, event : dict):
        """ Perform scroll event on remote system """
        delta = event["delta"]
        pyautogui.scroll(delta)


    def perform_keypress(self, event : dict):
        """ Perform key press event on remote system """
        key = event["key"]
        self.press_keys(key)


    def press_keys(self, key : str):
        """ 
        - Handle keypressing by detecting keys
        - If the keys are ctrl, shift, alt , Hold the keys.
        - If ctrl is pressed first and not released then call hotkeys function with pressed keys
        - If the keys are normal typing keys then press them. 
        """
        key = KEYBOARD_KEYS_MAPPING.get(key, key)
        self.pressed_keys.append(key) if key not in self.pressed_keys else ... # Only add in pressed keys list if key not present

        if key in ["ctrl", "shift", "alt"]:
            pyautogui.keyDown(key=key)
        elif self.pressed_keys[0] == "ctrl":
            pressed_keys = [key.lower() for key in self.pressed_keys]
            pyautogui.hotkey(*pressed_keys)
        else:
            pyautogui.press(key)

    def perform_keyrelease(self, event : dict):
        """ Perform key release event on remote system """
        key = KEYBOARD_KEYS_MAPPING.get(event["key"], event["key"])
        pyautogui.keyUp(key)
        # Remove key from pressed key when released
        try:
            self.pressed_keys.remove(key)
        except Exception as e:
            pass

    def perform_clipboard_change(self, event : dict):
        """ Perform clipboard change event on any system """
        self.root.clipboard_clear()
        self.root.clipboard_append(event["value"]) 
        self.root.update()

    def update_remote_id(self, remote_id):
        """Update the display of the remote ID"""
        self.remote_id = remote_id
        self.id_display.config(state='normal')
        self.id_display.delete(0, tk.END)
        self.id_display.insert(0, remote_id)
        self.id_display.config(state='readonly')

    def process_websocket_status(self, status: bool):
        """Process WebSocket status and update circle color and text accordingly"""
        self.status_circle.delete("all")  # Clear the current content of the circle
        if status:
            self.status_circle.create_oval(10, 10, 60, 60, fill="green")
            self.status_circle.create_text(35, 35, text="✔", font=("Arial", 30, "bold"), fill="white")
        else:
            self.status_circle.create_oval(10, 10, 60, 60, fill="red")
            self.status_circle.create_text(35, 35, text="✘", font=("Arial", 30, "bold"), fill="white")

    def handle_connection_request(self):
        """ Show accept connection accept/cancel modal in remote device"""
        modal_window = tk.Toplevel(self.root)
        modal_window.title("Accept Connection")
        modal_window.geometry("400x200")
        modal_window.resizable(False, False)
        modal_window.attributes('-topmost', True)  # Ensure modal stays on top

        # Set a modern, subtle background color for the modal
        modal_window.config(bg="#f0f0f0")

        # Create the message label with stylish font
        label = tk.Label(modal_window, text=f"Accept connection from remote peer ?", font=("Helvetica", 14), bg="#f0f0f0", fg="#333")
        label.pack(pady=30)

        # Create the button frame with padding and better alignment
        button_frame = tk.Frame(modal_window, bg="#f0f0f0")
        button_frame.pack(pady=20)

        # Stylish Accept button
        accept_button = tk.Button(button_frame, text="Accept", command=lambda: self.accept_local_system_offer(modal_window), width=15, bg="#1a7305", fg="white", relief="flat", font=("Arial", 12), bd=0, pady=8, cursor="hand2")
        accept_button.pack(side="left", padx=20)

        # Stylish Cancel button
        cancel_button = tk.Button(button_frame, text="Cancel", command=lambda: self.reject_local_system_offer(modal_window), width=15, bg="#ff0000", fg="white", relief="flat", font=("Arial", 12), bd=0, pady=8, cursor="hand2")
        cancel_button.pack(side="left", padx=20)

        # Center the modal on the parent window
        window_width = 400
        window_height = 200
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        position_top = (screen_height // 2) - (window_height // 2)
        position_right = (screen_width // 2) - (window_width // 2)
        modal_window.geometry(f"{window_width}x{window_height}+{position_right}+{position_top}")

        # Wait while the user does not accept the connection
        while True:
            if self.webrtc_handler.remote_system_answer_status != "pending":
                return True if self.webrtc_handler.remote_system_answer_status == "accepted" else False
            time.sleep(1)

    def accept_local_system_offer(self, modal_window):
        self.webrtc_handler.remote_system_answer_status = "accepted"
        modal_window.destroy()

    def reject_local_system_offer(self, modal_window):
        self.webrtc_handler.remote_system_answer_status = "rejected"
        modal_window.destroy()


def run_app():
    root = tk.Tk()
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    run_app()
