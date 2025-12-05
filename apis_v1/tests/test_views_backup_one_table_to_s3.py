
from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from wevote_tokens.models.single_use_tokens import SingleUseTokenManager
from wevote_tokens.enums import TokenUsage
from apis_v1.views.views_retrieve_tables import backup_one_table_to_s3_view
import json

class TestBackupOneTableToS3Tokens(TestCase):
    def setUp(self):
        self.host = 'localhost:8000'
        self.url = f'{self.host}/apis/v1/backupOneTableToS3/'
        self.request = RequestFactory().get(
            self.url,
            {'table_name': 'table_name',
            'voter_api_device_id': ''}
            )
    
    @classmethod
    def setUpTestData(cls):
        cls.validation_key = SingleUseTokenManager.generate_encryption_key()
        cls.user_id = 'user_id'
        cls.test_token_info = SingleUseTokenManager.create_token(
            user_id=cls.user_id,
            validation_key=cls.validation_key,
            expiration_seconds=1200,
            json_data={'usage': TokenUsage.FAST_LOAD.value}
        )
        # Convert bytes to string for testing, in production headers are strings
        cls.validation_key_str = cls.validation_key.decode('utf-8')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Start patches at class level
        cls.mock_get_voter_api_device_id = patch(
            'apis_v1.views.views_retrieve_tables.get_voter_api_device_id',
            return_value=''
        ).start()
        
        cls.mock_backup_one_table_to_s3_controller = patch(
            'apis_v1.views.views_retrieve_tables.backup_one_table_to_s3_controller',
            return_value={
                'success': True,
                'status': '',
                'aws_s3_file_url': 'https://example.com/aws_s3_file_url'
            }
        ).start()
    
    @classmethod
    def tearDownClass(cls):
        patch.stopall()
        super().tearDownClass()

    def test_tests(self):
        self.assertEqual(1, 1)

    def test_auth_token_and_new_key(self):
        request = self.request
        request.META['HTTP_AUTHORIZATION'] = f'Token {self.test_token_info["token_pk"]}'
        request.META['HTTP_X_TOKEN_KEY'] = self.validation_key_str
        request.META['HTTP_X_NEW_KEY'] = SingleUseTokenManager.generate_encryption_key().decode('utf-8')

        response = backup_one_table_to_s3_view(request)
        response_json = json.loads(response.content)

        # breakpoint()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json['token_info']['success'], True)
        self.assertIsNotNone(response_json['token_info']['token_pk'])
        self.assertNotEqual(response_json['token_info']['token_pk'], self.test_token_info['token_pk'])
        self.assertEqual(response_json['token_info']['token_user'], self.user_id)
        # self.assertEqual(response_json['token_info']['json_data'], {'usage': TokenUsage.FAST_LOAD.value})

    def test_auth_token_and_no_new_key(self):
        request = self.request
        request.META['HTTP_AUTHORIZATION'] = f'Token {self.test_token_info["token_pk"]}'
        request.META['HTTP_X_TOKEN_KEY'] = self.validation_key_str

        response = backup_one_table_to_s3_view(request)
        response_json = json.loads(response.content)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json['token_info']['success'], True)
        self.assertEqual(response_json['token_info']['token_user'], self.user_id)
        self.assertEqual(response_json['token_info']['json_data'], {'usage': TokenUsage.FAST_LOAD.value})
    
    def test_bad_token(self):
        request = self.request
        request.META['HTTP_AUTHORIZATION'] = f'Token {self.test_token_info["token_pk"] + 99999999999999999}'
        request.META['HTTP_X_TOKEN_KEY'] = self.validation_key_str

        response = backup_one_table_to_s3_view(request)
        response_json = json.loads(response.content)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json['token_info']['success'], False)
    
    def test_bad_token_key(self):
        request = self.request
        request.META['HTTP_AUTHORIZATION'] = f'Token {self.test_token_info["token_pk"]}'
        request.META['HTTP_X_TOKEN_KEY'] = 'invalid_token_key'

        response = backup_one_table_to_s3_view(request)
        response_json = json.loads(response.content)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json['token_info']['success'], False)

    def test_no_auth_token(self):
        request = self.request
        request.META['HTTP_X_TOKEN_KEY'] = self.validation_key_str

        response = backup_one_table_to_s3_view(request)
        response_json = json.loads(response.content)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json['token_info']['success'], False)
        self.assertEqual(response_json['token_info']['status'], 'Authorization token and key are required')

    def test_no_token_key(self):
        request = self.request
        request.META['HTTP_AUTHORIZATION'] = f'Token {self.test_token_info["token_pk"]}'

        response = backup_one_table_to_s3_view(request)
        response_json = json.loads(response.content)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json['token_info']['success'], False)
        self.assertEqual(response_json['token_info']['status'], 'Authorization token and key are required')

    def test_invalid_token_new_key(self):
        request = self.request
        request.META['HTTP_AUTHORIZATION'] = f'Token {self.test_token_info["token_pk"] + 99999999999999999}'
        request.META['HTTP_X_TOKEN_KEY'] = self.validation_key_str
        request.META['HTTP_X_NEW_KEY'] = SingleUseTokenManager.generate_encryption_key().decode('utf-8')

        response = backup_one_table_to_s3_view(request)
        response_json = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json['token_info']['success'], False)