import sqlite3


# Function to set up the database and create the users table
def setup_database():
    conn = sqlite3.connect('user_profiles.db')  # Connect to the SQLite database
    cursor = conn.cursor()


    # Create table if it does not exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        rfid_tag TEXT PRIMARY KEY NOT NULL,
        name TEXT NOT NULL,
        temp_threshold INTEGER NOT NULL,
        light_threshold INTEGER NOT NULL
    )
    ''')
    conn.commit()


    # Add initial users manually
    add_user("ADF20331", "Ralph", 25, 950)
    add_user("75C1A7AC", "Bantillo", 30, 300)


    conn.close()


# Function to add a user to the database
def add_user(rfid_tag, name, temp_threshold, light_threshold):
    conn = sqlite3.connect('user_profiles.db')
    cursor = conn.cursor()


    cursor.execute('''
    INSERT INTO users (rfid_tag, name, temp_threshold, light_threshold)
    VALUES (?, ?, ?, ?)
    ''', (rfid_tag, name, temp_threshold, light_threshold))


    conn.commit()
    conn.close()


# Call the setup_database function to initialize the database
setup_database()
