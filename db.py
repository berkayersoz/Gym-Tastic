import sqlite3
import re
import pandas as pd

def createDB(dbname):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    #User table
    c.execute("CREATE TABLE IF NOT EXISTS user(userID INTEGER PRIMARY KEY, "
              "full_name TEXT NOT NULL,"
              "username TEXT NOT NULL,"
              "password TEXT NOT NULL,"
              "email TEXT NOT NULL,"
              "telephone TEXT NOT NULL,"
              "address TEXT NOT NULL)")
    #Registered User table
    c.execute("CREATE TABLE IF NOT EXISTS registeredUser(userID INTEGER, "
              "age INTEGER NOT NULL,"
              "height DOUBLE NOT NULL"
              ",weight DOUBLE NOT NULL, "
              "goals TEXT NOT NULL, "
              "FOREIGN KEY(userID) REFERENCES user(userID))")
    #Admin table
    c.execute("CREATE TABLE IF NOT EXISTS admin(adminID INTEGER PRIMARY KEY,"
              "userID INTEGER NOT NULL,"
              "FOREIGN KEY(userID) REFERENCES user(userID))")
    #Fitness Plan table
    c.execute("CREATE TABLE IF NOT EXISTS fitnessPlan(planID INTEGER PRIMARY KEY,"
              "gender TEXT NOT NULL"
              ",height DOUBLE NOT NULL,"
              "weight DOUBLE NOT NULL,"
              "userID INTEGER NOT NULL,"
              "FOREIGN KEY(userID) REFERENCES user(userID))")
    #Content table
    c.execute("CREATE TABLE IF NOT EXISTS content(contentID INTEGER PRIMARY KEY, "
              "type TEXT NOT NULL,"
              "description TEXT NOT NULL,"
              "title TEXT NOT NULL)")

    #Exercise table
    c.execute("CREATE TABLE IF NOT EXISTS exercise(exerciseID INTEGER PRIMARY KEY, "
              "name TEXT NOT NULL,"
              "category TEXT NOT NULL,"
              "targetedBodyParts TEXT NOT NULL,"
              "requieredEquipment TEXT NOT NULL,"
              "videoURL TEXT NOT NULL)")
    #Workout Session table
    c.execute("CREATE TABLE IF NOT EXISTS workoutSession(sessionID INTEGER PRIMARY KEY,"
              "date DATETIME NOT NULL,"
              "duration TIMESTAMP NOT NULL,"
              "postureAccuracy DOUBLE NOT NULL,"
              "userID INTEGER NOT NULL,"
              "FOREIGN KEY(userID) REFERENCES registeredUser(userID))")

    #Issue Form table
    c.execute("CREATE TABLE IF NOT EXISTS issueForm(issueID INTEGER PRIMARY KEY, "
              "description TEXT NOT NULL"
              ",status TEXT NOT NULL,"
              "userID INTEGER NOT NULL,"
              "adminID INTEGER NOT NULL,"
              "FOREIGN KEY(userID) REFERENCES user(userID),"
              "FOREIGN KEY(adminID) REFERENCES admin(adminID))")
    conn.close()
#viewing the table content
def view_data_with_pandas(dbname):
    conn = sqlite3.connect(dbname)

    # Display raw data from the database for debugging


    # Query data into a pandas DataFrame for formatted display
    df = pd.read_sql_query("SELECT userID, full_name, username, password, email, telephone, address FROM user", conn)

    # Display DataFrame content with all columns
    pd.set_option('display.max_columns', None)  # Ensure all columns are shown
    pd.set_option('display.width', 1000)  # Increase console width for display
    print(df)

    conn.close()


#resetting the data in the table
def reset_database(dbname):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    try:
        # List of all tables to reset
        tables = [
            "user",
            "registeredUser",
            "admin",
            "fitnessPlan",
            "content",
            "exercise",
            "workoutSession",
            "issueForm"
        ]

        # Disable foreign key checks to avoid constraint issues while deleting
        c.execute("PRAGMA foreign_keys = OFF;")

        # Clear all tables
        for table in tables:
            c.execute(f"DELETE FROM {table};")  # Delete all rows

        # Re-enable foreign key checks
        c.execute("PRAGMA foreign_keys = ON;")

        conn.commit()  # Save changes
        print("Database reset successfully. All data has been deleted.")
    except sqlite3.Error as e:
        print(f"Database error during reset: {e}")
    finally:
        conn.close()


