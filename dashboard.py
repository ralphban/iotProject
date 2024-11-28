from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import yagmail
import imaplib
import email
from email.header import decode_header
from datetime import datetime
import sqlite3  # For SQLite database interaction
import RPi.GPIO as GPIO
import dht11
import threading
import time


app = Flask(__name__)


# MQTT broker configuration
MQTT_BROKER = "10.0.0.171"
MQTT_PORT = 1883
LIGHT_INTENSITY_TOPIC = "sensor/light_value"
LIGHT_ALERT_TOPIC = "sensor/light_alert"
RFID_TAG_TOPIC = "sensor/rfid_tag"  # Topic to publish RFID tag


# Email setup
SENDER_EMAIL = "ralphbantillo@gmail.com"
RECEIVER_EMAIL = "ralphbantillo@gmail.com"
EMAIL_PASSWORD = "nkkp epyd tqlr oglf"


# IMAP configuration for email reply handling
IMAP_SERVER = "imap.gmail.com"
IMAP_USER = SENDER_EMAIL
IMAP_PASSWORD = EMAIL_PASSWORD


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
user_profile = {}  # Store user profile for front-end display


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


# Function to fetch user profile from the database based on RFID tag
def get_user_profile(rfid_tag):
    conn = sqlite3.connect('user_profiles.db')
    cursor = conn.cursor()
    print(f"Searching for user with RFID tag: {rfid_tag}")

    cursor.execute('''
    SELECT name, temp_threshold, light_threshold
    FROM users WHERE rfid_tag = ?
    ''', (rfid_tag,))


    user = cursor.fetchone()
    conn.close()


    if user:
        return {
            "name": user[0],
            "temp_threshold": user[1],
            "light_threshold": user[2]
        }
    else:
        print(f"No user found for RFID tag: {rfid_tag}")
        return None  # Return None if user not found


# MQTT callback to handle incoming RFID tag
def on_message(client, userdata, message):
    global light_intensity, alert_message, email_sent_light, email_sent_temp
    global email_sent_light_time, email_sent_temp_time, temperature, humidity, fan_state
    global user_profile  # Add user_profile to global scope


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


        # Handle RFID tag messages
        elif message.topic == RFID_TAG_TOPIC:
            rfid_tag = message.payload.decode() # Get RFID tag from MQTT message
            print(f"Received RFID Tag: {rfid_tag}")
            user_profile = get_user_profile(rfid_tag)  # Fetch user profile from DB


            if user_profile:
                print(f"User Profile Found: {user_profile}")
            else:
                print(f"User not found for UID! {rfid_tag}")


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


def check_email_replies():
    """Checks the inbox for replies to the temperature email and handles fan control."""
    global fan_state


    try:
        # Connect to the email server
        print("Connecting to email server...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        print("Successfully logged into email server.")


        # Select the inbox
        mail.select("inbox")


        # Search for unread emails with "Re: IoT Alert" in the subject
        print("Checking for unread email replies...")
        status, messages = mail.search(None, '(UNSEEN SUBJECT "Re: IoT Alert")')
        email_ids = messages[0].split()


        for email_id in email_ids:
            # Fetch the email
            print(f"Processing email ID: {email_id.decode()}")
            res, msg = mail.fetch(email_id, "(RFC822)")
            for response in msg:
                if isinstance(response, tuple):
                    # Parse the email
                    msg = email.message_from_bytes(response[1])


                    # Decode the email body
                    body = None
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if "attachment" not in content_disposition and content_type == "text/plain":
                                body = part.get_payload(decode=True)
                                if body:
                                    body = body.decode().strip()
                                    print(f"Email reply body: {body}")
                                    handle_fan_control(body)  # Pass reply to fan control logic
                    else:
                        body = msg.get_payload(decode=True)
                        if body:
                            body = body.decode().strip()
                            print(f"Email reply body: {body}")
                            handle_fan_control(body)  # Pass reply to fan control logic


            # Mark the email as read
            mail.store(email_id, "+FLAGS", "\\Seen")


        # Logout from the email server
        mail.logout()
        print("Logged out from email server.")


        if fan_state == "OFF":
            email_sent_temp = False
            print("Resetting email_sent_temp")


    except Exception as e:
        print(f"Error checking email replies: {e}")


def handle_fan_control(reply):
    """Handles fan control based on the reply (YES/NO)."""
    global fan_state
    cleaned_reply = reply.strip().upper().replace('\r', '').replace('\n', '')
    print(f"Cleaned reply for fan control: '{cleaned_reply}'")


    if "Y" in cleaned_reply:
        print("Turning on the fan based on email reply.")
        turn_on_fan()
    else:
        print(f"Invalid fan control reply received: '{cleaned_reply}'")


def periodic_email_check():
    """Periodically checks for email replies every 10 seconds."""
    while True:
        check_email_replies()
        time.sleep(10)


def connect_mqtt():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.subscribe(LIGHT_INTENSITY_TOPIC)
    mqtt_client.subscribe(LIGHT_ALERT_TOPIC)
    mqtt_client.subscribe(RFID_TAG_TOPIC)  # Subscribe to RFID tag topic
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
        'fan_state': fan_state,
        'user_profile': user_profile  # Return the user profile to the front-end
    })


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
    threading.Thread(target=periodic_email_check, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)