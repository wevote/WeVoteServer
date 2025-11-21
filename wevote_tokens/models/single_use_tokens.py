from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
from cryptography.fernet import Fernet, InvalidToken
import json
from wevote_functions.functions import positive_value_exists


class SingleUseToken(models.Model):
    """
    ###################################################
    ONLY WORK WITH TOKENS THROUGH SingleUseTokenManager
    ###################################################
    Custom token model that extends DRF's Token with:
    - Retrieval Key Setting
    - Expiration Time Setting
    - JSON Data Setting
    - User Setting
    - Created at Setting
    """

    _user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='single_use_tokens',  # Allows user.single_use_tokens.all()
        on_delete=models.CASCADE,
        help_text='The user this token belongs to.',
    )

    # Retrieval Key Setting
    _validation = models.BinaryField(
        verbose_name='Encoded Validation Data',
        help_text='Field used to test if the passed validation key is valid.',
    )

    # Expiration time - tokens expire after this datetime
    _expiration_datetime = models.DateTimeField(
        verbose_name='token expiration datetime',
        help_text='When this token expires.',
    )
    
    # JSON blob for storing additional metadata
    _json_data_encrypted = models.BinaryField(
        verbose_name='additional token data',
        null=True,
        blank=True,
        default=None,
        help_text='Encrypted JSON blob for storing additional token data.',
    )
    
    # Timestamp when token was created
    _created_at = models.DateTimeField(
        verbose_name='token creation datetime',
        db_index=True,
        help_text='Timestamp when token was created.',
        default=timezone.now,
    )
    
    class Meta:
        verbose_name = 'Single Use Token'
        verbose_name_plural = 'Single Use Tokens'
        # db_table = 'authtoken_token' # Replacing DRF's default Token model
    
    def __str__(self):
        return f"Single Use Token for {self._user} (expires: {self._expiration_datetime})"

    ## Only modify on creation.
    def save(self, user, validation_key, expiration_seconds=None, json_data=None, *args, **kwargs):

        if self.pk is not None:  # object exists
            raise ValueError("Direct save is not allowed. Tokens are meant to be immutable after creation.")

        # Validate inputs
        if not isinstance(validation_key, (bytes)):
            raise ValueError("Validation key must be a bytes object.")
        if not isinstance(expiration_seconds, (int, float, type(None))):
            raise ValueError("Expiration time must be an integer or float, in seconds.")
        if not isinstance(json_data, (dict, type(None))):
            raise ValueError("JSON data must be a dictionary or None.")

        cipher = Fernet(validation_key)
        time_now = timezone.now()
            
        #default to 5 minutes expiration time
        if expiration_seconds is None:
            expiration_seconds = 300
        elif expiration_seconds < 0:
            raise ValueError("Expiration Seconds must be a positive value.")
        elif expiration_seconds > 1800: # 30 minutes
            raise ValueError("Expiration Seconds must be <= 1800.")
            

        if json_data is not None:
            json_data = json.dumps(json_data)
            json_data_size = len(bytes(json_data, "utf-8"))
            if json_data_size > 8192:
                raise ValueError(f"Json Data must be <= 8kb, currently {json_data_size} bytes.")
            json_data_encrypted = cipher.encrypt(json_data.encode('utf-8'))
        else:
            json_data_encrypted = None
        
        self._user = user
        self._created_at = time_now
        self._validation = cipher.encrypt(validation_key)
        self._expiration_datetime = time_now + timedelta(seconds=int(expiration_seconds))
        self._json_data_encrypted = json_data_encrypted

        super().save(*args, **kwargs)

class SingleUseTokenManager(models.Manager):

    def __str__(self):              # __unicode__ on Python 2
        return "Single Use Token Manager"

    @staticmethod
    def generate_encryption_key():
        ## Add cryptographically secure random URL safe base 64 encoded string generation
        return Fernet.generate_key()

    @staticmethod
    def create_token(user, validation_key, expiration_seconds=None, json_data=None):
        token_info = {
            'success': False,
            'status': '',
            'token_pk': None,
            'expiration_datetime': None,
            'token_user': None,
        }

        if isinstance(validation_key, (str)):
            validation_key = validation_key.encode('utf-8')
        
        if not isinstance(validation_key, (bytes)):
            token_info['status'] = "VALIDATION KEY MUST BE A BYTES OR STRING."
            return token_info

        new_token = SingleUseToken()
        try:
            new_token.save(user, validation_key=validation_key,
                expiration_seconds=expiration_seconds,
                json_data=json_data)
        except Exception as e:
            token_info['status'] = f"TOKEN SAVE FAILED: {e}"
            return token_info

        token_info['success'] = True
        token_info['status'] = 'TOKEN CREATED'
        token_info['token_pk'] = new_token.pk
        token_info['expiration_datetime'] = new_token._expiration_datetime
        token_info['token_user'] = new_token._user

        return token_info

    @staticmethod
    def authenticate_retrieve_token(pk, validation_key):
        token_info = {
            'success': False,
            'status': '',
            'expiration_datetime': None,
            'json_data': None,
            'token_user': None,
            'expired': False,
        }
        
        cipher = Fernet(validation_key)

        try:
            token = SingleUseToken.objects.get(pk=pk)
        except Exception as e:
            token_info['status'] = 'TOKEN NOT FOUND: ' + str(e)
            return token_info
        
        try:
            # Convert BinaryField (memoryview) to bytes for Fernet.decrypt()
            validation_bytes = bytes(token._validation) if token._validation else b''
            cipher.decrypt(validation_bytes)
        except InvalidToken:
            token_info['status'] = 'VALIDATION DECRYPTION ERROR: Invalid Key'
            return token_info
        except Exception as e:
            token_info['status'] = 'VALIDATION DECRYPTION ERROR: ' + str(e)
            return token_info

        if timezone.now() > token._expiration_datetime:
            token_info['status'] = 'TOKEN EXPIRED'
            token_info['expired'] = True
            token_info['expiration_datetime'] = token._expiration_datetime
            token.delete()
            return token_info


        if token._json_data_encrypted is not None:
            # Convert BinaryField (memoryview) to bytes for Fernet.decrypt()
            json_data_bytes = bytes(token._json_data_encrypted)
            json_data = json.loads(cipher.decrypt(json_data_bytes).decode('utf-8'))
        else:
            json_data = token_info['json_data'] = None

        token_info['success'] = True
        token_info['status'] = 'TOKEN RETRIEVED AND AUTHENTICATED'
        token_info['expiration_datetime'] = token._expiration_datetime
        token_info['json_data'] = json_data
        token_info['token_user'] = token._user

        # Enforce token single use.
        token.delete()

        return token_info