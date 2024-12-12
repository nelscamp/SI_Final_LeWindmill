import customtkinter as ctk
import tkinter as tk
import time
from threading import Thread, Event
import queue
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD
import os
import sys

GPIO.setwarnings(False)

# Motor control system class
class MotorControlSystem:
    def __init__(self, log_queue):
        # Define GPIO pins for Windmill Stepper Motor (DRV8833)
        self.WM_AIN1 = 17  # Pin for Coil A1
        self.WM_AIN2 = 22  # Pin for Coil A2
        self.WM_BIN1 = 27  # Pin for Coil B1
        self.WM_BIN2 = 23  # Pin for Coil B2
        # Define GPIO pins for Music Box Stepper Motor (DRV8833)
        self.MB_AIN1 = 24  # Pin for Coil A1
        self.MB_AIN2 = 25  # Pin for Coil A2
        self.MB_BIN1 = 8   # Pin for Coil B1
        self.MB_BIN2 = 7   # Pin for Coil B2
        # Stepper motor parameters
        self.STEPS_PER_REV = 200  # NEMA17 typically has 200 steps per revolution
        self.FULL_STEP_SEQUENCE = [
            [1, 0, 1, 0],  # Step 1
            [0, 1, 1, 0],  # Step 2
            [0, 1, 0, 1],  # Step 3
            [1, 0, 0, 1],  # Step 4
        ]  # Stepper motor clockwise steps
        # Note: Windmill motor can reverse direction; Music box motor only moves forward
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.WM_AIN1, GPIO.OUT)
        GPIO.setup(self.WM_AIN2, GPIO.OUT)
        GPIO.setup(self.WM_BIN1, GPIO.OUT)
        GPIO.setup(self.WM_BIN2, GPIO.OUT)
        GPIO.setup(self.MB_AIN1, GPIO.OUT)
        GPIO.setup(self.MB_AIN2, GPIO.OUT)
        GPIO.setup(self.MB_BIN1, GPIO.OUT)
        GPIO.setup(self.MB_BIN2, GPIO.OUT)
        # Initialize all pins to LOW
        self.set_motor_pins([0, 0, 0, 0], motor='windmill')
        self.set_motor_pins([0, 0, 0, 0], motor='musicbox')
        # Motor control variables
        self.motor_speed = 50  # Initial speed percentage
        self.motor_running = False  # Start as not running
        self.motor_paused = False  # Start as paused
        self.direction = 'clockwise'  # 'clockwise' or 'counterclockwise'
        # Thread control
        self.stop_event = Event()
        self.pause_event = Event()
        # Log queue for GUI
        self.log_queue = log_queue
        # Music Box speed factor relative to Windmill speed
        self.music_speed_factor = 4  # Adjust as needed
        # Initialize threads
        self.windmill_thread = None
        self.musicbox_thread = None
    def set_motor_pins(self, state, motor='windmill'):
        if motor == 'windmill':
            GPIO.output(self.WM_AIN1, state[0])
            GPIO.output(self.WM_AIN2, state[1])
            GPIO.output(self.WM_BIN1, state[2])
            GPIO.output(self.WM_BIN2, state[3])
        elif motor == 'musicbox':
            GPIO.output(self.MB_AIN1, state[0])
            GPIO.output(self.MB_AIN2, state[1])
            GPIO.output(self.MB_BIN1, state[2])
            GPIO.output(self.MB_BIN2, state[3])
    def calculate_windmill_delay(self):
        MAX_RPM = 60  # Maximum RPM
        rpm = self.motor_speed / 100.0 * MAX_RPM
        steps_per_second = rpm * self.STEPS_PER_REV / 60.0
        delay = 1.0 / steps_per_second if steps_per_second > 0 else 0.1
        return delay
    def calculate_musicbox_delay(self):
        # Music box RPM is proportional to windmill RPM
        MAX_RPM = 60  # Maximum RPM
        music_rpm = self.motor_speed / 100.0 * MAX_RPM * self.music_speed_factor
        steps_per_second = music_rpm * self.STEPS_PER_REV / 60.0
        delay = 1.0 / steps_per_second if steps_per_second > 0 else 0.1
        return delay
    def start_motor(self):
        if not self.motor_running:
            self.stop_event.clear()
            self.pause_event.clear()
            self.motor_paused = False
            # Start Windmill Motor Thread
            self.windmill_thread = Thread(target=self.run_windmill_motor)
            self.windmill_thread.start()
            # Start Music Box Motor Thread
            self.musicbox_thread = Thread(target=self.run_musicbox_motor)
            self.musicbox_thread.start()
            self.motor_running = True
            self.log_queue.put("Windmill and Music Box started.")
    def run_windmill_motor(self):
        step_index = 0
        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(0.1)
                continue
            # Determine the sequence index based on direction
            if self.direction == 'clockwise':
                sequence_index = step_index % len(self.FULL_STEP_SEQUENCE)
            else:
                sequence_index = (-step_index) % len(self.FULL_STEP_SEQUENCE)
            self.set_motor_pins(self.FULL_STEP_SEQUENCE[sequence_index], motor='windmill')
            step_index += 1
            delay = self.calculate_windmill_delay()
            time.sleep(delay)
        # Stop Windmill Motor
        self.set_motor_pins([0, 0, 0, 0], motor='windmill')
    def run_musicbox_motor(self):
        step_index = 0
        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(0.1)
                continue
            # Music Box motor only steps forward
            sequence_index = -step_index % len(self.FULL_STEP_SEQUENCE)
            self.set_motor_pins(self.FULL_STEP_SEQUENCE[sequence_index], motor='musicbox')
            step_index += 1
            delay = self.calculate_musicbox_delay()
            time.sleep(delay)
        # Stop Music Box Motor
        self.set_motor_pins([0, 0, 0, 0], motor='musicbox')
    def stop_motor(self):
        if self.motor_running:
            self.stop_event.set()
            self.pause_event.clear()
            if self.windmill_thread is not None:
                self.windmill_thread.join()
            if self.musicbox_thread is not None:
                self.musicbox_thread.join()
            self.motor_running = False
            self.log_queue.put("Windmill and Music Box stopped.")
    def toggle_pause(self):
        if self.motor_running:
            if self.pause_event.is_set():
                self.pause_event.clear()
                self.motor_paused = False
                self.log_queue.put("Windmill and Music Box resumed.")
            else:
                self.pause_event.set()
                self.motor_paused = True
                self.log_queue.put("Windmill and Music Box paused.")
    def set_motor_speed(self, speed):
        self.motor_speed = float(speed)
    def toggle_direction(self):
        self.direction = 'counterclockwise' if self.direction == 'clockwise' else 'clockwise'
        self.log_queue.put(f"Windmill direction set to {self.direction}")
    def get_direction_text(self):
        return self.direction.capitalize()
    def get_status_text(self):
        if self.motor_running:
            return "Paused" if self.pause_event.is_set() else "Running"
        else:
            return "Stopped"
    def calculate_rpm(self):
        MAX_RPM = 60
        return int(self.motor_speed / 100.0 * MAX_RPM)
    def cleanup(self):
        GPIO.cleanup()
