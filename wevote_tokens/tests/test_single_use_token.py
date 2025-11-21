from django.test import TestCase
from voter.models import VoterManager
from wevote_tokens.models.single_use_tokens import SingleUseToken, SingleUseTokenManager
from cryptography.fernet import Fernet
import json
from datetime import timedelta
from django.utils import timezone
import time

# Only used to test SingleUseToken model
class TestSingleUseToken(TestCase):
    def setUp(self):
        self.test_voter = VoterManager().create_voter(email='test@example.com', password='testpassword')['voter']
        self.test_validation_key = Fernet.generate_key()
        self.test_cipher = Fernet(self.test_validation_key)
    
    def test_single_use_token_creation(self):
        voter = self.test_voter
        validation_key = self.test_validation_key
        expiration = 300
        json_data = {'test': 'test'}

        token = SingleUseToken()
        token.save(user=voter, validation_key=validation_key, expiration_seconds=expiration, json_data=json_data)

        self.assertEqual(
            token._user,
            voter,
            "_user Not Set Correctly")
        self.assertEqual(
            self.test_cipher.decrypt(token._validation),
            validation_key,
            "_validation Not Set Correctly")
        self.assertEqual(
            json.loads(self.test_cipher.decrypt(token._json_data_encrypted).decode('utf-8')),
            json_data, 
            "_json_data_encrypted Not Set Correctly")
        self.assertLessEqual(
            (timezone.now() + timedelta(seconds=expiration)) - token._expiration_datetime,
            timedelta(seconds=1),
            "_expiration_datetime Not Set Correctly")
    
    def test_single_use_token_creation_with_invalid_user(self):
        invalid_user = 'invalid'
        validation_key = self.test_validation_key

        token = SingleUseToken()

        with self.assertRaisesMessage(ValueError, 'Cannot assign'):
            token.save(user=invalid_user, validation_key=validation_key)

    def test_single_use_token_creation_with_invalid_validation_key(self):
        voter = self.test_voter
        invalid_validation_key = 'invalid'

        token = SingleUseToken()

        with self.assertRaisesMessage(ValueError, "Validation key must be a bytes object."):
            token.save(user=voter, validation_key=invalid_validation_key)

    def test_single_use_token_creation_with_invalid_json_data(self):
        voter = self.test_voter
        invalid_json_data = 1

        token = SingleUseToken()

        with self.assertRaisesMessage(ValueError, "JSON data must be a dictionary or None."):
            token.save(user=voter, validation_key=self.test_validation_key, json_data=invalid_json_data)
    
    def test_single_use_token_creation_with_large_json_data(self):
        voter = self.test_voter
        large_json_data = {'test': 'test' * 10000}
        large_json_data_size = len(bytes(json.dumps(large_json_data), "utf-8"))

        token = SingleUseToken()

        with self.assertRaisesMessage(ValueError, f"Json Data must be <= 8kb, currently {large_json_data_size} bytes."):
            token.save(user=voter, validation_key=self.test_validation_key, json_data=large_json_data)
    
    def test_single_use_token_creation_with_default_expiration(self):
        voter = self.test_voter
        default_expiration = 300
        validation_key = self.test_validation_key

        token = SingleUseToken()
        token.save(user=voter, validation_key=validation_key)

        self.assertLessEqual(
            (timezone.now() + timedelta(seconds=default_expiration)) - token._expiration_datetime,
            timedelta(seconds=1),
            "_expiration_datetime Not Set With Correct Default Expiration")

    def test_single_use_token_creation_with_invalid_expiration(self):
        voter = self.test_voter
        invalid_expiration = 'invalid'
        validation_key = self.test_validation_key

        token = SingleUseToken()

        with self.assertRaisesMessage(ValueError, "Expiration time must be an integer or float, in seconds."):
            token.save(user=voter, validation_key=validation_key, expiration_seconds=invalid_expiration)

    def test_single_use_token_creation_with_negative_expiration(self):
        voter = self.test_voter
        negative_expiration = -1
        validation_key = self.test_validation_key

        token = SingleUseToken()

        with self.assertRaisesMessage(ValueError, "Expiration Seconds must be a positive value."):
            token.save(user=voter, validation_key=validation_key, expiration_seconds=negative_expiration)

    def test_single_use_token_creation_with_large_expiration(self):
        voter = self.test_voter
        large_expiration = 1801
        validation_key = self.test_validation_key

        token = SingleUseToken()

        with self.assertRaisesMessage(ValueError, "Expiration Seconds must be <= 1800."):
            token.save(user=voter, validation_key=validation_key, expiration_seconds=large_expiration)


