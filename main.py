import os
import sqlite3
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify, Blueprint
from flask_swagger_ui import get_swaggerui_blueprint

from db import initialize_database
from auth import auth_bp
from security import encode_auth_token, token_required

# --------------------------------------------------
# App Initialization
# --------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here')

# Initialize database once
with app.app_context():
    initialize_database('fitness.db')

# --------------------------------------------------
# User Blueprint
# --------------------------------------------------
user_bp = Blueprint('user', __name__)

@user_bp.route('/register', methods=['POST'])
def register():
    """Register a new user with both account and profile info, and issue a JWT."""
    data = request.json or {}

    # required account fields
    acct_fields   = ['full_name', 'username', 'password', 'email']
    # required profile fields
    profile_fields = ['gender', 'height', 'weight', 'birth_date', 'fitness_goal', 'activity_level']

    missing = [f for f in acct_fields + profile_fields if f not in data]
    if missing:
        return jsonify({
            'error': f'Missing required fields: {missing}'
        }), 400

    full_name     = data['full_name']
    username      = data['username']
    raw_password  = data['password']
    email         = data['email']
    role          = data.get('role', 'user')
    gender        = data['gender']
    try:
        height    = float(data['height'])
        weight    = float(data['weight'])
        if height <= 0 or weight <= 0:
            raise ValueError()
    except ValueError:
        return jsonify({'error': 'height and weight must be positive numbers'}), 400
    birth_date    = data['birth_date']
    fitness_goal  = data['fitness_goal']
    activity_level= data['activity_level']
    profilepic    = data.get('profilepic')

    # validate optional profilepic base64
    if profilepic:
        import base64
        try:
            base64.b64decode(profilepic)
        except Exception:
            return jsonify({'error': 'Invalid base64 for profilepic'}), 400

    hashed_password = hashlib.md5(raw_password.encode('utf-8')).hexdigest()

    conn = sqlite3.connect('fitness.db')
    c    = conn.cursor()

    # uniqueness checks
    c.execute("SELECT 1 FROM user WHERE username=?", (username,))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'Username already exists'}), 400

    c.execute("SELECT 1 FROM user WHERE email=?", (email,))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'Email already registered'}), 400

    # insert everything in one shot
    c.execute("""
        INSERT INTO user
          (full_name, username, password, role, email,
           gender, height, weight, profilepic,
           birth_date, fitness_goal, activity_level,
           isActive)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        full_name, username, hashed_password, role, email,
        gender, height, weight, profilepic,
        birth_date, fitness_goal, activity_level
    ))
    conn.commit()
    user_id = c.lastrowid
    conn.close()

    # Issue JWT
    token = encode_auth_token(user_id, role)
    return jsonify({
        'message':   'User registered successfully',
        'userID':    user_id,
        'token':     token
    }), 201

@user_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'username and password are required'}), 400

    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute("SELECT password, role, isActive, userID FROM user WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Username not found'}), 404

    stored_hash, role, is_active, user_id = row
    if hashlib.md5(password.encode('utf-8')).hexdigest() != stored_hash:
        return jsonify({'error': 'Incorrect password'}), 401
    if not is_active:
        return jsonify({'error': 'Account inactive'}), 403

    token = encode_auth_token(user_id, role)
    return jsonify({
        'message': f'Welcome, {username}!',
        'userID': user_id,
        'token': token
    }), 200


@user_bp.route('/updateUserProfile', methods=['PUT'])
@token_required
def update_user_profile(current_user_id):
    data = request.json or {}
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    allowed = {
        'full_name': str, 'username': str, 'password': str, 'email': str,
        'gender': str, 'height': float, 'weight': float, 'profilepic': str,
        'birth_date': str, 'fitness_goal': str, 'activity_level': str,
        'isActive': bool
    }
    updates, params = [], []
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()

    # Process each field
    for field, typ in allowed.items():
        if field in data:
            val = data[field]
            # Type conversions
            if typ is float:
                try:
                    fv = float(val)
                    if fv <= 0:
                        raise ValueError
                    val = fv
                except:
                    conn.close()
                    return jsonify({'error': f'{field} must be a positive number'}), 400
            elif typ is bool:
                if not isinstance(val, bool):
                    conn.close()
                    return jsonify({'error': 'isActive must be boolean'}), 400
                val = 1 if val else 0
            elif field == 'password':
                val = hashlib.md5(val.encode('utf-8')).hexdigest()

            updates.append(f"{field} = ?")
            params.append(val)

    if not updates:
        conn.close()
        return jsonify({'error': 'No valid fields to update'}), 400

    # Uniqueness checks
    if 'username' in data:
        c.execute("SELECT 1 FROM user WHERE username=? AND userID!=?", (data['username'], current_user_id))
        if c.fetchone():
            conn.close()
            return jsonify({'error': 'Username taken'}), 400
    if 'email' in data:
        c.execute("SELECT 1 FROM user WHERE email=? AND userID!=?", (data['email'], current_user_id))
        if c.fetchone():
            conn.close()
            return jsonify({'error': 'Email in use'}), 400

    # Execute update
    sql = f"UPDATE user SET {', '.join(updates)} WHERE userID=?"
    c.execute(sql, params + [current_user_id])
    conn.commit()
    conn.close()
    return jsonify({'message': 'Profile updated successfully'}), 200


@user_bp.route('/workoutHistory', methods=['GET'])
@token_required
def workout_history(current_user_id):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute(
        "SELECT sessionID, date, duration, postureAccuracy FROM workoutSession WHERE userID=?",
        (current_user_id,)
    )
    rows = c.fetchall()
    conn.close()
    history = [
        {'sessionID': sid, 'date': dt, 'duration': dur, 'postureAccuracy': pa}
        for (sid, dt, dur, pa) in rows
    ]
    return jsonify({'userID': current_user_id, 'workoutHistory': history}), 200

@user_bp.route('/userProfile', methods=['GET'])
@token_required
def get_user_profile(current_user_id):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute(
        "SELECT full_name, username, email, gender, height, weight, profilepic,"
        " birth_date, fitness_goal, activity_level, isActive, role"
        " FROM user WHERE userID=?",
        (current_user_id,)
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'User not found'}), 404

    keys = [
        'full_name', 'username', 'email', 'gender', 'height', 'weight',
        'profilepic', 'birth_date', 'fitness_goal', 'activity_level', 'isActive', 'role'
    ]
    profile = dict(zip(keys, row), userID=current_user_id)
    return jsonify(profile), 200


@user_bp.route('/checkUser/<int:user_id>', methods=['GET'])
@token_required
def check_user(current_user_id, user_id):

    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute("SELECT isActive FROM user WHERE userID = ?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({'exists': False, 'active': False}), 200

    return jsonify({'exists': True, 'active': bool(row[0])}), 200


# --------------------------------------------------
# Exercise Blueprint
# --------------------------------------------------
exercise_bp = Blueprint('exercise', __name__)

@exercise_bp.route('/workoutLibrary', methods=['GET'])
@token_required
def workout_library(current_user_id):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute("SELECT exerciseID, name, category, targetedBodyParts, requiredEquipment, videoURL FROM exercise")
    rows = c.fetchall()
    conn.close()
    exercises = [
        {
            'exerciseID': eid, 'name': name, 'category': cat,
            'targetedBodyParts': tb, 'requiredEquipment': req, 'videoURL': url
        }
        for (eid, name, cat, tb, req, url) in rows
    ]
    return jsonify({'exercises': exercises}), 200

@exercise_bp.route('/resetWorkoutLibrary', methods=['POST'])
@token_required

#will be DELETE endpoint
def reset_workout_library(current_user_id):
    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute("DELETE FROM exercise")
    conn.commit()
    conn.close()
    return jsonify({'message': 'Workout library reset'}), 200

@exercise_bp.route('/startWorkout', methods=['POST'])
@token_required
def start_workout(current_user_id):
    """Start a new workout session for an exercise."""
    data = request.json or {}
    exercise_id = data.get('exerciseID')
    duration    = data.get('duration')
    if not all([exercise_id, duration]):
        return jsonify({'error': 'exerciseID and duration are required'}), 400

    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    # Check account active
    c.execute("SELECT isActive FROM user WHERE userID=?", (current_user_id,))
    status = c.fetchone()
    if not status or not status[0]:
        conn.close()
        return jsonify({'error': 'Account inactive or user not found'}), 403
    # Check exercise exists
    c.execute("SELECT 1 FROM exercise WHERE exerciseID=?", (exercise_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'Exercise not found'}), 404

    session_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute(
        "INSERT INTO workoutSession(date, duration, postureAccuracy, userID) VALUES(?, ?, ?, ?)",
        (session_date, duration, 0.0, current_user_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Workout started', 'exerciseID': exercise_id}), 201

@exercise_bp.route('/exerciseVideos', methods=['GET'])
@token_required
def exercise_videos(current_user_id):

    conn = sqlite3.connect('fitness.db')
    c = conn.cursor()
    c.execute("SELECT exerciseID, name, videoURL FROM exercise")
    rows = c.fetchall()
    conn.close()
    videos = [
        {'exerciseID': eid, 'name': name, 'videoURL': url}
        for (eid, name, url) in rows
    ]
    return jsonify({'exerciseVideos': videos}), 200

# --------------------------------------------------
# Register Blueprints & Swagger UI
# --------------------------------------------------
SWAGGER_URL = '/swagger'
API_URL     = '/static/swagger.json'
app.register_blueprint(get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "Fitness API"}), url_prefix=SWAGGER_URL)

app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(exercise_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
