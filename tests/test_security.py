import pytest
from flask import Flask, jsonify
from security import encode_auth_token, decode_auth_token, token_required

def test_encode_and_decode_token():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'
    with app.app_context():
        token = encode_auth_token(42, 'admin')
        payload = decode_auth_token(token)
        assert payload['sub'] == 42
        assert payload['role'] == 'admin'
        assert 'exp' in payload and 'iat' in payload

def test_decode_invalid_token_raises():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'
    with app.app_context():
        with pytest.raises(ValueError):
            decode_auth_token("not-a-valid.jwt.token")

def test_token_required_decorator_allows_and_blocks(client):
    # create a small Flask app to test the decorator
    test_app = Flask(__name__)
    test_app.config['SECRET_KEY'] = 'abc123'

    @test_app.route("/protected")
    @token_required
    def protected_route(current_user_id):
        return jsonify({"you": current_user_id})

    with test_app.test_client() as c, test_app.app_context():
        # no header => 401
        r1 = c.get("/protected")
        assert r1.status_code == 401

        # valid token => 200
        token = encode_auth_token(7, 'user')
        r2 = c.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        assert r2.get_json()["you"] == 7
