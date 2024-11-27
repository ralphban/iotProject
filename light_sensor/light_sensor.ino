#include <WiFi.h>
#include <PubSubClient.h>


// Wi-Fi credentials
const char* ssid = "Rapcassrae_2.4";  // Replace with your Wi-Fi SSID
const char* password = "5144490892";  // Replace with your Wi-Fi password


// MQTT broker configuration
const char* mqtt_server = "10.0.0.171";  // MQTT Broker IP address


WiFiClient espClient;
PubSubClient client(espClient);


// Pin definitions
#define LIGHT_SENSOR_PIN 34  // Analog pin for light sensor (ESP32 ADC pin)
#define LED_PIN 2            // GPIO2 for LED
#define ANALOG_THRESHOLD 400 // Light threshold for turning on LED


long lastMsg = 0;
char msg[50];


void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);  // Set LED pin as output
  digitalWrite(LED_PIN, LOW);  // Turn off LED initially


  Serial.println("ESP32 is starting...");
  WiFi.begin(ssid, password);


  // Connect to Wi-Fi
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());


  // Connect to MQTT broker
  client.setServer(mqtt_server, 1883);
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


  // Read light sensor value
  int analogValue = analogRead(LIGHT_SENSOR_PIN);
  Serial.print("Light sensor value: ");
  Serial.println(analogValue);


  // Publish light intensity value
  snprintf(msg, 50, "%d", analogValue);
  client.publish("sensor/light_value", msg);
  Serial.print("Published light intensity: ");
  Serial.println(msg);


  // Control LED based on light intensity
  if (analogValue < ANALOG_THRESHOLD) {
    digitalWrite(LED_PIN, HIGH);  // Turn on LED
    snprintf(msg, 50, "Light intensity low: %d. LED ON.", analogValue);
    client.publish("sensor/light_alert", msg);  // Publish alert
    Serial.println("LED ON: Alert sent.");
  } else {
    digitalWrite(LED_PIN, LOW);  // Turn off LED
    snprintf(msg, 50, "Light intensity normal: %d. LED OFF.", analogValue);
    client.publish("sensor/light_alert", msg);  // Publish alert
    Serial.println("LED OFF: Alert sent.");
  }


  delay(5000);  // Publish every 5 seconds
}