def register(dbname, fullname=None, username=None, password=None, email=None, telephone=None, address=None,
             google_register=False):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    if google_register:
        # For Google registration: Only email and password are needed
        if not email or not password:
            print("Error: Email and password are required for Google registration.")
            return

        # Check if the email already exists in the user table
        c.execute("SELECT * FROM user WHERE email = ?", (email,))
        if c.fetchone():
            print("Error: Email already registered. Please use a different email.")
            return

        # Register the user with email and password only (no full_name, username, etc.)
        try:
            c.execute("INSERT INTO user(email, password) VALUES (?, ?)", (email, password))
            conn.commit()
            print("User registered with Google successfully!")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()
    else:
        # Regular registration: Full details required
        email_format = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        telephone_format = re.compile(r'^\+?\d{1,4}?[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}$')
        password_format = re.compile(
            r'^(?=.*\d)(?=.*[A-Za-z])(?=.*[\W_]).{8,}$')  # Minimum 8 chars, 1 digit, 1 special char

        # Validate the full user details for regular registration
        try:
            # Check if the username already exists
            c.execute("SELECT * FROM user WHERE username = ?", (username,))
            if c.fetchone():
                print("Username already exists")
                return

            # Check email format
            if not email_format.match(email):
                print("Invalid email address")
                return

            # Check if the email already exists in the user table
            c.execute("SELECT * FROM user WHERE email = ?", (email,))
            if c.fetchone():
                print("Error: Email already exists. Please use a different email.")
                return

            # Check telephone format
            if not telephone_format.match(telephone):
                print("Invalid telephone number format")
                return

            # Check password format
            if not password_format.match(password):
                print(
                    "Password must be at least 8 characters long, contain at least one digit, and one special character.")
                return

            # Insert the new user into the user table
            c.execute("INSERT INTO user(full_name, username, password, email, telephone, address) VALUES (?,?,?,?,?,?)",
                      (fullname, username, password, email, telephone, address))
            conn.commit()
            print("User registered successfully!")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()


def login(dbname,username,password):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    try:
        # Checking if the username exists
        c.execute("SELECT password FROM user WHERE username = ?", (username,))
        user = c.fetchone()

        if not user:
            print("The username is incorrect.")
            return
        # Validating the password
        if user[0] != password:
            print("The password is incorrect.")
            return

        # Successful login
        print("Login successful! Welcome,", username)

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

