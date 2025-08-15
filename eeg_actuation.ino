#include <Servo.h>

int POS_LOW = 0;
int POS_HIGH = 160;

int SERVO_PINS[5] = {3, 5, 6, 9, 10};
Servo servos[5];
bool isHigh[5] = {false, false, false, false, false};

void toggleServo(int idx) {
  if (idx < 0 || idx >= 5) return;
  if (isHigh[idx]) {
    servos[idx].write(POS_LOW);
    isHigh[idx] = false;
  } else {
    servos[idx].write(POS_HIGH);
    isHigh[idx] = true;
  }
}

void toggleAll() {
  for (int i = 0; i < 5; i++) {
    toggleServo(i);
  }
}

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < 5; i++) {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(POS_LOW);
  }
  delay(1000);
  Serial.println("READY");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input == "double_blink") { //toggle thumb movement
      toggleServo(0);
    } 
    else if (input == "triple_blink") { //toggle index finger movement
      toggleServo(1);
    } 
    else if (input == "seq_double_blink_double_blink") { //toggle middle finger movement
      toggleServo(2);
    } 
    else if (input == "seq_double_blink_triple_blink") { //toggle ring finger movement
      toggleServo(3);
    } 
    else if (input == "seq_triple_blink_double_blink") { //toggle pinky finger movement
      toggleServo(4);
    } 
    else if (input == "seq_triple_blink_triple_blink") { //move all fingers in/out (open/close hand)
      toggleAll();
    }
  }
}