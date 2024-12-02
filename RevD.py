import customtkinter as ctk
import tkinter as tk
import time
from threading import Thread, Event
import queue
import RPi.GPIO as GPIO
 
# Motor control system class
class MotorControlSystem:
    def __init__(self, log_queue):
        # Define GPIO pins for DRV8833
        self.AIN1 = 17  # Pin for Coil A1
        self.AIN2 = 22  # Pin for Coil A2
        self.BIN1 = 27  # Pin for Coil B1
        self.BIN2 = 23  # Pin for Coil B2
 
        # Stepper motor parameters
        self.STEPS_PER_REV = 200  # NEMA17 typically has 200 steps per revolution
        self.FULL_STEP_SEQUENCE = [
            [1, 0, 1, 0],  # Step 1
            [0, 1, 1, 0],  # Step 2
            [0, 1, 0, 1],  # Step 3
            [1, 0, 0, 1],  # Step 4
        ] # Stepper motor clockwise steps

        # Note: Will iterate in reverse order when going counterclockwise
 
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.AIN1, GPIO.OUT)
        GPIO.setup(self.AIN2, GPIO.OUT)
        GPIO.setup(self.BIN1, GPIO.OUT)
        GPIO.setup(self.BIN2, GPIO.OUT)
 
        # Motor control variables
        self.motor_speed = 50  # Initial speed percentage
        self.motor_running = False # Start as not running
        self.motor_paused = False # Start as paused
        self.direction = 'clockwise'  # 'clockwise' or 'counterclockwise'
 
        # Thread control
        self.stop_event = Event()
        self.pause_event = Event()
 
        # Log queue for GUI
        self.log_queue = log_queue
 
    def set_motor_pins(self, state):
        GPIO.output(self.AIN1, state[0])
        GPIO.output(self.AIN2, state[1])
        GPIO.output(self.BIN1, state[2])
        GPIO.output(self.BIN2, state[3])
 
    def calculate_delay(self):
        MAX_RPM = 120  # Maximum RPM
        rpm = self.motor_speed / 100.0 * MAX_RPM
        steps_per_second = rpm * self.STEPS_PER_REV / 60.0
        delay = 1.0 / steps_per_second if steps_per_second > 0 else 0.1
        return delay
 
    def start_motor(self):
        if not self.motor_running:
            self.stop_event.clear()
            self.pause_event.clear()
            self.motor_paused = False
            self.motor_thread = Thread(target=self.run_motor)
            self.motor_running = True
            self.motor_thread.start()
            self.log_queue.put("Windmill started.")
 
    def run_motor(self):
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
            self.set_motor_pins(self.FULL_STEP_SEQUENCE[sequence_index])
            step_index += 1
            delay = self.calculate_delay()
            time.sleep(delay)
        self.motor_running = False
        self.set_motor_pins([0, 0, 0, 0])
 
    def stop_motor(self):
        if self.motor_running:
            self.stop_event.set()
            self.pause_event.clear()
            self.motor_paused = False
            self.motor_thread.join()
            self.motor_running = False
            self.log_queue.put("Windmill stopped.")
 
    def toggle_pause(self):
        if self.motor_running:
            if self.pause_event.is_set():
                self.pause_event.clear()
                self.motor_paused = False
                self.log_queue.put("Windmill resumed.")
            else:
                self.pause_event.set()
                self.motor_paused = True
                self.log_queue.put("Windmill paused.")
 
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
        MAX_RPM = 120
        return int(self.motor_speed / 100.0 * MAX_RPM)
 
    def cleanup(self):
        GPIO.cleanup()
 
# GUI class
class WindmillControlGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
 
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
 
        # Initialize customtkinter theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
 
        # Initialize motor control system
        self.control_system = MotorControlSystem(self.log_queue)
        self.control_system.set_motor_speed(self.control_system.motor_speed)
 
        # Speed control slider with label
        self.speed_label = ctk.CTkLabel(self, text="Speed")
        self.speed_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.speed_slider = ctk.CTkSlider(self, from_=0, to=100, command=self.update_motor_speed)
        self.speed_slider.set(self.control_system.motor_speed)
        self.speed_slider.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
 
        # Stats box
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.grid(row=2, column=0, padx=10, pady=10, rowspan=4, sticky="nsew")
 
        self.rpm_label = ctk.CTkLabel(self.stats_frame, text=f"RPM: {self.control_system.calculate_rpm()}")
        self.rpm_label.pack(pady=2, expand=True, fill='y')
 
        self.speed_percent_label = ctk.CTkLabel(self.stats_frame, text=f"Speed: {self.control_system.motor_speed}%")
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
            font=("Helvetica", 18),
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
        self.after(100, self.process_log_queue)
 
        self.update_button_states()
 
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
        self.rpm_label.configure(text=f"RPM: {self.control_system.calculate_rpm()}")
        self.speed_percent_label.configure(text=f"Speed: {self.control_system.motor_speed}%")
 
    def start_motor(self):
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
        self.control_system.stop_motor()
        self.control_system.cleanup()
        self.destroy()
 
if __name__ == "__main__":
    app = WindmillControlGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()