import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, InvalidSubjectError
from datetime import datetime, timedelta
from flask import current_app, request, jsonify
from functools import wraps

def encode_auth_token(user_id, role):
    payload = {
        'exp': datetime.utcnow() + timedelta(days=1),
        'iat': datetime.utcnow(),
        'sub': str(user_id),
        'role': role
    }
    return jwt.encode(payload,
                      current_app.config['SECRET_KEY'],
                      algorithm='HS256')

def decode_auth_token(token):
    try:
        payload = jwt.decode(token,
                             current_app.config['SECRET_KEY'],
                             algorithms=['HS256'])

        if 'sub' in payload:
            try:
                payload['sub'] = int(payload['sub'])
            except ValueError:
                pass
        return payload

    except ExpiredSignatureError:
        raise ValueError('Token expired, please login again.')
    except (InvalidTokenError, InvalidSubjectError):
        raise ValueError('Invalid token, please login again.')


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', None)
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token is missing'}), 401
        token = auth_header.split(' ')[1]
        try:
            payload = decode_auth_token(token)
            user_id = payload['sub']
            request.user_role = payload.get('role')
        except ValueError as e:
            return jsonify({'error': str(e)}), 401

        return f(user_id, *args, **kwargs)
    return decorated
