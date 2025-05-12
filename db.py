import sqlite3
import re
import pandas as pd

# update for commit
def createDB(dbname):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    # Drop old profile table to recreate merged schema
    c.execute("DROP TABLE IF EXISTS createProfile")

    c.execute(
        "CREATE TABLE IF NOT EXISTS user_new("
        "userID INTEGER PRIMARY KEY, "
        "full_name TEXT NOT NULL, "
        "username TEXT NOT NULL, "
        "password TEXT NOT NULL, "
        "role TEXT NOT NULL DEFAULT 'user', "
        "email TEXT NOT NULL, "
        "gender TEXT, "
        "height DOUBLE, "
        "weight DOUBLE, "
        "profilepic TEXT, "
        "birth_date DATE, "
        "fitness_goal TEXT, "
        "activity_level TEXT, "
        "isActive BOOLEAN DEFAULT 1"
        ")"
    )

    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if c.fetchone():
            c.execute(
                "INSERT INTO user_new(userID, full_name, username, password, role, email) "
                "SELECT userID, full_name, username, password, 'user', email FROM user"
            )
            # Merge profile data if exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='createProfile'")
            if c.fetchone():
                c.execute(
                    "UPDATE user_new SET "
                    "gender = (SELECT gender FROM createProfile WHERE createProfile.userID = user_new.userID), "
                    "height = (SELECT height FROM createProfile WHERE createProfile.userID = user_new.userID), "
                    "weight = (SELECT weight FROM createProfile WHERE createProfile.userID = user_new.userID), "
                    "profilepic = (SELECT profilepic FROM createProfile WHERE createProfile.userID = user_new.userID), "
                    "birth_date = (SELECT birth_date FROM createProfile WHERE createProfile.userID = user_new.userID), "
                    "fitness_goal = (SELECT fitness_goal FROM createProfile WHERE createProfile.userID = user_new.userID), "
                    "activity_level = (SELECT activity_level FROM createProfile WHERE createProfile.userID = user_new.userID) "
                    "WHERE EXISTS (SELECT 1 FROM createProfile WHERE createProfile.userID = user_new.userID)"
                )
            # Drop old and rename
            c.execute("DROP TABLE IF EXISTS user")
            c.execute("ALTER TABLE user_new RENAME TO user")
        else:
            # No existing user table
            c.execute("ALTER TABLE user_new RENAME TO user")
    except sqlite3.Error as e:
        print(f"Error during data migration: {e}")

    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(user)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'role' not in columns:
        cursor.execute("ALTER TABLE user ADD COLUMN role TEXT DEFAULT 'user'")

    # Content table
    c.execute("CREATE TABLE IF NOT EXISTS content(contentID INTEGER PRIMARY KEY, "
              "type TEXT NOT NULL, "
              "description TEXT NOT NULL, "
              "title TEXT NOT NULL)")

    # Exercise table
    c.execute("CREATE TABLE IF NOT EXISTS exercise(exerciseID INTEGER PRIMARY KEY, "
              "name TEXT NOT NULL, "
              "category TEXT NOT NULL, "
              "targetedBodyParts TEXT NOT NULL, "
              "requieredEquipment TEXT NOT NULL, "
              "videoURL TEXT)")

    # Workout Session table
    c.execute("CREATE TABLE IF NOT EXISTS workoutSession(sessionID INTEGER PRIMARY KEY, "
              "date DATETIME NOT NULL, "
              "duration TIMESTAMP NOT NULL, "
              "postureAccuracy DOUBLE NOT NULL, "
              "userID INTEGER NOT NULL, "
              "FOREIGN KEY(userID) REFERENCES user(userID))")

    # Issue Form table
    c.execute("CREATE TABLE IF NOT EXISTS issueForm(issueID INTEGER PRIMARY KEY, "
              "description TEXT NOT NULL, "
              "status TEXT NOT NULL, "
              "userID INTEGER NOT NULL, "
              "adminID INTEGER NOT NULL, "
              "FOREIGN KEY(userID) REFERENCES user(userID), "
              "FOREIGN KEY(adminID) REFERENCES admin(adminID))")

    conn.commit()
    conn.close()


def view_data_with_pandas(dbname):
    conn = sqlite3.connect(dbname)
    df = pd.read_sql_query(
        "SELECT userID, full_name, username, password, role, email FROM user", conn
    )
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(df)
    conn.close()


def reset_database(dbname):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    try:
        tables = [
            "user",
            "content",
            "exercise",
            "workoutSession",
            "issueForm"
        ]
        c.execute("PRAGMA foreign_keys = OFF;")
        for table in tables:
            c.execute(f"DELETE FROM {table};")
        c.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        print("Database reset successfully. All data has been deleted.")
    except sqlite3.Error as e:
        print(f"Database error during reset: {e}")
    finally:
        conn.close()

