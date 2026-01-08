from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import requests
import google.generativeai as genai  # Import Google Generative AI

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a strong, random key!

# Database Connection
try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Nrrg@27082004",
        database="farmers_assistance"
    )
    cursor = db.cursor()
except mysql.connector.Error as e:
    print(f"Error connecting to database: {e}")
    # Consider a more robust error handling strategy here, like logging to a file
    # and perhaps displaying a user-friendly error page.
    exit()  # Exit if the database connection fails

# Ensure tables exist (do this once on setup, not on every request)
def create_tables():
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            contact VARCHAR(20)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            city VARCHAR(100),
            country VARCHAR(50),
            temperature FLOAT,
            weather_description VARCHAR(255),
            wind_speed FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        db.commit()
    except mysql.connector.Error as e:
        print(f"Error creating tables: {e}")
        # Handle table creation errors (e.g., log, display message, or attempt to recover)
        db.rollback()
        exit()

create_tables() #calling the function to create tables

# OpenWeather API Key
API_KEY = "your_secret_key"  # Replace with your actual API key

# Configure Gemini
genai.configure(api_key="your_secret_key")  # Use your Gemini API key

# Corrected Model Name - IMPORTANT
model_name = 'gemini-1.5-pro'  # Or 'gemini-2.5-flash',  or whatever is appropriate as per documentation.  Using 1.5 Pro
model = genai.GenerativeModel(model_name)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        contact = request.form['contact']

        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()
        except mysql.connector.Error as e:
            print(f"Error checking for existing user: {e}")
            db.rollback()
            return "Database error!"  #  Handle the error

        if existing_user:
            return "User already exists!"

        try:
            cursor.execute("INSERT INTO users (username, password, contact) VALUES (%s, %s, %s)", (username, password, contact))
            db.commit()
        except mysql.connector.Error as e:
            print(f"Error inserting new user: {e}")
            db.rollback()
            return "Database error during signup!"  #  Handle the error
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()
        except mysql.connector.Error as e:
            print(f"Error during login: {e}")
            db.rollback()
            return "Database error during login"

        if user:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials!"

    return render_template('login.html')

def get_weather_data(city):
    """Fetches weather data from OpenWeatherMap API.

    Args:
        city (str): The name of the city.

    Returns:
        dict: A dictionary containing weather information, or None on error.
    """
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        weather_data = response.json()
        return weather_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None  # Return None to indicate an error

def store_weather_data(weather_data):
    """Stores weather data in the database.

    Args:
        weather_data (dict): A dictionary containing weather information.
    """
    try:
        insert_query = """
            INSERT INTO weather_data (city, country, temperature, weather_description, wind_speed)
            VALUES (%s, %s, %s, %s, %s)
            """
        cursor.execute(insert_query, (
            weather_data["name"], weather_data.get("sys", {}).get("country", "Unknown"),
            weather_data["main"]["temp"], weather_data.get("weather", [{}])[0].get("description", "No description"),
            weather_data["wind"]["speed"]
        ))
        db.commit()
    except mysql.connector.Error as e:
        print(f"Error storing weather data: {e}")
        db.rollback()  # Rollback on database error
        # Consider whether to raise an exception or return a value to the caller

def get_chatbot_response(user_question):
    """Gets a response from the Google Gemini.

    Args:
        user_question (str): The user's question.

    Returns:
        str: The chatbot's response, or an error message.
    """
    try:
        response = model.generate_content(user_question)
        if response.text:
            return response.text
        else:
            return "Sorry, I couldn't understand your question."
    except Exception as e:
        print(f"Error getting Gemini response: {e}")
        return f"Error: {e}"

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    weather_info = None
    chatbot_response = None

    if request.method == 'POST':
        if 'city' in request.form:
            city = request.form['city']
            weather_data = get_weather_data(city) #calling the get_weather_data function

            if weather_data:
                weather_info = {
                    "city": weather_data["name"],
                    "country": weather_data.get("sys", {}).get("country", "Unknown"),
                    "temperature": weather_data["main"]["temp"],
                    "weather_description": weather_data.get("weather", [{}])[0].get("description", "No description"),
                    "humidity": weather_data["main"]["humidity"],
                    "wind_speed": weather_data["wind"]["speed"]
                }
                store_weather_data(weather_data) # Store the data
            else:
                weather_info = None #set weather info to none if there is an error

        if 'user_query' in request.form:
            user_question = request.form['user_query']
            chatbot_response = get_chatbot_response(user_question)

    return render_template('dashboard.html', username=session['username'], weather=weather_info, chatbot_response=chatbot_response)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)

