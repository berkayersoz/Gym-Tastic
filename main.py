from flask import Flask, request, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
import sqlite3
import re
import os
import hashlib

app = Flask(__name__)

# Database creation function
def createDB(dbname):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS user(userID INTEGER PRIMARY KEY, "
              "full_name TEXT NOT NULL,"
              "username TEXT NOT NULL,"
              "password TEXT NOT NULL,"
              "email TEXT NOT NULL,"
              "telephone TEXT NOT NULL,"
              "address TEXT NOT NULL)")
    #Workout Session table
    c.execute("CREATE TABLE IF NOT EXISTS workoutSession(sessionID INTEGER PRIMARY KEY,"
              "date DATETIME NOT NULL,"
              "duration TIMESTAMP NOT NULL,"
              "postureAccuracy DOUBLE NOT NULL,"
              "userID INTEGER NOT NULL,"
              "FOREIGN KEY(userID) REFERENCES user(userID))")

    #Exercise table
    c.execute("CREATE TABLE IF NOT EXISTS exercise(exerciseID INTEGER PRIMARY KEY, "
              "name TEXT NOT NULL,"
              "category TEXT NOT NULL,"
              "targetedBodyParts TEXT NOT NULL,"
              "requieredEquipment TEXT NOT NULL,"
              "videoURL TEXT NOT NULL)")

    # Fitness Plan table
    c.execute("CREATE TABLE IF NOT EXISTS fitnessPlan(planID INTEGER PRIMARY KEY,"
              "gender TEXT NOT NULL"
              ",height DOUBLE NOT NULL,"
              "weight DOUBLE NOT NULL,"
              "userID INTEGER NOT NULL,"
              "FOREIGN KEY(userID) REFERENCES user(userID))")


    conn.commit()

    conn.close()




