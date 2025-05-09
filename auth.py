"""
Google Authentication module for Fitness Application

This module provides endpoints for handling Google authentication.
It allows users to sign in or register with their Google accounts.
"""
from flask import Blueprint, request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import sqlite3
import base64
import re

# Create a Blueprint for auth routes
auth_bp = Blueprint('auth', __name__)

# Google Client IDs
GOOGLE_CLIENT_IDS = [
    "192945878015-c7ck03vqeduqhnln1a9eslb085on44te.apps.googleusercontent.com",  # GYM-Tastic Web
    "192945878015-9j4pbdvkjjr22uvarfgv1qdbjp2lonnp.apps.googleusercontent.com",  # GYM-Tastic Android2
    "192945878015-c5tujrfnael92ts8900tlr55noh93ohk.apps.googleusercontent.com",  # GYM-Tastic Android
]

# Primary Web Client ID (used for verification)
GOOGLE_CLIENT_ID = "192945878015-c7ck03vqeduqhnln1a9eslb085on44te.apps.googleusercontent.com"

def get_db_connection():
    """Create and return a connection to the SQLite database."""
    conn = sqlite3.connect('fitness.db')
    conn.row_factory = sqlite3.Row
    return conn

def find_user_by_email(email):
    """Find a user by their email address."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE email = ?", (email,))
        user = cursor.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def find_user_by_google_id(google_id):
    """Find a user by their Google ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Add a query to check if google_id column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'google_id' not in columns:
            # Add google_id column if it doesn't exist
            cursor.execute("ALTER TABLE user ADD COLUMN google_id TEXT")
            conn.commit()
            
        cursor.execute("SELECT * FROM user WHERE google_id = ?", (google_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def create_user_with_google(google_data):
    """Create a new user using Google account information."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check if google_id column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'google_id' not in columns:
            # Add google_id column if it doesn't exist
            cursor.execute("ALTER TABLE user ADD COLUMN google_id TEXT")
            conn.commit()
        
        # Generate a username from email if not provided
        username = google_data.get('username', google_data['email'].split('@')[0])
        
        # Check if username already exists, append numbers if needed
        base_username = username
        counter = 1
        while True:
            cursor.execute("SELECT username FROM user WHERE username = ?", (username,))
            if not cursor.fetchone():
                break
            username = f"{base_username}{counter}"
            counter += 1
        
        # Generate a random password for Google users
        # This is not used for authentication but satisfies the NOT NULL constraint
        google_password = f"GOOGLE_AUTH_{google_data['google_id']}"
        
        # Insert the new user with isActive=1
        cursor.execute(
            'INSERT INTO user (full_name, username, email, google_id, profilepic, isActive, password) VALUES (?, ?, ?, ?, ?, 1, ?)',
            (
                google_data['name'],
                username,
                google_data['email'],
                google_data['google_id'],
                google_data.get('photo', None),
                google_password
            )
        )
        conn.commit()
        
        # Get the newly created user
        cursor.execute("SELECT * FROM user WHERE google_id = ?", (google_data['google_id'],))
        user = cursor.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def update_user_with_google_id(email, google_id, photo=None):
    """Update an existing user with Google ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check if google_id column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'google_id' not in columns:
            # Add google_id column if it doesn't exist
            cursor.execute("ALTER TABLE user ADD COLUMN google_id TEXT")
            conn.commit()
        
        # Update query
        update_query = 'UPDATE user SET google_id = ?'
        params = [google_id]
        
        # Add photo update if provided
        if photo:
            update_query += ', profilepic = ?'
            params.append(photo)
            
        # Complete the query
        update_query += ' WHERE email = ?'
        params.append(email)
        
        # Execute update
        cursor.execute(update_query, params)
        conn.commit()
        
        # Get the updated user
        cursor.execute("SELECT * FROM user WHERE email = ?", (email,))
        user = cursor.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def user_to_dict(user):
    """Convert a user database row to a dictionary."""
    profile_complete = all([
        user.get('gender'), 
        user.get('height'), 
        user.get('weight'), 
        user.get('birth_date'), 
        user.get('fitness_goal'), 
        user.get('activity_level')
    ])
    
    return {
        "userID": user['userID'],
        "username": user['username'],
        "email": user['email'],
        "full_name": user['full_name'],
        "profilePic": user.get('profilepic', None),
        "profileComplete": profile_complete,
        "isActive": bool(user.get('isActive', 1))
    }

@auth_bp.route('/google-auth', methods=['POST'])
def google_auth():
    """Handle Google authentication requests.
    
    This endpoint verifies Google ID tokens and either creates a new user
    or authenticates an existing user based on the Google account details.
    """
    data = request.json
    
    if not data or 'id_token' not in data:
        return jsonify({"error": "Missing ID token"}), 400
    
    try:
        # Verify the Google ID token
        id_info = id_token.verify_oauth2_token(
            data['id_token'], 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Check that the token is valid and meant for your app
        if id_info['aud'] not in GOOGLE_CLIENT_IDS:
            return jsonify({"error": "Invalid token audience"}), 401
        
        # Get the Google unique ID
        google_id = id_info['sub']
        email = id_info['email']
        name = id_info.get('name', '')
        
        # Get profile photo if available and convert to base64 if not already
        photo = None
        if 'picture' in id_info and id_info['picture']:
            # If the photo is a URL, we need to fetch it and convert to base64
            # For this implementation, we'll just use the URL as is
            # In a production app, you'd fetch the image and convert it
            photo = id_info['picture']
            
            # If you want to override with client-provided photo:
            if 'photo' in data and data['photo']:
                photo = data['photo']
        
        # Check if we have a user with this Google ID
        user = find_user_by_google_id(google_id)
        is_new_user = False
        
        if not user:
            # Check if we have a user with this email
            user = find_user_by_email(email)
            
            if not user:
                # Create a new user with Google data
                google_data = {
                    'name': name,
                    'email': email,
                    'google_id': google_id,
                    'photo': photo
                }
                user = create_user_with_google(google_data)
                is_new_user = True
            else:
                # Update existing user with Google ID
                user = update_user_with_google_id(email, google_id, photo)
        
        # Check if the user is active
        if not user.get('isActive', 1):
            return jsonify({"error": "This account is inactive"}), 403
        
        # Return user data with appropriate status code
        return jsonify(user_to_dict(user)), 201 if is_new_user else 200
    
    except ValueError:
        # Invalid token
        return jsonify({"error": "Invalid ID token"}), 401
    except Exception as e:
        print(f"Google auth error: {str(e)}")
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 500 