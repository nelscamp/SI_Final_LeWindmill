# Windmill Control Panel

## Overview
The **Windmill Control Panel** is a Python-based application for managing the operation of a motorized windmill and music box. It provides a graphical user interface (GUI) to adjust motor speed, change direction, and monitor real-time status using a Raspberry Pi. The application also supports a LCD display for visual feedback.

---

## Features
- **Motor Control**: Start, stop, and adjust the speed of the windmill and music box motors.
- **Direction Control**: Change the direction of motor rotation.
- **GUI**: User-friendly interface built with CustomTkinter.
- **LCD Support**: Display real-time motor statistics and status.
- **Raspberry Pi GPIO Integration**: Control hardware components directly.

---

## Prerequisites
Before installing and running the program, ensure the following:
- **Raspberry Pi**: A model with GPIO support (e.g., Raspberry Pi 4, 3B+).
- **Operating System**: Raspberry Pi OS (Debian-based).
- **Python Version**: Python 3.7 or higher.

---

## Required Hardware
1. **Stepper Motors** (e.g., NEMA17)
2. **DRV8833 Motor Drivers**
3. **LCD Display**
4. **Raspberry Pi GPIO Pins**
5. Power Supply and Cables

---

## Installation

### Step 1: Update Raspberry Pi
Update your Raspberry Pi’s package list and upgrade installed packages:
```bash
sudo apt-get update
sudo apt-get upgrade
```

### Step 2: Install Python and Pip
Ensure Python and pip are installed:
```bash
sudo apt-get install python python-pip
```

### Step 3: Enable I2C
Enable I2C communication on your Raspberry Pi:
```bash
sudo raspi-config
```
- Navigate to **Interfacing Options > I2C** and enable it.

Install I2C tools:
```bash
sudo apt-get install i2c-tools
```

### Step 4a: Clone the Repository
Clone the project repository to your Raspberry Pi:
```bash
git clone https://github.com/nelscamp/SI_Final_LeWindmill.git
cd SI_Final_LeWindmill
```

### OR ###

### Step 4b: Download Files Manually
- Install all files from https://github.com/nelscamp/SI_Final_LeWindmill.git into a folder.
- Access folder in terminal:
```bash
cd C:/path/to/folder
```

### Step 5: Install Dependencies
Install the required Python libraries:
```bash
pip install -r requirements.txt
```

---

## Usage

### Step 1: Connect Hardware
1. Wire the stepper motors, DRV8833 drivers, and LCD display to the Raspberry Pi GPIO pins as specified in your hardware documentation.
2. Ensure all connections are secure.

### Step 2: Run the Application
Start the program by running:
```bash
python LeWindmill.py
```

### Step 3: Use the Control Panel
- Adjust the **Dunk Rate** slider to set the motor speed.
- Click **Start** to activate the windmill and music box.
- Use **Pause** and **Stop** buttons to control the motor activity.
- Monitor motor status and speed on the GUI and LCD display.

---

## File Structure
```
windmill-control/
|-- LeWindmill.py          # Main program script
|-- lakers-theme.json      # Theme configuration for the GUI
|-- lebron.png             # Icon for the application
|-- requirements.txt       # List of required Python libraries
```

---

## Troubleshooting

### Common Issues
1. **I2C LCD Not Detected**:
   - Run `sudo i2cdetect -y 1` to check for the LCD address.
   - Ensure the correct address is configured in the code.

2. **GPIO Permission Denied**:
   - Run the program with elevated privileges:
     ```bash
     sudo python LeWindmill.py
     ```

3. **Missing Dependencies**:
   - Ensure all required libraries are installed using:
     ```bash
     pip3 install -r requirements.txt
     ```

4. **Motor Not Spinning**:
   - Check the wiring and power supply.
   - Verify that the GPIO pins are correctly configured in the code.
  
5. **LCD Display Showing Error**:
   - Check the wiring and power supply.
   - Verify that the GPIO pins are correctly configured in the code.
   - After checking wiring and power to LCD display, restart LeWindmill.py if error is there.
---

## Credits
Developed by **Nelson C., Ryan C., and Ethan S.** as a control panel for the Lebron Windmill.

---

## Contact
For questions or support, reach out at [ncampos@wm.edu].

