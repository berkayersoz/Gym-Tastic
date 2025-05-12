# Fitness API Application

A Flask-based REST API for a fitness application that allows users to register, login, track workout history, and access workout resources.

## Project Structure

The application is organized using Flask Blueprints:

- **User Blueprint**: Manages all user-related endpoints like registration, login, and profile management
- **Exercise Blueprint**: Handles exercise library, workout sessions, and exercise videos
- **Auth Blueprint**: Handles Google authentication for login and registration

## API Endpoints

### User Endpoints

- **POST /register**: Register a new user with full name, username, password, and email (sets isActive=1)
- **POST /login**: Authenticate user with username and password (checks isActive status)
- **POST /createProfile**: Create or update user profile details in the unified user table
- **PUT /updateUserProfile/{userID}**: Update existing user profile information and account status
- **GET /workoutHistory/{userID}**: Get workout history for a specific user (checks isActive status)
- **GET /checkUser/{user_id}**: Check if a user exists and if their account is active
- **GET /userProfile/{user_id}**: Get complete user profile information for the profile screen

### Authentication Endpoints

- **POST /google-auth**: Authenticate or register a user with their Google account

### Exercise Endpoints

- **GET /workoutLibrary**: Get the complete workout library
- **POST /resetWorkoutLibrary**: Reset the workout library by removing all exercises
- **POST /startWorkout**: Start a new workout session for a user (checks isActive status)
- **GET /exerciseVideos**: Get all exercise videos with their details

## Database Schema

The application uses SQLite with the following main tables:

- **user**: Unified table that stores both user account and profile information, including:
  - `userID`: Unique identifier for the user (Primary Key)
  - `full_name`: User's full name
  - `username`: Unique username for login
  - `password`: User's password
  - `email`: User's email address
  - `gender`: User's gender
  - `height`: User's height in cm
  - `weight`: User's weight in kg
  - `profilepic`: Base64 encoded profile picture
  - `birth_date`: User's date of birth
  - `fitness_goal`: User's fitness goals
  - `activity_level`: User's activity level
  - `isActive`: Boolean flag indicating if the account is active
  - `google_id`: Google ID for users who registered with Google (added automatically)
  
- **exercise**: Contains exercise library details
  - `exerciseID`: Unique identifier for the exercise
  - `name`: Exercise name
  - `category`: Exercise category (e.g., Upper Body, Lower Body)
  - `targetedBodyParts`: Body parts targeted by the exercise
  - `requieredEquipment`: Equipment needed for the exercise
  - `videoURL`: URL to exercise demonstration video

- **workoutSession**: Tracks user workout sessions
  - `sessionID`: Unique identifier for the session
  - `date`: Date and time of the workout
  - `duration`: Duration of the workout
  - `postureAccuracy`: Accuracy of user's posture during workout
  - `userID`: Foreign key linking to the user table

## Getting Started

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Set your Google Client ID (for Google Authentication):
   - Get your client ID from Google Cloud Console
   - Edit the `GOOGLE_CLIENT_ID` variable in `auth.py`

3. Run the application:
```
python main.py
```

4. Access the Swagger UI documentation at:
```
http://localhost:5000/swagger
```

## Features

- User registration and authentication
- Google Sign-In integration
- User profile management with account activation status
- Exercise library management
- Workout tracking
- Exercise videos
- API documentation with Swagger 