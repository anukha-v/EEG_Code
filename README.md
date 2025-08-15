# Muse EEG Blink Sequences -> Arduino Servo Actuation

Real-time blink **sequence** detection from a Muse EEG stream in Python, with serial commands sent to an Arduino that **toggles 5 servo motors** (0° ↔ 160°) based on detection of the 6 following blink events: only double blink, only triple blink, double-double blink sequence, double-triple blink seequence, triple-double blink sequence, and triple-triple blink sequence.

---

## Repo Contents
- `sequence_detection.py`: Analyzes Muse data (streamed to computer via Open Sound Control), blink detection & classification, sequence detection, and serial send.
- `eeg_actuation.ino`: Arduino code that receives classified blink sequences and toggles micro servos on pins **3, 5, 6, 9, 10**.

---

## Hardware
- **Muse 2 headset** streaming via **Muse app** (enable OSC output)  
- **Arduino Uno**
- **5× micro servos**  
- **External 5V power connected to Arduino** for servos (recommended)

---

## Software Setup

### Python -> install necessary libraries
```bash
pip install numpy scipy python-osc pyserial
