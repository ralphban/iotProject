#include <ESP8266WiFi.h>
#include <PubSubClient.h>

const char* ssid = "TP-Link_2AD8";
const char* password = "14730078";
const char* mqtt_server = "192.168.0.176"; // MQTT Broker IP address

WiFiClient espClient;
PubSubClient client(espClient);

#define LIGHT_SENSOR_PIN A0 // Light sensor analog pin

long lastMsg = 0;
char msg[50];

void setup() {
Serial.begin(115200);
delay(10);

Serial.println("Connecting to Wi-Fi...");
WiFi.begin(ssid, password);

while (WiFi.status() != WL_CONNECTED) {
delay(500);
Serial.print(".");
}

Serial.println("\nWiFi connected");
Serial.print("IP address: ");
Serial.println(WiFi.localIP());

client.setServer(mqtt_server, 1883);
}

void reconnect() {
while (!client.connected()) {
Serial.print("Attempting MQTT connection...");
if (client.connect("ESP8266Client")) {
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
if (!client.connected()) {
reconnect();
}

int analogValue = analogRead(LIGHT_SENSOR_PIN); // Read light sensor value
Serial.print("Light sensor value: ");
Serial.println(analogValue);

snprintf(msg, 50, "Light sensor value: %d", analogValue);

if (millis() - lastMsg > 10000) { // Publish every 10 seconds
client.publish("sensor/light_value", msg);
lastMsg = millis();
}

client.loop();
}