class TestSingleUseTokenManager(TestCase):

    def setUp(self):
        self.test_voter = VoterManager().create_voter(email='test@example.com', password='testpassword')['voter']
        self.test_validation_key = Fernet.generate_key()

    def _assert_equal(self, values_dict, keys_to_check, expected_value, reason):
        for i, key in enumerate(keys_to_check):
            self.assertEqual(values_dict[key], expected_value[i], f"'{key}' Should Be {expected_value[i]} on {reason} but was {values_dict[key]}")

    def _assert_is_none(self, values_dict, keys_to_check, reason):
        for key in keys_to_check:
            self.assertIsNone(values_dict[key], f"'{key}' Should Be None on {reason} but was {values_dict[key]}")

    def _assert_is_not_none(self, values_dict, keys_to_check, reason):
        for key in keys_to_check:
            self.assertIsNotNone(values_dict[key], f"'{key}' Should Be Not None on {reason} but was {values_dict[key]}")

    def _assert_true(self, values_dict, keys_to_check, reason):
        for key in keys_to_check:
            self.assertTrue(values_dict[key], f"'{key}' Should Be True on {reason} but was {values_dict[key]}")

    def _assert_false(self, values_dict, keys_to_check, reason):
        for key in keys_to_check:
            self.assertFalse(values_dict[key], f"'{key}' Should Be False on {reason} but was {values_dict[key]}")

    def _get_test_token_pk(self, voter=None, validation_key=None, expiration_seconds=None, json_data=None):
        if voter is None:
            voter = self.test_voter
        if validation_key is None:
            validation_key = self.test_validation_key
            
        token_info = SingleUseTokenManager.create_token(user=voter, validation_key=validation_key, expiration_seconds=expiration_seconds, json_data=json_data)
        return token_info['token_pk']

    def test_generate_encryption_key(self):
        
        encryption_key = SingleUseTokenManager.generate_encryption_key()
        
        self._assert_equal(
            {'encryption_key': len(encryption_key)},
            ['encryption_key'],
            [len(Fernet.generate_key())],
            "Encryption Key Generation")
        self._assert_is_not_none({'encryption_key': encryption_key}, ['encryption_key'], "Encryption Key Should Not Be None")
        self.assertIsInstance(encryption_key, bytes, "Encryption Key Not a bytes object")

    def test_create_token(self):
        voter = self.test_voter
        validation_key = self.test_validation_key
        expiration = 300
        message_addon = "Token Creation Success"

        token_info = SingleUseTokenManager.create_token(user=voter, validation_key=validation_key, expiration_seconds=expiration)

        self._assert_equal(token_info, ['status', 'token_user'], ["TOKEN CREATED", voter], message_addon)
        self._assert_is_not_none(token_info, ['token_pk'], message_addon)
        self.assertLessEqual(
            (timezone.now() + timedelta(seconds=expiration)) - token_info['expiration_datetime'],
            timedelta(seconds=1),
            "Expiration Datetime Not Set Correctly")

    def test_create_token_failure(self):
        voter = self.test_voter
        validation_key = self.test_validation_key
        message_addon = "Token Creation Failure"

        token_info = SingleUseTokenManager.create_token(user=voter, validation_key=validation_key, expiration_seconds='invalid')
        
        self._assert_false(token_info, ['success'], message_addon)
        self._assert_is_none(token_info, ['token_pk', 'expiration_datetime', 'token_user'], message_addon)
        self._assert_equal(
            token_info,
            ['status'],
            ["TOKEN SAVE FAILED: Expiration time must be an integer or float, in seconds."],
            message_addon)

    def test_create_token_with_invalid_validation_key(self):
        voter = self.test_voter
        invalid_validation_key = 99999999
        message_addon = "Invalid Validation Key"
        
        token_info = SingleUseTokenManager.create_token(user=voter, validation_key=invalid_validation_key)

        self._assert_false(token_info, ['success'], message_addon)
        self._assert_is_none(token_info, ['token_pk', 'expiration_datetime', 'token_user'], message_addon)
        self._assert_equal(token_info, ['status'], ["VALIDATION KEY MUST BE A BYTES OR STRING."], message_addon)

    def test_authenticate_retrieve_token(self):
        voter = self.test_voter
        json_data = {'test': 'test'}
        message_addon = "Authentication Success"
        
        token_pk = self._get_test_token_pk(voter=voter, json_data=json_data)
        token_info = SingleUseTokenManager.authenticate_retrieve_token(token_pk, self.test_validation_key)

        self._assert_false(token_info, ['expired'], message_addon)
        self._assert_false({'exists': SingleUseToken.objects.filter(pk=token_pk).exists()}, ['exists'], message_addon)
        self._assert_equal(
            token_info,
            ['status', 'json_data', 'token_user'],
            ["TOKEN RETRIEVED AND AUTHENTICATED", json_data, voter],
            message_addon)
        self._assert_is_not_none(token_info, ['expiration_datetime'], message_addon)
        self._assert_true(token_info, ['success'], message_addon)


    def test_authenticate_retrieve_token_invalid_pk(self):
        invalid_pk = 999999
        message_addon = "Token Not Found"

        token_pk = self._get_test_token_pk()
        token_info = SingleUseTokenManager.authenticate_retrieve_token(invalid_pk, self.test_validation_key)

        self._assert_false(token_info, ['success', 'expired'], message_addon)
        self._assert_is_none(token_info, ['expiration_datetime', 'token_user', 'json_data'], message_addon)
        self._assert_equal(token_info, ['status'], ["TOKEN NOT FOUND: SingleUseToken matching query does not exist."], message_addon)
        self._assert_true({'exists': SingleUseToken.objects.filter(pk=token_pk).exists()}, ['exists'], message_addon)
    
    def test_authenticate_retrieve_token_invalid_validation_key(self):
        invalid_validation_key = Fernet.generate_key()
        message_addon = "Invalid Validation Key"

        token_pk = self._get_test_token_pk()
        token_info = SingleUseTokenManager.authenticate_retrieve_token(token_pk, invalid_validation_key)

        self._assert_false(token_info, ['success', 'expired'], message_addon)
        self._assert_is_none(token_info, ['expiration_datetime', 'token_user', 'json_data'], message_addon)
        self._assert_equal(token_info, ['status'], ["VALIDATION DECRYPTION ERROR: Invalid Key"], message_addon)
        self._assert_true({'exists': SingleUseToken.objects.filter(pk=token_pk).exists()}, ['exists'], message_addon)

    def test_authenticate_retrieve_token_expired(self):
        expiration = 0
        message_addon = "Expired Token"

        token_pk = self._get_test_token_pk(expiration_seconds=expiration)
        time.sleep(1)
        token_info = SingleUseTokenManager.authenticate_retrieve_token(token_pk, self.test_validation_key)

        self._assert_false(token_info, ['success'], message_addon)
        self._assert_false({'exists': SingleUseToken.objects.filter(pk=token_pk).exists()}, ['exists'], message_addon)
        self._assert_is_none(token_info, ['token_user', 'json_data'], message_addon)
        self._assert_equal(token_info, ['status'], ["TOKEN EXPIRED"], message_addon)
        self._assert_is_not_none(token_info, ['expiration_datetime'], message_addon)
        self._assert_true(token_info, ['expired'], message_addon)

    def test_authenticate_retrieve_token_with_json_data(self):
        voter = self.test_voter
        json_data = {'test': 'test'}
        message_addon = "Authentication Success with JSON Data"
        
        token_pk = self._get_test_token_pk(voter=voter, json_data=json_data)
        token_info = SingleUseTokenManager.authenticate_retrieve_token(token_pk, self.test_validation_key)

        self._assert_false(token_info, ['expired'], message_addon)
        self._assert_false({'exists': SingleUseToken.objects.filter(pk=token_pk).exists()}, ['exists'], message_addon)
        self._assert_equal(
            token_info,
            ['status', 'json_data', 'token_user'],
            ["TOKEN RETRIEVED AND AUTHENTICATED", json_data, voter],
            message_addon)
        self._assert_is_not_none(token_info, ['expiration_datetime'], message_addon)
        self._assert_true(token_info, ['success'], message_addon)
    
    def test_authenticate_retrieve_token_with_no_json_data(self):
        voter = self.test_voter
        message_addon = "Authentication Success With No JSON Data"

        token_pk = self._get_test_token_pk(voter=voter)
        token_info = SingleUseTokenManager.authenticate_retrieve_token(token_pk, self.test_validation_key)

        self._assert_false(token_info, ['expired'], message_addon)
        self._assert_false({'exists': SingleUseToken.objects.filter(pk=token_pk).exists()}, ['exists'], message_addon)
        self._assert_equal(
            token_info,
            ['status', 'json_data', 'token_user'],
            ["TOKEN RETRIEVED AND AUTHENTICATED", None, voter],
            message_addon)
        self._assert_is_not_none(token_info, ['expiration_datetime'], message_addon)
        self._assert_true(token_info, ['success'], message_addon)