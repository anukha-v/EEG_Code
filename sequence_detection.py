# import necessary libraries 
import numpy as np
import time
import serial
from collections import deque
from scipy.signal import savgol_filter, find_peaks
from pythonosc import dispatcher, osc_server
import threading

SERIAL_PORT = '/dev/cu.usbmodem101'
BAUD_RATE = 9600
FS = 256  # Sampling frequency (Hz)
PROMINENCE = 90
WINDOW_SECONDS = 2

eeg_buffer = deque(maxlen=FS * WINDOW_SECONDS)

classified_events = []  # list with start, end, and type (of blink)
global_offset = 0  # tracks pos of blink in full EEG stream 

def eeg_handler(unused_addr, *args):
    global global_offset
    try:
        val = float(args[0])
        eeg_buffer.append(val)
        global_offset += 1
    except:
        pass

def start_osc_listener(ip="0.0.0.0", port=5000): 
    disp = dispatcher.Dispatcher()
    disp.map("/eeg", eeg_handler)
    server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    print(f"\U0001d55e Listening to OSC on port {port}...")
    threading.Thread(target=server.serve_forever, daemon=True).start()


def detect_grouped_blink_boundaries(signal, fs=256, baseline_window=256, prominence=100):
    baseline = np.mean(signal[:baseline_window])
    inverted = -signal #to find troughs

    troughs, props = find_peaks(inverted, distance=fs//10, prominence=prominence, width=1)
    peaks, _ = find_peaks(signal, distance=fs//10, prominence=prominence)

    if len(troughs) == 0:
        return [], []

    #increased functionality for longer blinks (i.e. blinks over 100 ms)
    first_width_ms = (props['widths'][0] / fs) * 1000 #for long blinks (generally have wider troughs)
    gap_ms = 1300 if first_width_ms > 140 else 500 #adaptive gap timing for long blinks

    grouped_troughs = []
    current_group = []

    for t in troughs:
        if not current_group:
            current_group.append(t)
        else:
            ms_gap = (t - current_group[-1]) / fs * 1000
            if ms_gap <= gap_ms: 
                current_group.append(t) #group troughs that are close together into current_group
            else:
                grouped_troughs.append(current_group)
                current_group = [t]
    if current_group:
        grouped_troughs.append(current_group)

    boundaries = []
    last_end = -1
    for group in grouped_troughs:
        first = group[0] #first trough index in current group
        last = group[-1] #last trough index in current group
        future_peaks = peaks[peaks > last] #to find peak after the last trough (endpoint)
        last_peak = future_peaks[0] if len(future_peaks) else min(len(signal) - 1, last + 30) #set end index as last peak or last trough + 30

        start = first
        end = last_peak

        if start > last_end and end > start: #makes sure no overlapping
            boundaries.append((start, end)) 
            last_end = end

    return boundaries, grouped_troughs

def extract_features(signal, global_troughs, fs=FS, start_idx=0, end_idx=None):
    if end_idx is None:
        end_idx = len(signal)

    segment_troughs = [t for t in global_troughs if start_idx <= t < end_idx] #finds troughs within blink start and end
    if len(segment_troughs) == 0:
        return {"num_troughs": 0, "inter_trough_avg_ms": 0, "duration_ms": 0}

    inter_troughs = np.diff(segment_troughs) / fs * 1000
    avg_inter = np.mean(inter_troughs) if len(inter_troughs) > 0 else 0
    duration_ms = (segment_troughs[-1] - segment_troughs[0]) / fs * 1000 if len(segment_troughs) > 1 else 0

    return {
        "num_troughs": len(segment_troughs),
        "inter_trough_avg_ms": avg_inter,
        "duration_ms": duration_ms
    }

def classify_blink(features):
    troughs = features["num_troughs"]
    duration = features["duration_ms"]

    #values determined from feature extraction on recorded data
    if troughs == 3 and 400 <= duration <= 950:
        return "triple_blink"
    elif troughs == 2 and 200 <= duration <= 550:
        return "double_blink"
    else:
        return "uncertain"

def detect_blink_sequence(classified_events, max_gap_ms=1500):
    if len(classified_events) < 2:
        return None

    last = classified_events[-1] #most recent blink
    prev = classified_events[-2] #the one before that
    gap_samples = last["start"] - prev["end"]
    gap_ms = (gap_samples / FS) * 1000 

    if gap_ms <= max_gap_ms: #checking timing to determine if sequence is valid
        return f"seq_{prev['type']}_{last['type']}"
    return None


def send_to_arduino(message):
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        time.sleep(2) #waiting till Arduino is ready
        while True:
            line = ser.readline().decode().strip()
            if line == "READY":
                print("Arduino is ready.")
                break

        ser.write((message + "\n").encode())
        print(f"Sent '{message}' to Arduino.")
        ser.close()

    except Exception as e:
        print(f"Failed to send to Arduino: {e}")

def real_time_main():
    start_osc_listener()
    smoothed_buffer = deque(maxlen=FS * WINDOW_SECONDS) #most recent samples depending on sliding window duration (WINDOW_SECONDS)
    print("Starting real-time detection")

    global global_offset #track position in entire EEG streamed data

    while True:
        if len(eeg_buffer) >= FS * 1.5: #1.5 seconds ish of data stored
            eeg_array = np.array(eeg_buffer)
            smoothed = savgol_filter(eeg_array, window_length=51, polyorder=3) #smooth the signal
            smoothed_buffer.clear()
            smoothed_buffer.extend(smoothed)
            signal = np.array(smoothed_buffer) #stores smoothed data in signal

            boundaries, grouped_troughs = detect_grouped_blink_boundaries(signal, prominence=PROMINENCE)
            global_troughs, _ = find_peaks(-signal, distance=FS//10, prominence=PROMINENCE)

            if grouped_troughs:
                group = grouped_troughs[-1]
                start_idx, end_idx = boundaries[-1]

                abs_start = global_offset - len(signal) + start_idx #converts start index of group into global time
                abs_end = global_offset - len(signal) + end_idx #converts end index to global

                #skips previously classified events
                overlap_exists = any(
                    abs_start <= e['end'] and abs_end >= e['start']
                    for e in classified_events
                )
                if overlap_exists:
                    continue

                features = extract_features(signal, global_troughs, start_idx=start_idx, end_idx=end_idx)

                if features["num_troughs"] == 2:
                    time.sleep(0.5) #wait to see if a third blink is coming before classifying as double blink

                    #re-run feature extraction to see if its a triple blink or double blink
                    eeg_array = np.array(eeg_buffer)
                    smoothed = savgol_filter(eeg_array, window_length=51, polyorder=3)
                    smoothed_buffer.clear()
                    smoothed_buffer.extend(smoothed)
                    signal = np.array(smoothed_buffer)

                    boundaries, grouped_troughs = detect_grouped_blink_boundaries(signal, prominence=PROMINENCE)
                    global_troughs, _ = find_peaks(-signal, distance=FS//10, prominence=PROMINENCE)

                    if grouped_troughs:
                        group = grouped_troughs[-1]
                        start_idx, end_idx = boundaries[-1]
                        abs_start = global_offset - len(signal) + start_idx
                        abs_end = global_offset - len(signal) + end_idx
                        features = extract_features(signal, global_troughs, start_idx=start_idx, end_idx=end_idx)

                blink_type = classify_blink(features)

                if blink_type in ["double_blink", "triple_blink"]:
                    classified_events.append({ #add data of blink to classified events
                        "start": abs_start,
                        "end": abs_end,
                        "type": blink_type
                    })
                    print(f"blink type detected: {blink_type} from {abs_start} to {abs_end}")

                    # Only prints/sends to Arduino if a valid sequence is detected
                    sequence = detect_blink_sequence(classified_events)
                    if sequence:
                        print(f"detected blink sequence: {sequence}")
                        send_to_arduino(sequence)

                    else:
                        print("no valid sequence formed yet")


if __name__ == "__main__":
    real_time_main()