def register(dbname, fullname=None, username=None, password=None, email=None,
             google_register=False):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    if google_register:
        # For Google registration only email and password are needed
        if not email or not password:
            print("Error: Email and password are required for Google registration.")
            return
        c.execute("SELECT * FROM user WHERE email = ?", (email,))
        if c.fetchone():
            print("Error: Email already registered. Please use a different email.")
            return
        try:
            c.execute("INSERT INTO user(email, password, isActive) VALUES (?, ?, 1)", (email, password))
            conn.commit()
            print("User registered with Google successfully!")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()
    else:
        # Regular registration: Full details required
        email_format = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        password_format = re.compile(r'^(?=.*\d)(?=.*[A-Za-z])(?=.*[\W_]).{8,}$')
        try:
            c.execute("SELECT * FROM user WHERE username = ?", (username,))
            if c.fetchone():
                print("Username already exists")
                return
            if not email_format.match(email):
                print("Invalid email address")
                return
            c.execute("SELECT * FROM user WHERE email = ?", (email,))
            if c.fetchone():
                print("Error: Email already exists. Please use a different email.")
                return
            if not password_format.match(password):
                print(
                    "Password must be at least 8 characters long, contain at least one digit, and one special character.")
                return
            c.execute("INSERT INTO user(full_name, username, password, email, isActive) VALUES (?,?,?,?,1)",
                      (fullname, username, password, email))
            conn.commit()
            print("User registered successfully!")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()


def login(dbname, username, password):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    try:
        c.execute("SELECT password FROM user WHERE username = ?", (username,))
        user = c.fetchone()
        if not user:
            print("The username is incorrect.")
            return
        if user[0] != password:
            print("The password is incorrect.")
            return
        print("Login successful! Welcome,", username)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


# Updating user profile details
def updateUserprofile(dbname, userID):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM user WHERE userID = ?", (userID,))
        user = c.fetchone()
        if not user:
            print("Error: User with userID {} does not exist.".format(userID))
            return
        print("Updating user profile. Leave a field blank if you don't want to update it.")
        
        # Account information
        new_full_name = input("Enter new full name (or press Enter to skip): ").strip()
        new_username = input("Enter new username (or press Enter to skip): ").strip()
        new_password = input("Enter new password (or press Enter to skip): ").strip()
        new_email = input("Enter new email (or press Enter to skip): ").strip()
        
        # Profile information
        new_gender = input("Enter new gender (Male/Female) (or press Enter to skip): ").strip().capitalize()
        if new_gender and new_gender not in ["Male", "Female"]:
            print("Error: Gender must be 'Male' or 'Female'.")
            return
            
        new_height = input("Enter new height in cm (or press Enter to skip): ").strip()
        if new_height:
            try:
                new_height = float(new_height)
                if new_height <= 0:
                    print("Error: Height must be a positive number.")
                    return
            except ValueError:
                print("Error: Invalid height input. Please enter a numeric value.")
                return
                
        new_weight = input("Enter new weight in kg (or press Enter to skip): ").strip()
        if new_weight:
            try:
                new_weight = float(new_weight)
                if new_weight <= 0:
                    print("Error: Weight must be a positive number.")
                    return
            except ValueError:
                print("Error: Invalid weight input. Please enter a numeric value.")
                return
                
        print("Enter new base64 encoded profile picture (or press Enter to skip):")
        new_profilepic = input().strip()
        if new_profilepic:
            try:
                import base64
                base64.b64decode(new_profilepic)
            except Exception:
                print("Error: Invalid base64 encoded string for profile picture.")
                return
                
        new_birth_date = input("Enter new birth date (YYYY-MM-DD) (or press Enter to skip): ").strip()
        new_fitness_goal = input("Enter new fitness goal (or press Enter to skip): ").strip()
        new_activity_level = input("Enter new activity level (or press Enter to skip): ").strip()
        
        is_active_input = input("Is user active? (yes/no) (or press Enter to skip): ").strip().lower()
        new_is_active = None
        if is_active_input:
            if is_active_input in ['yes', 'y', 'true', '1']:
                new_is_active = 1
            elif is_active_input in ['no', 'n', 'false', '0']:
                new_is_active = 0
            else:
                print("Error: Invalid input for active status. Please use yes/no.")
                return

        updates = {}
        if new_full_name:
            updates["full_name"] = new_full_name
        if new_username:
            c.execute("SELECT * FROM user WHERE username = ? AND userID != ?", (new_username, userID))
            if c.fetchone():
                print("Error: Username already exists.")
                return
            updates["username"] = new_username
        if new_password:
            password_format = re.compile(r'^(?=.*\d)(?=.*[A-Za-z])(?=.*[\W_]).{8,}$')
            if not password_format.match(new_password):
                print(
                    "Error: Password must be at least 8 characters long, include at least one digit, one special character, and one letter.")
                return
            updates["password"] = new_password
        if new_email:
            email_format = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_format.match(new_email):
                print("Error: Invalid email format.")
                return
            c.execute("SELECT * FROM user WHERE email = ? AND userID != ?", (new_email, userID))
            if c.fetchone():
                print("Error: Email already exists.")
                return
            updates["email"] = new_email
        if new_gender:
            updates["gender"] = new_gender
        if new_height:
            updates["height"] = new_height
        if new_weight:
            updates["weight"] = new_weight
        if new_profilepic:
            updates["profilepic"] = new_profilepic
        if new_birth_date:
            updates["birth_date"] = new_birth_date
        if new_fitness_goal:
            updates["fitness_goal"] = new_fitness_goal
        if new_activity_level:
            updates["activity_level"] = new_activity_level
        if new_is_active is not None:
            updates["isActive"] = new_is_active
            
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
        c.execute("SELECT * FROM user WHERE userID = ?", (userID,))
        user = c.fetchone()
        if not user:
            print("You are not registered yet.")
            return
        c.execute("SELECT sessionID, date, duration, postureAccuracy FROM workoutSession WHERE userID = ?", (userID,))
        sessions = c.fetchall()
        if not sessions:
            print("Error: You have not done any workout sessions yet.")
            return
        print("Workout history for userID", userID)
        for session in sessions:
            print("Session ID:{}, Date:{}, Duration:{}, PostureAccuracy:{}".format(session[0], session[1], session[2],
                                                                                   session[3]))
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