#updating registered user profile details
def updateUserprofile(dbname, userID):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    try:
        # Check if the user exists
        c.execute("SELECT * FROM user WHERE userID = ?", (userID,))
        user = c.fetchone()

        if not user:
            print("Error: User with userID {} does not exist.".format(userID))
            return

        print("Updating user profile. Leave a field blank if you don't want to update it.")

        # Gather updated details from the user
        new_full_name = input("Enter new full name (or press Enter to skip): ").strip()
        new_username = input("Enter new username (or press Enter to skip): ").strip()
        new_password = input("Enter new password (or press Enter to skip): ").strip()
        new_email = input("Enter new email (or press Enter to skip): ").strip()
        new_telephone = input("Enter new telephone (or press Enter to skip): ").strip()
        new_address = input("Enter new address (or press Enter to skip): ").strip()

        # Dictionary to store updated fields
        updates = {}
        if new_full_name:
            updates["full_name"] = new_full_name
        if new_username:
            c.execute("SELECT * FROM user WHERE username = ?", (new_username,))
            if c.fetchone():
                print("Error: Username already exists.")
                return
            updates["username"] = new_username
        if new_password:
            password_format = re.compile(r'^(?=.*\d)(?=.*[A-Za-z])(?=.*[\W_]).{8,}$')  # Password format
            if not password_format.match(new_password):
                print("Error: Password must be at least 8 characters long, include at least one digit, one special character, and one letter.")
                return
            updates["password"] = new_password
        if new_email:
            email_format = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_format.match(new_email):
                print("Error: Invalid email format.")
                return
            c.execute("SELECT * FROM user WHERE email = ?", (new_email,))
            if c.fetchone():
                print("Error: Email already exists.")
                return
            updates["email"] = new_email
        if new_telephone:
            telephone_format = re.compile(r'^\+?\d{1,4}?[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}$')
            if not telephone_format.match(new_telephone):
                print("Error: Invalid telephone number format.")
                return
            updates["telephone"] = new_telephone
        if new_address:
            updates["address"] = new_address

        # Update the database with the provided details
        if updates:
            set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values()) + [userID]
            query = f"UPDATE user SET {set_clause} WHERE userID = ?"
            c.execute(query, values)
            conn.commit()
            print("User profile updated successfully.")
        else:
            print("No updates provided. User profile remains unchanged.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


def workoutHistory(dbname, userID):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    try:
        # Check if the user exists in the registeredUser table
        c.execute("SELECT * FROM registeredUser WHERE userID = ?", (userID,))
        user = c.fetchone()
        if not user:
            print("You are not registered yet.")
            return

        # Query workout sessions for the user
        c.execute("SELECT sessionID, date, duration, postureAccuracy FROM workoutSession WHERE userID = ?", (userID,))
        sessions = c.fetchall()

        if not sessions:
            print("Error: You have not done any workout sessions yet.")
            return

        # Format and display the workout history
        print("Workout history for userID", userID)
        for session in sessions:
            print("Session ID:{}, Date:{}, Duration:{}, PostureAccuracy:{}".format(session[0], session[1], session[2], session[3]))

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def accessWorkoutLibrary(dbname):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    try:
        # Fetch exercise details
        c.execute("SELECT * FROM exercise")
        exercises = c.fetchall()

        if not exercises:
            # If no exercises are available, return an error message
            return {"error": "No exercise sets available."}, 404

        # Format and display the exercise data
        exercise_data = []
        for exercise in exercises:
            exercise_data.append({
                "exerciseID": exercise[0],
                "name": exercise[1],
                "category": exercise[2],
                "targetedBodyParts": exercise[3],
                "requiredEquipment": exercise[4]
            })

        return {"exercises": exercise_data}, 200

    except sqlite3.Error as e:
        return {"error": f"Database error: {e}"}, 500
    finally:
        conn.close()

def insert_exercise_sets(dbname):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    exercises = [
        ("Planks", "Core", "Abdominals, Back", "None"),
        ("Push-ups", "Upper Body", "Chest, Shoulders, Triceps", "None"),
        ("Squats", "Lower Body", "Quads, Hamstrings, Glutes", "None"),
        ("Lunges", "Lower Body", "Quads, Hamstrings, Glutes", "None"),
        ("Bicep Curls", "Upper Body", "Biceps", "Dumbbells"),
        ("Deadlifts", "Full Body", "Back, Legs, Core", "Barbell"),
        ("Pull-ups", "Upper Body", "Back, Biceps", "Pull-up Bar"),
        ("Leg Press", "Lower Body", "Quads, Hamstrings, Glutes", "Leg Press Machine"),
        ("Bench Press", "Upper Body", "Chest, Shoulders, Triceps", "Barbell"),
        ("Mountain Climbers", "Cardio", "Core, Shoulders", "None")
    ]

    try:
        # Insert exercise sets into the exercise table
        c.executemany("INSERT INTO exercise (name, category, targetedBodyParts, requieredEquipment) VALUES (?, ?, ?, ?)", exercises)
        conn.commit()
        print("Exercise sets inserted successfully!")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


def fitnessPlan(dbname):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    try:
        print("Enter your fitness plan details:")

        # Input gender with validation
        gender = input("Enter gender (Male/Female): ").strip().capitalize()
        if gender not in ["Male", "Female"]:
            print("Error: Gender must be 'Male' or 'Female'.")
            return

        # Input height with validation
        try:
            height = float(input("Enter height in cm: ").strip())
            if height <= 0:
                print("Error: Height must be a positive number.")
                return
        except ValueError:
            print("Error: Invalid height input. Please enter a numeric value.")
            return

        # Input weight with validation
        try:
            weight = float(input("Enter weight in kg: ").strip())
            if weight <= 0:
                print("Error: Weight must be a positive number.")
                return
        except ValueError:
            print("Error: Invalid weight input. Please enter a numeric value.")
            return

        # Insert the fitness plan into the database
        c.execute("INSERT INTO fitnessPlan (gender, height, weight) VALUES (?, ?, ?)", (gender, height, weight))
        conn.commit()
        print("Fitness plan added successfully!")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    createDB('fitness.db')

    print("Testing user registration...")

    # Example user details
    full_name = "Berkay Soyak"
    user_name = "godfather2003"
    Password = "berkay_soyak2003"
    Email = "Berkaysoyak@gmail.com"
    Telephone = "0548863232"
    Address = "Bellapais Kpet karsısı"
    Age = 21
    Height = 180.5
    Weight = 75.3
    Goals = "Lose Weight"

    # Registering user (not with google)
    register('fitness.db', full_name, user_name, Password, Email, Telephone, Address)

    # Register with google
    #register('fitness.db', email="Berkaysoyak@gmail.com", password="berkay_soyak2003", google_register=True)

    # Login for user
    login('fitness.db', "godfather2003", "berkay_soyak2003")
    login('fitness.db', "godfather2003", "incorrect_password")


    # Reset database
    #reset_database('fitness.db')
    insert_exercise_sets('fitness.db')

    # Viewing the table contents
    view_data_with_pandas('fitness.db')