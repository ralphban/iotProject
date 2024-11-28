#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MFRC522.h>  // Include MFRC522 RFID library


// Wi-Fi credentials
const char* ssid = "Rapcassrae_2.4";  // Replace with your Wi-Fi SSID
const char* password = "5144490892";  // Replace with your Wi-Fi password


// MQTT broker configuration
const char* mqtt_server = "10.0.0.171";  // MQTT Broker IP address


WiFiClient espClient;
PubSubClient client(espClient);


// Pin definitions for light sensor and LED
#define LIGHT_SENSOR_PIN 34  // Analog pin for light sensor (ESP32 ADC pin)
#define LED_PIN 2            // GPIO2 for LED
#define ANALOG_THRESHOLD 400 // Light threshold for turning on LED


// Pin definitions for RFID
#define SS_PIN 5  // SDA Pin on RC522 (Chip Select)
#define RST_PIN 4 // Reset Pin on RC522


MFRC522 rfid(SS_PIN, RST_PIN); // Create MFRC522 instance


long lastMsg = 0;
char msg[50];


void setup() {
  // Initialize Serial communication for debugging
  Serial.begin(115200);


  // Initialize MFRC522 RFID reader
  SPI.begin();          // Initialize the SPI bus
  rfid.PCD_Init();      // Initialize MFRC522 reader
  Serial.println("Place your RFID card near the reader...");


  // Initialize Wi-Fi
  WiFi.begin(ssid, password);


  // Wait for Wi-Fi connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());


  // Connect to MQTT broker
  client.setServer(mqtt_server, 1883);
  reconnect();  // Ensure MQTT connection


  // Initialize LED pin
  pinMode(LED_PIN, OUTPUT);  // Set the LED pin as an output
  digitalWrite(LED_PIN, LOW);  // Ensure LED is off initially
}


void reconnect() {
  // Reconnect to MQTT broker if disconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32Client")) {
      Serial.println("connected to MQTT broker");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 5 seconds");
      delay(5000);
    }
  }
}


void loop() {
  // Ensure MQTT connection
  if (!client.connected()) {
    reconnect();
  }
  client.loop();


  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {

    // Construct UID in HEX format
    String uidHex = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
        if (rfid.uid.uidByte[i] < 0x10) {
            uidHex += "0"; // Add leading zero for single-digit hex values
        }
        uidHex += String(rfid.uid.uidByte[i], HEX);
    }
    uidHex.toUpperCase(); // Format to uppercase


    // Publish RFID UID
    client.publish("sensor/rfid_tag", uidHex.c_str()); // Publish to RFID topic
    Serial.print("Published RFID UID: ");
    Serial.println(uidHex);


    rfid.PICC_HaltA(); // Halt the card to be ready for the next one
  }

  // Read light sensor value
  int analogValue = analogRead(LIGHT_SENSOR_PIN);
  Serial.print("Light sensor value: ");
  Serial.println(analogValue);


  // Publish light intensity value to MQTT
  snprintf(msg, 50, "%d", analogValue);
  client.publish("sensor/light_value", msg);
  Serial.print("Published light intensity: ");
  Serial.println(msg);


  // Control LED based on light intensity
  if (analogValue < ANALOG_THRESHOLD) {
    Serial.println("Light intensity below threshold, turning LED ON");
    digitalWrite(LED_PIN, HIGH);  // Turn on LED
    snprintf(msg, 50, "Light intensity low: %d. LED ON.", analogValue);
    client.publish("sensor/light_alert", msg);  // Publish alert
    Serial.println("LED ON: Alert sent.");
  } else {
    Serial.println("Light intensity above threshold, turning LED OFF");
    digitalWrite(LED_PIN, LOW);  // Turn off LED
    snprintf(msg, 50, "Light intensity normal: %d. LED OFF.", analogValue);
    client.publish("sensor/light_alert", msg);  // Publish alert
    Serial.println("LED OFF: Alert sent.");
  }


  delay(1000);  // Delay before reading again
}
