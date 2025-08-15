# Muse EEG Blink Sequences → Arduino Servo Actuation

Real-time blink **sequence** detection from a Muse EEG stream in Python, with serial commands sent to an Arduino that **toggles 5 servo motors** (0° ↔ 160°). Singles (double/triple) and pairs (double→double, double→triple, triple→double, triple→triple) are supported.

---

## Repo Contents
- `sequence_detection.py` — Muse OSC ingest, blink detection & classification, sequence detection, and serial send.
- `eeg_actuation.ino` — Arduino sketch that receives commands and toggles servos on pins **3, 5, 6, 9, 10**.

---

## Hardware
- **Muse headset** streaming via **Muse app** (OSC output enabled)  
- **Arduino** (Uno/Nano/Leonardo or similar)  
- **5× hobby servos**  
- **External 5 V power** for servos (recommended). **Common ground** with Arduino is required.

### Wiring (example)
| Servo | Arduino Pin |
|------:|:-----------:|
| S1    | 3           |
| S2    | 5           |
| S3    | 6           |
| S4    | 9           |
| S5    | 10          |

> Servos draw significant current. Power servos from a separate 5 V supply (capable of ≥2–3 A for five servos), and connect the supply **GND to Arduino GND**.

---

## Software Setup

### Python
```bash
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install numpy scipy python-osc pyserial
