import jwt
from jwt.algorithms import RSAAlgorithm
import requests
from time import time
import json
# import os
from config.base import get_environment_variable


APPLE_PUBLIC_KEY_URL = "https://appleid.apple.com/auth/keys"
APPLE_PUBLIC_KEY = None
APPLE_KEY_CACHE_EXP = 60 * 60 * 24
APPLE_LAST_KEY_FETCH = 0

# https://gist.github.com/davidhariri/b053787aabc9a8a9cc0893244e1549fe


# TODO: Question - could we change the name of this class so it doesn't conflict with the AppleUser in models.py?
class AppleUser(object):
    def __init__(self, apple_id, email=None):
        self.id = apple_id
        self.email = email
        self.full_user = False

        if email is not None:
            self.full_user = True

    def __repr__(self):
        return "<AppleUser {}>".format(self.id)


def _fetch_apple_public_key():
    # Check to see if the public key is unset or is stale before returning
    global APPLE_LAST_KEY_FETCH
    global APPLE_PUBLIC_KEY

    if (APPLE_LAST_KEY_FETCH + APPLE_KEY_CACHE_EXP) < int(time()) or APPLE_PUBLIC_KEY is None:
        key_payload = requests.get(APPLE_PUBLIC_KEY_URL).json()
        APPLE_PUBLIC_KEY = RSAAlgorithm.from_jwk(json.dumps(key_payload["keys"][0]))
        APPLE_LAST_KEY_FETCH = int(time())

    return APPLE_PUBLIC_KEY


def _decode_apple_user_token(apple_user_token):
    public_key = _fetch_apple_public_key()

    try:
        # token = jwt.decode(apple_user_token, public_key, audience=os.getenv("APPLE_APP_ID"), algorithm="RS256")
        token = jwt.decode(apple_user_token, public_key, audience=get_environment_variable("SOCIAL_AUTH_APPLE_KEY_ID"),
                           algorithms=["RS256"])
    except jwt.exceptions.ExpiredSignatureError as e:
        raise Exception("That token has expired")
    except jwt.exceptions.InvalidAudienceError as e:
        raise Exception("That token's audience did not match")
    except Exception as e:
        print(e)
        raise Exception("An unexpected error occurred")

    return token


def retrieve_user(user_token):
    token = _decode_apple_user_token(user_token)
    apple_user = AppleUser(token["sub"], token.get("email", None))

    return apple_user
