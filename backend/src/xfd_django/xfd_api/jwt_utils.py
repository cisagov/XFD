# xfd_api/jwt_utils.py

import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from jwt import ExpiredSignatureError, InvalidTokenError

User = get_user_model()
SECRET_KEY = settings.SECRET_KEY

def create_jwt_token(user):
    payload = {
        'id': str(user.id),
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def decode_jwt_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user = User.objects.get(id=payload['id'])
        return user
    except (ExpiredSignatureError, InvalidTokenError, User.DoesNotExist):
        return None
