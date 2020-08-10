import json  # pragma: no cover
import jwt   # pragma: no cover
from cryptography.hazmat.primitives import serialization    # pragma: no cover
from jwt.algorithms import RSAAlgorithm     # pragma: no cover
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


class AppleResolver(object):
    # https://gist.github.com/davidhariri/b053787aabc9a8a9cc0893244e1549fe

    @classmethod
    def __get_right_public_key_info(cls, keys, unverified_header):
        for key in keys:
            if key['kid'] == unverified_header['kid']:
                return key

    @classmethod
    def authenticate(cls, access_token, client_id):

        import http.client

        apple_keys_host = 'appleid.apple.com'
        apple_keys_url = '/auth/keys'
        headers = {"Content-type": "application/json"}

        try:

            connection = http.client.HTTPSConnection(apple_keys_host, 443)
            connection.request('GET', apple_keys_url, headers=headers)
            response = connection.getresponse()

            keys_json = json.loads(response.read().decode('utf8'))
            connection.close()

            unverified_header = jwt.get_unverified_header(access_token)

            public_key_info = cls.__get_right_public_key_info(keys_json['keys'], unverified_header)

            apple_public_key = RSAAlgorithm.from_jwk(json.dumps(public_key_info))

            apple_public_key_as_string = apple_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            verified_payload = jwt.decode(access_token, apple_public_key_as_string,
                                          audience=client_id,
                                          algorithm=public_key_info['alg'])
            print('AppleResolver verified_payload: ', verified_payload)

            # sub:
            #   The subject registered claim identifies the principal that is the subject of the identity token. Since
            #   this token is meant for your application, the value is the unique identifier for the user.
            return {'email': verified_payload['email'],
                    'subject_registered_claim': verified_payload['sub']}

        except Exception as ex:
            logger.error("AppleResolver caught exception: " + str(ex))
