from flask import Flask, render_template, jsonify
import paho.mqtt.client as mqtt
import yagmail
from datetime import datetime


app = Flask(__name__)


# MQTT broker configuration
MQTT_BROKER = "10.0.0.172"
MQTT_PORT = 1883
LIGHT_INTENSITY_TOPIC = "sensor/light_value"
LIGHT_ALERT_TOPIC = "sensor/light_alert"


# Email setup
SENDER_EMAIL = "ralphbantillo@gmail.com"
RECEIVER_EMAIL = "ralphbantillo@gmail.com"
EMAIL_PASSWORD = "nkkp epyd tqlr oglf"


# Global state variables
light_intensity = 0
alert_message = ""
email_sent = False
email_sent_time = None

# MQTT client setup
mqtt_client = mqtt.Client()


def on_message(client, userdata, message):
    global light_intensity, alert_message, email_sent, email_sent_time
    try:
        # Handle light intensity updates
        if message.topic == LIGHT_INTENSITY_TOPIC:
            light_intensity = int(message.payload.decode())
            print(f"Received light intensity: {light_intensity}")

        # Handle light alert messages
        elif message.topic == LIGHT_ALERT_TOPIC:
            alert_message = message.payload.decode()
            print(f"Received alert: {alert_message}")


            # Send email if an alert is received
            if "LED ON" in alert_message and not email_sent:
                email_sent_time = datetime.now().strftime("%H:%M")
                send_email(f"The Light is ON at {email_sent_time}.")
                email_sent = True
            #    print("Email sent. Reseting email_sent flag")
            #    email_sent = False
            elif "LED OFF" in alert_message:
                email_sent = False  # Reset email flag when light is off
                email_sent_time = None


    except Exception as e:
        print(f"Error processing message: {e}")


mqtt_client.on_message = on_message


def connect_mqtt():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.subscribe(LIGHT_INTENSITY_TOPIC)
    mqtt_client.subscribe(LIGHT_ALERT_TOPIC)
    mqtt_client.loop_start()


@app.route('/')
def dashboard():
    return render_template('index.html', light_intensity=light_intensity, alert_message=alert_message)


@app.route('/status', methods=['GET'])
def status():
    print(f"light_intensity: {light_intensity}")
    print(f"aler_message: {alert_message}")
    print(f"email_sent: {email_sent}")
    print(f"email_sent_time: {email_sent_time}")
    return jsonify({
        'light_intensity': light_intensity,
        'alert_message': alert_message,
        'email_sent': email_sent,
        'email_sent_time': email_sent_time
    })


def send_email(body):
    try:
        yag = yagmail.SMTP(user=SENDER_EMAIL, password=EMAIL_PASSWORD)
        subject = "Light Alert"
        yag.send(to=RECEIVER_EMAIL, subject=subject, contents=body)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")


if __name__ == "__main__":
    connect_mqtt()
    app.run(host="0.0.0.0", port=5000)