# GUI class
class WindmillControlGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Initialize LCD
        self.lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2)
        self.lcd.backlight_enabled = False
        # Initialize log queue
        self.log_queue = queue.Queue()
        # Set up window properties
        self.title("Windmill Control Panel")
        self.geometry("720x600")
        # Configure grid layout
        for i in range(10):
            self.grid_rowconfigure(i, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        # Initialize theme
        ctk.set_appearance_mode("dark")

        def resource_path(relative_path):
            try:
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
            except AttributeError:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        # Access your files
        theme_path = resource_path("lakers-theme.json")
        image_path = resource_path("lebron.png")
        ctk.set_default_color_theme(theme_path)

        # Icon
        icon_image = tk.PhotoImage(file=image_path)
        self.iconphoto(False, icon_image)

        # Initialize motor control system
        self.control_system = MotorControlSystem(self.log_queue)
        self.control_system.set_motor_speed(self.control_system.motor_speed)
        # Speed control slider with label
        self.speed_label = ctk.CTkLabel(self, text="Dunk Rate")
        self.speed_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.speed_slider = ctk.CTkSlider(self, from_=0, to=100, command=self.update_motor_speed)
        self.speed_slider.set(self.control_system.motor_speed)
        self.speed_slider.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        # Stats box
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.grid(row=2, column=0, padx=10, pady=10, rowspan=4, sticky="nsew")
        self.rpm_label = ctk.CTkLabel(self.stats_frame, text=f"{self.control_system.calculate_rpm()} pts/gm")
        self.rpm_label.pack(pady=2, expand=True, fill='y')
        self.speed_percent_label = ctk.CTkLabel(self.stats_frame, text=f"Speed: {self.control_system.motor_speed:.5g}%")
        self.speed_percent_label.pack(pady=2, expand=True, fill='y')
        self.direction_label = ctk.CTkLabel(self.stats_frame, text=f"Direction: {self.control_system.get_direction_text()}")
        self.direction_label.pack(pady=2, expand=True, fill='y')
        self.status_label = ctk.CTkLabel(self.stats_frame, text=f"Status: {self.control_system.get_status_text()}")
        self.status_label.pack(pady=2, expand=True, fill='y')
        self.update_status_label()
        # Control buttons
        self.start_button = ctk.CTkButton(self, text="Start", command=self.start_motor)
        self.start_button.grid(row=6, column=0, padx=10, pady=5, sticky="nsew")
        self.pause_resume_button = ctk.CTkButton(self, text="Pause", command=self.pause_resume_motor)
        self.pause_resume_button.grid(row=7, column=0, padx=10, pady=5, sticky="nsew")
        self.stop_button = ctk.CTkButton(self, text="Stop", command=self.stop_motor)
        self.stop_button.grid(row=8, column=0, padx=10, pady=5, sticky="nsew")
        # Direction control button
        self.direction_button = ctk.CTkButton(self, text="Reverse Direction", command=self.reverse_direction)
        self.direction_button.grid(row=9, column=0, padx=10, pady=5, sticky="nsew")
        # Output terminal for logs
        self.terminal_frame = ctk.CTkFrame(self)
        self.terminal_frame.grid(row=0, column=1, rowspan=10, padx=10, pady=10, sticky="nsew")
        self.terminal_frame.rowconfigure(0, weight=1)
        self.terminal_frame.columnconfigure(0, weight=1)
        self.output_terminal = tk.Text(
            self.terminal_frame,
            wrap="word",
            state='disabled',
            bg="#1F1F1F",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            font=("Roboto", 18),
            highlightthickness=0,
            bd=0,
            cursor='arrow'
        )
        self.output_terminal.grid(row=0, column=0, sticky='nsew')
        # Scrollbar for the terminal
        self.scrollbar = ctk.CTkScrollbar(self.terminal_frame, command=self.output_terminal.yview)
        self.scrollbar.grid(row=0, column=1, sticky='ns')
        self.output_terminal.configure(yscrollcommand=self.scrollbar.set)
        # Start log processing
        self.after_log_id = self.after(100, self.process_log_queue)
        self.update_button_states()
    def update_lcd_display(self):
        """
        Update the LCD display with current RPM and status.
        """
        try:
            # Get current RPM and status
            rpm = self.control_system.calculate_rpm()
            status = self.control_system.get_status_text()
            # Update LCD content
            self.lcd.clear()
            self.lcd.write_string(f"{rpm} pts/gm")
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(f"Status: {status}")
        except Exception as e:
            self.log_to_terminal(f"LCD Update Error: {e}, reconnect LCD screen or restart program.")
            self.lcd.clear()
        finally:
            # Schedule next update after 1 second
            self.after_lcd_id = self.after(1000, self.update_lcd_display)
    def process_log_queue(self):
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.log_to_terminal(message)
        self.after(100, self.process_log_queue)
    def log_to_terminal(self, message):
        self.output_terminal.configure(state='normal')
        self.output_terminal.insert("end", f"{message}\n")
        self.output_terminal.configure(state='disabled')
        self.output_terminal.see("end")
    def update_motor_speed(self, value):
        self.control_system.set_motor_speed(value)
        self.rpm_label.configure(text=f"{self.control_system.calculate_rpm()} pts/gm")
        self.speed_percent_label.configure(text=f"Speed: {self.control_system.motor_speed:.2f}%")
    def start_motor(self):
        # Start LCD update loop
        self.lcd.backlight_enabled = True
        self.after_lcd_id = self.after(1000, self.update_lcd_display)
        self.control_system.start_motor()
        self.update_status_label()
        self.update_button_states()
    def pause_resume_motor(self):
        self.control_system.toggle_pause()
        if self.control_system.motor_paused:
            self.pause_resume_button.configure(text="Resume")
        else:
            self.pause_resume_button.configure(text="Pause")
        self.update_status_label()
    def stop_motor(self):
        self.after_cancel(self.after_log_id)
        self.after_cancel(self.after_lcd_id)
        self.lcd.backlight_enabled = False
        self.lcd.clear()
        self.control_system.stop_motor()
        self.pause_resume_button.configure(text="Pause")
        self.update_status_label()
        self.update_button_states()
    def reverse_direction(self):
        self.control_system.toggle_direction()
        self.direction_label.configure(text=f"Direction: {self.control_system.get_direction_text()}")
    def update_status_label(self):
        status = self.control_system.get_status_text()
        self.status_label.configure(text=f"Status: {status}")
        color = "green" if status == "Running" else "yellow" if status == "Paused" else "red"
        self.status_label.configure(text_color=color)
    def update_button_states(self):
        if self.control_system.motor_running:
            self.start_button.configure(state="disabled")
            self.pause_resume_button.configure(state="normal")
            self.stop_button.configure(state="normal")
        else:
            self.start_button.configure(state="normal")
            self.pause_resume_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
    def on_closing(self):
        try:
            self.control_system.stop_motor()
            self.control_system.cleanup()
            # Clear and close LCD display
            self.lcd.clear()
            self.lcd.backlight_enabled = False
            self.lcd.close()
            GPIO.cleanup()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            self.destroy()
if __name__ == "__main__":
    app = WindmillControlGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
