import pytest

REGISTER_PAYLOAD = {
    "full_name": "John Doe",
    "username": "johndoe",
    "password": "Passw0rd!",
    "email": "john@example.com",
    "gender": "Male",
    "height": 180,
    "weight": 75,
    "birth_date": "1990-01-01",
    "fitness_goal": "Lose weight",
    "activity_level": "Moderate"
}

def register_and_get_token(client):
    # register new user
    res = client.post("/register", json=REGISTER_PAYLOAD)
    assert res.status_code == 201
    data = res.get_json()
    return data["userID"], data["token"]

def test_register_and_login(client):
    user_id, token = register_and_get_token(client)

    # now login with the same credentials
    res = client.post("/login", json={
        "username": REGISTER_PAYLOAD["username"],
        "password": REGISTER_PAYLOAD["password"]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["userID"] == user_id
    assert "token" in data

def test_update_user_profile_and_get_profile(client):
    user_id, token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # update some fields
    res = client.put("/updateUserProfile", headers=headers, json={
        "full_name": "Johnny",
        "height": 185
    })
    assert res.status_code == 200
    assert res.get_json()["message"] == "Profile updated successfully"

    # fetch profile and confirm changes
    res2 = client.get("/userProfile", headers=headers)
    assert res2.status_code == 200
    profile = res2.get_json()
    assert profile["full_name"] == "Johnny"
    assert profile["height"] == 185
    assert profile["userID"] == user_id

def test_workout_history_empty_then_start_and_list(client):
    user_id, token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # initially no sessions
    res = client.get("/workoutHistory", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["workoutHistory"] == []

    # start workout (exerciseID 1 exists from default inserts)
    res2 = client.post("/startWorkout", headers=headers, json={
        "exerciseID": 1,
        "duration": "00:10:00"
    })
    assert res2.status_code == 201
    assert res2.get_json()["message"] == "Workout started"

    # now history should have one record
    res3 = client.get("/workoutHistory", headers=headers)
    history = res3.get_json()["workoutHistory"]
    assert len(history) == 1
    rec = history[0]
    # keys: sessionID, date, duration, postureAccuracy
    assert "sessionID" in rec and "date" in rec and "duration" in rec and "postureAccuracy" in rec

def test_workout_library_and_reset(client):
    _, token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # default exercises present
    res = client.get("/workoutLibrary", headers=headers)
    assert res.status_code == 200
    exercises = res.get_json()["exercises"]
    names = {e["name"] for e in exercises}
    assert {"Planks", "Squats", "Lunges"}.issubset(names)

    # reset library
    res2 = client.post("/resetWorkoutLibrary", headers=headers)
    assert res2.status_code == 200
    assert res2.get_json()["message"] == "Workout library reset"

    # now library is empty
    res3 = client.get("/workoutLibrary", headers=headers)
    assert res3.status_code == 200
    assert res3.get_json()["exercises"] == []

def test_exercise_videos(client):
    _, token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/exerciseVideos", headers=headers)
    assert res.status_code == 200
    vids = res.get_json()["exerciseVideos"]
    # each entry has a videoURL key (even if None)
    assert all("videoURL" in v for v in vids)

def test_check_user_endpoint(client):
    user_id, token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/checkUser/{user_id}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["exists"] is True
    assert data["active"] is True
