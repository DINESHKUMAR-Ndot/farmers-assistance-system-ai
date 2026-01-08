import mysql.connector

def get_db_connection():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Nrrg@27082004",
            database="farmers_assistance"
        )
        if db.is_connected():
            print("Database Connection Successful!")
        return db
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None
