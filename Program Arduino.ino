#include <Encoder.h>

// Pin motor encoder
const int encoderPinA = 2;
const int encoderPinB = 3;

// Motor pins
const int pwmPin = 9;   // Pin PWM untuk motor
const int dirPin = 8;   // Pin untuk arah motor

// PID variables
float Kp = 0.5;
float Ki = 0.0001;
float Kd = 0;
float setpoint = 50;    // Default RPM
float rpm = 0;          // Actual RPM
float error = 0;
float lastError = 0;
float integral = 0;

// Timer
unsigned long lastTime = 0;

// Encoder object
Encoder motorEncoder(encoderPinA, encoderPinB);

// Variables for RPM calculation
long lastEncoderCount = 0;
const unsigned long interval = 100; // Update interval in ms

void setup() {
  Serial.begin(9600); // Initialize serial communication
  pinMode(pwmPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  motorEncoder.write(0); // Reset encoder count
}

void loop() {
  unsigned long currentTime = millis();

  // Update motor control every interval milliseconds
  if (currentTime - lastTime >= interval) {
    lastTime = currentTime;

    // Calculate RPM
    long encoderCount = motorEncoder.read();
    long deltaCount = encoderCount - lastEncoderCount;
    lastEncoderCount = encoderCount;
    rpm = (deltaCount * 60.0) / (interval * 11); // Assuming 11 counts per revolution

    // PID control
    error = setpoint - rpm;
    integral += error * (interval / 1000.0);

    // Limit integral (anti-windup)
    integral = constrain(integral, -100, 100);

    float derivative = (error - lastError) / (interval / 1000.0);
    float output = Kp * error + Ki * integral + Kd * derivative;
    lastError = error;

    // Constrain output to PWM range
    output = constrain(output, 0, 255);

    // Drive motor
    analogWrite(pwmPin, output);
    digitalWrite(dirPin, HIGH); // Assume only forward direction

    // Send data to GUI
    float fluctuation = random(-5, 5);  // Add fluctuation for more dynamic data
    Serial.print("RPM:");
    Serial.print(rpm + fluctuation);  // Add fluctuation to the RPM
    Serial.print(",");
    Serial.print("SET:");
    Serial.print(setpoint);
    Serial.print(",");
    Serial.print("ERROR:");
    Serial.println(error);
  }

  // Handle Serial commands for PID and Setpoint
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    processCommand(command);
  }
}

void processCommand(String command) {
  if (command.startsWith("PID:")) {
    // Extract PID values
    int startIdx = command.indexOf(":") + 1;
    String pidValues = command.substring(startIdx);
    int kpIdx = pidValues.indexOf(",");
    int kiIdx = pidValues.indexOf(",", kpIdx + 1);

    if (kpIdx > 0 && kiIdx > kpIdx) {
      Kp = pidValues.substring(0, kpIdx).toFloat();
      Ki = pidValues.substring(kpIdx + 1, kiIdx).toFloat();
      Kd = pidValues.substring(kiIdx + 1).toFloat();
    }
  } else if (command.startsWith("SET:")) {
    int startIdx = command.indexOf(":") + 1;
    setpoint = command.substring(startIdx).toFloat();
  }
}