# API Endpoint: Register a new user
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    try:
        # Retrieve input data
        full_name = data.get('full_name')
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        telephone = data.get('telephone')
        address = data.get('address')
        google_register = data.get('google_register', False)

        # Common validation patterns
        email_format = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        telephone_format = re.compile(r'^\+?\d{1,4}?[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}$')
        password_format = re.compile(r'^(?=.*\d)(?=.*[A-Za-z])(?=.*[\W_]).{8,}$')  # At least 8 chars, 1 digit, 1 special char

        if google_register:
            # Validate email and password for Google registration
            if not email or not password:
                return jsonify({"error": "Email and password are required for Google registration"}), 400

            if not email_format.match(email):
                return jsonify({"error": "Invalid email format"}), 400

            # Check if email is already registered
            c.execute("SELECT * FROM user WHERE email = ?", (email,))
            if c.fetchone():
                return jsonify({"error": "Email already registered. Please use a different email"}), 400

            # Register user with email and password only
            c.execute("INSERT INTO user(email, password) VALUES (?, ?)", (email, password))
            conn.commit()
            return jsonify({"message": "User registered with Google successfully"}), 201

        else:
            # Validate full registration data
            if not all([full_name, username, password, email, telephone, address]):
                return jsonify({"error": "All fields are required"}), 400

            # Check if the username already exists
            c.execute("SELECT * FROM user WHERE username = ?", (username,))
            if c.fetchone():
                return jsonify({"error": "Username already exists"}), 400

            # Validate email format and uniqueness
            if not email_format.match(email):
                return jsonify({"error": "Invalid email format"}), 400

            c.execute("SELECT * FROM user WHERE email = ?", (email,))
            if c.fetchone():
                return jsonify({"error": "Email already exists. Please use a different email"}), 400

            # Validate telephone format
            if not telephone_format.match(telephone):
                return jsonify({"error": "Invalid telephone number format"}), 400

            # Validate password strength
            if not password_format.match(password):
                return jsonify({
                    "error": "Password must be at least 8 characters long, contain at least one digit, and one special character"
                }), 400

            # Insert the user into the database
            c.execute(
                "INSERT INTO user(full_name, username, password, email, telephone, address) VALUES (?, ?, ?, ?, ?, ?)",
                (full_name, username, password, email, telephone, address)
            )
            conn.commit()
            return jsonify({"message": "User registered successfully"}), 201

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# API Endpoint: Login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    try:
        username = data.get('username')
        password = data.get('password')

        # Validate credentials
        c.execute("SELECT password FROM user WHERE username = ?", (username,))
        user = c.fetchone()

        if not user:
            return jsonify({"error": "Username not found"}), 404
        if user[0] != password:
            return jsonify({"error": "Incorrect password"}), 401

        return jsonify({"message": f"Welcome, {username}!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# API Endpoint: Fetch Workout History
@app.route('/workoutHistory/<int:userID>', methods=['GET'])
def workout_history(userID):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    try:
        # Check if the user exists
        c.execute("SELECT * FROM user WHERE userID = ?", (userID,))
        user = c.fetchone()
        if not user:
            return jsonify({"error": "User not found. Please register first."}), 404

        # Fetch workout sessions
        c.execute("SELECT sessionID, date, duration, postureAccuracy FROM workoutSession WHERE userID = ?", (userID,))
        sessions = c.fetchall()

        if not sessions:
            return jsonify({"error": "No workout sessions found for this user."}), 404

        # Format workout history
        workout_data = []
        for session in sessions:
            workout_data.append({
                "sessionID": session[0],
                "date": session[1],
                "duration": session[2],
                "postureAccuracy": session[3]
            })

        return jsonify({
            "userID": userID,
            "workoutHistory": workout_data
        }), 200

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        conn.close()


@app.route('/workoutLibrary', methods=['GET'])
def accessWorkoutLibrary():
    dbname = 'fitness.db'  # Assuming this is your database name
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    try:
        # Fetch exercise details
        exercises =[
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

        # Check and insert only unique exercises
        for exercise in exercises:
            c.execute(
                "SELECT * FROM exercise WHERE name = ? AND category = ? AND targetedBodyParts = ? AND requieredEquipment = ?",
                (exercise[0], exercise[1], exercise[2], exercise[3]))
            existing_exercise = c.fetchone()

            if not existing_exercise:
                # Insert exercise if not already in the database
                c.execute(
                    "INSERT INTO exercise (name, category, targetedBodyParts, requieredEquipment) VALUES (?, ?, ?, ?)",
                    (exercise[0], exercise[1], exercise[2], exercise[3]))

        conn.commit()

        # Fetch all exercises to display
        c.execute("SELECT * FROM exercise")
        exercises = c.fetchall()

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

        return jsonify({"exercises": exercise_data}), 200

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        conn.close()


@app.route('/resetWorkoutLibrary', methods=['POST'])
def resetWorkoutLibrary():
    dbname = 'fitness.db'  # Assuming this is your database name
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    try:
        # Delete all exercises from the workout library
        c.execute("DELETE FROM exercise")
        conn.commit()

        return jsonify({"message": "Workout library has been reset."}), 200

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        conn.close()

@app.route('/startWorkout', methods=['POST'])
def startWorkout():
    data = request.json
    dbname = 'fitness.db'
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    try:
        # Retrieve input data
        user_id = data.get('userID')
        exercise_id = data.get('exerciseID')
        duration = data.get('duration')  # Duration in minutes

        if not all([user_id, exercise_id, duration]):
            return jsonify({"error": "All fields (userID, exerciseID, duration) are required."}), 400

        # Check if user exists
        c.execute("SELECT * FROM user WHERE userID = ?", (user_id,))
        user = c.fetchone()
        if not user:
            return jsonify({"error": "User not found. Please register first."}), 404

        # Check if exercise exists
        c.execute("SELECT * FROM exercise WHERE exerciseID = ?", (exercise_id,))
        exercise = c.fetchone()
        if not exercise:
            return jsonify({"error": f"Exercise with ID {exercise_id} not found in the workout library."}), 404

        # Insert a new workout session
        from datetime import datetime
        session_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Current date and time
        posture_accuracy = 0.0  # Default value; can be updated later

        c.execute(
            "INSERT INTO workoutSession (date, duration, postureAccuracy, userID) VALUES (?, ?, ?, ?)",
            (session_date, duration, posture_accuracy, user_id)
        )
        conn.commit()

        return jsonify({
            "message": "Workout session started successfully.",
            "userID": user_id,
            "exerciseID": exercise_id,
            "duration": duration
        }), 201

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        conn.close()

import hashlib
import os
import sqlite3
import re
from flask import request, jsonify

@app.route('/updateUserProfile/<int:userID>', methods=['GET', 'PUT'])
def update_user_profile(userID):
    dbname = 'fitness.db'
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    try:
        # Check if the user exists
        c.execute("SELECT * FROM user WHERE userID = ?", (userID,))
        user = c.fetchone()

        if not user:
            return jsonify({"error": f"User with userID {userID} does not exist."}), 404

        if request.method == 'GET':
            # Fetch and return the current user details
            user_details = {
                "userID": user[0],
                "full_name": user[1],
                "username": user[2],
                "email": user[4],
                "telephone": user[5],
                "address": user[6]
            }
            return jsonify({"userDetails": user_details}), 200

        elif request.method == 'PUT':
            # Fetch current user details first before updating
            current_user_details = {
                "userID": user[0],
                "full_name": user[1],
                "username": user[2],
                "email": user[4],
                "telephone": user[5],
                "address": user[6]
            }

            # Return current details and allow user to submit updated data
            data = request.json
            updates = {}

            # Only apply updates if the user provides new values
            if 'full_name' in data and data['full_name'] and data['full_name'] != current_user_details['full_name']:
                updates['full_name'] = data['full_name']
            if 'username' in data and data['username'] and data['username'] != current_user_details['username']:
                # Check if the new username is already taken
                c.execute("SELECT * FROM user WHERE username = ?", (data['username'],))
                if c.fetchone():
                    return jsonify({"error": "Username already exists."}), 400
                updates['username'] = data['username']
            if 'password' in data and data['password']:
                password_format = re.compile(r'^(?=.*\d)(?=.*[A-Za-z])(?=.*[\W_]).{8,}$')
                if not password_format.match(data['password']):
                    return jsonify({
                        "error": "Password must be at least 8 characters long, include at least one digit, one special character, and one letter."
                    }), 400

                # Hash the password using hashlib
                salt = os.urandom(16)  # Generate a random salt
                hashed_password = hashlib.sha256(salt + data['password'].encode('utf-8')).hexdigest()

                # Store the hashed password and salt
                updates['password'] = hashed_password
                updates['salt'] = salt.hex()  # Store the salt in hex format
            if 'email' in data and data['email'] and data['email'] != current_user_details['email']:
                email_format = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
                if not email_format.match(data['email']):
                    return jsonify({"error": "Invalid email format."}), 400
                c.execute("SELECT * FROM user WHERE email = ?", (data['email'],))
                if c.fetchone():
                    return jsonify({"error": "Email already exists."}), 400
                updates['email'] = data['email']
            if 'telephone' in data and data['telephone'] and data['telephone'] != current_user_details['telephone']:
                telephone_format = re.compile(r'^\+?\d{1,4}?[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}$')
                if not telephone_format.match(data['telephone']):
                    return jsonify({"error": "Invalid telephone number format."}), 400
                updates['telephone'] = data['telephone']
            if 'address' in data and data['address'] and data['address'] != current_user_details['address']:
                updates['address'] = data['address']

            # If there are updates, apply them to the database
            if updates:
                set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
                values = list(updates.values()) + [userID]
                query = f"UPDATE user SET {set_clause} WHERE userID = ?"
                c.execute(query, values)
                conn.commit()
                return jsonify({"message": "User profile updated successfully."}), 200
            else:
                return jsonify({"error": "No updates provided. User profile remains unchanged."}), 400

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        conn.close()






@app.route('/fitnessPlan', methods=['POST', 'GET'])
def fitnessPlan():
    dbname = 'fitness.db'
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    try:
        if request.method == 'POST':
            # Add a new fitness plan
            data = request.json
            user_id = data.get('userID')
            gender = data.get('gender')
            height = data.get('height')
            weight = data.get('weight')

            # Check if all required fields are provided
            if not all([user_id, gender, height, weight]):
                return jsonify({"error": "userID, gender, height, and weight are required."}), 400
            elif height < 0:
                return jsonify({"error": "Height should be a positive value."}), 400
            elif weight < 0:
                return jsonify({"error": "Weight should be a positive value."}), 400

            # Check if the user exists
            c.execute("SELECT * FROM user WHERE userID = ?", (user_id,))
            user = c.fetchone()

            if not user:
                return jsonify({"error": "No registered user found with the provided userID."}), 404

            # Insert fitness plan into the database
            c.execute(
                "INSERT INTO fitnessPlan (userID, gender, height, weight) VALUES (?, ?, ?, ?)",
                (user_id, gender, height, weight)
            )
            conn.commit()

            return jsonify({
                "message": "Fitness plan created successfully.",
                "fitnessPlan": {
                    "planID": c.lastrowid,
                    "userID": user_id,
                    "gender": gender,
                    "height": height,
                    "weight": weight
                }
            }), 201

        elif request.method == 'GET':
            # Retrieve fitness plans for a specific userID
            user_id = request.args.get('userID')

            if not user_id:
                return jsonify({"error": "userID is required."}), 400

            # Check if the user exists
            c.execute("SELECT * FROM user WHERE userID = ?", (user_id,))
            user = c.fetchone()

            if not user:
                return jsonify({"error": "No registered user found with the provided userID."}), 404

            # Fetch the fitness plans
            c.execute("SELECT * FROM fitnessPlan WHERE userID = ?", (user_id,))
            plans = c.fetchall()

            if not plans:
                return jsonify({"message": "No fitness plans found for this user."}), 404

            plan_data = []
            for plan in plans:
                plan_data.append({
                    "planID": plan[0],
                    "userID": plan[1],
                    "gender": plan[2],
                    "height": plan[3],
                    "weight": plan[4]
                })

            return jsonify({"fitnessPlans": plan_data}), 200

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        conn.close()


@app.route('/exerciseVideos', methods=['GET'])
def exercise_videos():
    dbname = 'fitness.db'  # Assuming this is your database name
    conn = sqlite3.connect(dbname)
    c = conn.cursor()

    try:
        # Add videoURL column if it doesn't exist
        c.execute("PRAGMA table_info(exercise)")
        columns = [column[1] for column in c.fetchall()]
        if "videoURL" not in columns:
            c.execute("ALTER TABLE exercise ADD COLUMN videoURL TEXT")
            conn.commit()

        # Insert exercises with video URLs
        exercises_with_videos = [
            ("Planks", "Core", "Abdominals, Back", "None", "https://youtu.be/video_for_planks"),
            ("Push-ups", "Upper Body", "Chest, Shoulders, Triceps", "None", "https://youtu.be/video_for_pushups"),
            ("Squats", "Lower Body", "Quads, Hamstrings, Glutes", "None", "https://youtu.be/video_for_squats"),
            ("Lunges", "Lower Body", "Quads, Hamstrings, Glutes", "None", "https://youtu.be/video_for_lunges"),
            ("Bicep Curls", "Upper Body", "Biceps", "Dumbbells", "https://youtu.be/video_for_bicep_curls"),
            ("Deadlifts", "Full Body", "Back, Legs, Core", "Barbell", "https://youtu.be/video_for_deadlifts"),
            ("Pull-ups", "Upper Body", "Back, Biceps", "Pull-up Bar", "https://youtu.be/video_for_pullups"),
            ("Leg Press", "Lower Body", "Quads, Hamstrings, Glutes", "Leg Press Machine", "https://youtu.be/video_for_leg_press"),
            ("Bench Press", "Upper Body", "Chest, Shoulders, Triceps", "Barbell", "https://youtu.be/video_for_bench_press"),
            ("Mountain Climbers", "Cardio", "Core, Shoulders", "None", "https://youtu.be/video_for_mountain_climbers"),
        ]

        for exercise in exercises_with_videos:
            c.execute(
                "SELECT * FROM exercise WHERE name = ? AND category = ? AND targetedBodyParts = ? AND requieredEquipment = ?",
                (exercise[0], exercise[1], exercise[2], exercise[3]))
            existing_exercise = c.fetchone()

            if not existing_exercise:
                # Insert new exercise with video URL
                c.execute(
                    "INSERT INTO exercise (name, category, targetedBodyParts, requieredEquipment, videoURL) VALUES (?, ?, ?, ?, ?)",
                    exercise
                )
            else:
                # Update the videoURL for existing exercises
                c.execute(
                    "UPDATE exercise SET videoURL = ? WHERE name = ? AND category = ?",
                    (exercise[4], exercise[0], exercise[1])
                )

        conn.commit()

        # Fetch all exercises with their video URLs
        c.execute("SELECT exerciseID, name, category, targetedBodyParts, requieredEquipment, videoURL FROM exercise")
        exercises = c.fetchall()

        # Format the response
        exercise_data = []
        for exercise in exercises:
            exercise_data.append({
                "exerciseID": exercise[0],
                "name": exercise[1],
                "category": exercise[2],
                "targetedBodyParts": exercise[3],
                "requiredEquipment": exercise[4],
                "videoURL": exercise[5]
            })

        return jsonify({"exerciseVideos": exercise_data}), 200

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        conn.close()



# Integrating Swagger UI
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'  # Swagger JSON file location

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "Fitness API"}
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

if __name__ == '__main__':
    createDB('fitness.db')
    app.run(debug=True)
#http://localhost:5000/swagger