def accessWorkoutLibrary(dbname):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM exercise")
        exercises = c.fetchall()
        if not exercises:
            return {"error": "No exercise sets available."}, 404
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
        ("Squats", "Lower Body", "Quads, Hamstrings, Glutes", "None"),
        ("Lunges", "Lower Body", "Quads, Hamstrings, Glutes", "None"),
    ]
    try:
        c.executemany(
            "INSERT INTO exercise (name, category, targetedBodyParts, requieredEquipment) VALUES (?, ?, ?, ?)",
            exercises)
        conn.commit()
        print("Exercise sets inserted successfully!")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


def create_profile(dbname):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    try:
        print("Enter your profile details:")
        userID = int(input("Enter your user ID: ").strip())

        c.execute("SELECT * FROM user WHERE userID = ?", (userID,))
        if not c.fetchone():
            print("Error: User with this ID does not exist.")
            return

        c.execute("SELECT gender FROM user WHERE userID = ? AND gender IS NOT NULL", (userID,))
        if c.fetchone():
            print("Error: Profile already exists for this user. Please use updateUserProfile to modify it.")
            return
            
        gender = input("Enter gender (Male/Female): ").strip().capitalize()
        if gender not in ["Male", "Female"]:
            print("Error: Gender must be 'Male' or 'Female'.")
            return
        try:
            height = float(input("Enter height in cm: ").strip())
            if height <= 0:
                print("Error: Height must be a positive number.")
                return
        except ValueError:
            print("Error: Invalid height input. Please enter a numeric value.")
            return
        try:
            weight = float(input("Enter weight in kg: ").strip())
            if weight <= 0:
                print("Error: Weight must be a positive number.")
                return
        except ValueError:
            print("Error: Invalid weight input. Please enter a numeric value.")
            return

        print("Enter base64 encoded profile picture (or press Enter to skip):")
        profilepic = input().strip()
        if profilepic:
            try:
                import base64
                base64.b64decode(profilepic)
            except Exception:
                print("Error: Invalid base64 encoded string for profile picture.")
                return
                
        birth_date = input("Enter birth date (YYYY-MM-DD): ").strip()
        fitness_goal = input("Enter fitness goal: ").strip()
        activity_level = input("Enter activity level: ").strip()

        c.execute(
            "UPDATE user SET gender = ?, height = ?, weight = ?, profilepic = ?, "
            "birth_date = ?, fitness_goal = ?, activity_level = ? WHERE userID = ?",
            (gender, height, weight, profilepic, birth_date, fitness_goal, activity_level, userID))
        
        conn.commit()
        print("Profile updated successfully!")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


def initialize_database(dbname='fitness.db'):
    createDB(dbname)

    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM exercise")
    exercise_count = c.fetchone()[0]
    conn.close()

    if exercise_count == 0:
        insert_exercise_sets(dbname)
        print("Exercise database initialized with default exercises.")
    
    return True


if __name__ == '__main__':
    initialize_database()
    print("Database initialized successfully.")
