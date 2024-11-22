from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import yagmail
from datetime import datetime
import RPi.GPIO as GPIO
import dht11


app = Flask(__name__)


# MQTT broker configuration
MQTT_BROKER = "10.0.0.172"
MQTT_PORT = 1883
LIGHT_INTENSITY_TOPIC = "sensor/light_value"
LIGHT_ALERT_TOPIC = "sensor/light_alert"
FAN_CONTROL_TOPIC = "fan/control"


# Email setup
SENDER_EMAIL = "ralphbantillo@gmail.com"
RECEIVER_EMAIL = "ralphbantillo@gmail.com"
EMAIL_PASSWORD = "nkkp epyd tqlr oglf"


# Global state variables
light_intensity = 0
alert_message = ""
email_sent_light = False
email_sent_temp = False
email_sent_light_time = None
email_sent_temp_time = None
temperature = None
humidity = None
fan_state = "OFF"


# GPIO setup for DHT11 sensor
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
DHT_PIN = 4  # GPIO pin for DHT11
sensor = dht11.DHT11(pin=DHT_PIN)


# GPIO setup for the fan
Motor1 = 22  # Enable Pin
Motor2 = 27  # Input Pin 1
Motor3 = 17  # Input Pin 2
GPIO.setup(Motor1, GPIO.OUT)
GPIO.setup(Motor2, GPIO.OUT)
GPIO.setup(Motor3, GPIO.OUT)
GPIO.output(Motor1, GPIO.LOW)
GPIO.output(Motor2, GPIO.LOW)
GPIO.output(Motor3, GPIO.LOW)


# MQTT client setup
mqtt_client = mqtt.Client()


def on_message(client, userdata, message):
    global light_intensity, alert_message, email_sent_light, email_sent_temp
    global email_sent_light_time, email_sent_temp_time, temperature, humidity, fan_state


    try:
        # Handle light intensity updates
        if message.topic == LIGHT_INTENSITY_TOPIC:
            light_intensity = int(message.payload.decode())
            print(f"Received light intensity: {light_intensity}")


        # Handle light alert messages
        elif message.topic == LIGHT_ALERT_TOPIC:
            alert_message = message.payload.decode()
            print(f"Received alert: {alert_message}")


            # Send email for low light intensity if condition met
            if "LED ON" in alert_message and not email_sent_light:
                email_sent_light_time = datetime.now().strftime("%H:%M")
                send_email(f"The Light is ON due to low light intensity at {email_sent_light_time}.")
                email_sent_light = True
            elif "LED OFF" in alert_message:
                email_sent_light = False  # Reset flag when light turns off


        # Read temperature and humidity
        result = sensor.read()
        if result.is_valid():
            temperature = result.temperature
            humidity = result.humidity
            print(f"Temperature: {temperature}°C, Humidity: {humidity}%")


            # Send email for high temperature if condition met
            if temperature > 24 and not email_sent_temp:
                email_sent_temp_time = datetime.now().strftime("%H:%M")
                send_email(f"The current temperature is {temperature}°C. Would you like to turn on the fan? Reply YES to this email.")
                email_sent_temp = True
            elif temperature <= 24:
                email_sent_temp = False  # Reset flag when temperature goes below threshold


        # Handle fan control
        if message.topic == FAN_CONTROL_TOPIC:
            control_message = message.payload.decode().strip().upper()
            if control_message == "YES":
                turn_on_fan()
            elif control_message == "NO":
                turn_off_fan()


    except Exception as e:
        print(f"Error processing message: {e}")


mqtt_client.on_message = on_message


def turn_on_fan():
    global fan_state
    GPIO.output(Motor1, GPIO.HIGH)
    GPIO.output(Motor2, GPIO.LOW)
    GPIO.output(Motor3, GPIO.HIGH)
    fan_state = "ON"
    print("Fan turned ON.")


def turn_off_fan():
    global fan_state
    GPIO.output(Motor1, GPIO.LOW)
    GPIO.output(Motor2, GPIO.LOW)
    GPIO.output(Motor3, GPIO.LOW)
    fan_state = "OFF"
    print("Fan turned OFF.")

@app.route('/toggle-fan', methods=['POST'])
def toggle_fan():
    global fan_state
    data = request.get_json()
    if 'state' in data:
        requested_state = data['state']
        if requested_state == "ON":
            turn_on_fan()
        elif requested_state == "OFF":
            turn_off_fan()
        return jsonify({'success': True, 'fan_state': fan_state})
    return jsonify({'success': False, 'message': 'Invalid request'})


def connect_mqtt():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.subscribe(LIGHT_INTENSITY_TOPIC)
    mqtt_client.subscribe(LIGHT_ALERT_TOPIC)
    mqtt_client.subscribe(FAN_CONTROL_TOPIC)  # Subscribe to fan control topic
    mqtt_client.loop_start()


@app.route('/')
def dashboard():
    return render_template('index.html', light_intensity=light_intensity, alert_message=alert_message)


@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'light_intensity': light_intensity,
        'alert_message': alert_message,
        'email_sent_light': email_sent_light,
        'email_sent_light_time': email_sent_light_time,
        'email_sent_temp': email_sent_temp,
        'email_sent_temp_time': email_sent_temp_time,
        'temperature': temperature,
        'humidity': humidity,
        'fan_state': fan_state
    })


def send_email(body):
    try:
        yag = yagmail.SMTP(user=SENDER_EMAIL, password=EMAIL_PASSWORD)
        subject = "IoT Alert"
        yag.send(to=RECEIVER_EMAIL, subject=subject, contents=body)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")


if __name__ == "__main__":
    connect_mqtt()
    app.run(host="0.0.0.0", port=5000)