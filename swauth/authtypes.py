# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Pablo Llopis 2011


"""This module hosts available auth types for encoding and matching user keys.
For adding a new auth type, simply write a class that satisfies the following
conditions:

- For the class name, capitalize first letter only. This makes sure the user
  can specify an all-lowercase config option such as "plaintext" or "sha1".
  Swauth takes care of capitalizing the first letter before instantiating it.
- Write an encode(key) method that will take a single argument, the user's key,
  and returns the encoded string. For plaintext, this would be
  "plaintext:<key>"
- Write a match(key, creds) method that will take two arguments: the user's
  key, and the user's retrieved credentials. Return a boolean value that
  indicates whether the match is True or False.
"""

import base64
import hashlib
import os
import six
import string
import sys


#: Maximum length any valid token should ever be.
MAX_TOKEN_LENGTH = 5000


def validate_creds(creds):
    """Parse and validate user credentials whether format is right

    :param creds: User credentials
    :returns: Auth_type class instance and parsed user credentials in dict
    :raises ValueError: If credential format is wrong (eg: bad auth_type)
    """
    try:
        auth_type, auth_rest = creds.split(':', 1)
    except ValueError:
        raise ValueError("Missing ':' in %s" % creds)
    authtypes = sys.modules[__name__]
    auth_encoder = getattr(authtypes, auth_type.title(), None)
    if auth_encoder is None:
        raise ValueError('Invalid auth_type: %s' % auth_type)
    auth_encoder = auth_encoder()
    parsed_creds = dict(type=auth_type, salt=None, hash=None)
    parsed_creds.update(auth_encoder.validate(auth_rest))
    return auth_encoder, parsed_creds


class Plaintext(object):
    """Provides a particular auth type for encoding format for encoding and
    matching user keys.

    This class must be all lowercase except for the first character, which
    must be capitalized. encode and match methods must be provided and are
    the only ones that will be used by swauth.
    """
    def encode(self, key):
        """Encodes a user key into a particular format. The result of this method
        will be used by swauth for storing user credentials.

        :param key: User's secret key
        :returns: A string representing user credentials
        """
        return "plaintext:%s" % key

    def match(self, key, creds, **kwargs):
        """Checks whether the user-provided key matches the user's credentials

        :param key: User-supplied key
        :param creds: User's stored credentials
        :param kwargs: Extra keyword args for compatibility reason with
                       other auth_type classes
        :returns: True if the supplied key is valid, False otherwise
        """
        return self.encode(key) == creds

    def validate(self, auth_rest):
        """Validate user credentials whether format is right for Plaintext

        :param auth_rest: User credentials' part without auth_type
        :return: Dict with a hash part of user credentials
        :raises ValueError: If credentials' part has zero length
        """
        if len(auth_rest) == 0:
            raise ValueError("Key must have non-zero length!")
        return dict(hash=auth_rest)


class Sha1(object):
    """Provides a particular auth type for encoding format for encoding and
    matching user keys.

    This class must be all lowercase except for the first character, which
    must be capitalized. encode and match methods must be provided and are
    the only ones that will be used by swauth.
    """

    def encode_w_salt(self, salt, key):
        """Encodes a user key with salt into a particular format. The result of
        this method will be used internally.

        :param salt: Salt for hashing
        :param key: User's secret key
        :returns: A string representing user credentials
        """
        enc_key = salt + key
        if not six.PY2:
            enc_key = enc_key.encode('utf8')
        enc_val = hashlib.sha1(enc_key).hexdigest()
        return "sha1:%s$%s" % (salt, enc_val)

    def encode(self, key):
        """Encodes a user key into a particular format. The result of this method
        will be used by swauth for storing user credentials.

        If salt is not manually set in conf file, a random salt will be
        generated and used.

        :param key: User's secret key
        :returns: A string representing user credentials
        """
        salt = self.salt or base64.b64encode(os.urandom(32)).rstrip()
        if not six.PY2 and isinstance(salt, bytes):
            salt = salt.decode('ascii')
        return self.encode_w_salt(salt, key)

    def match(self, key, creds, salt, **kwargs):
        """Checks whether the user-provided key matches the user's credentials

        :param key: User-supplied key
        :param creds: User's stored credentials
        :param salt: Salt for hashing
        :param kwargs: Extra keyword args for compatibility reason with
                       other auth_type classes
        :returns: True if the supplied key is valid, False otherwise
        """
        return self.encode_w_salt(salt, key) == creds

    def validate(self, auth_rest):
        """Validate user credentials whether format is right for Sha1

        :param auth_rest: User credentials' part without auth_type
        :return: Dict with a hash and a salt part of user credentials
        :raises ValueError: If credentials' part doesn't contain delimiter
                            between a salt and a hash.
        """
        try:
            auth_salt, auth_hash = auth_rest.split('$')
        except ValueError:
            raise ValueError("Missing '$' in %s" % auth_rest)

        if len(auth_salt) == 0:
            raise ValueError("Salt must have non-zero length!")
        if len(auth_hash) != 40:
            raise ValueError("Hash must have 40 chars!")
        if not all(c in string.hexdigits for c in auth_hash):
            raise ValueError("Hash must be hexadecimal!")

        return dict(salt=auth_salt, hash=auth_hash)


class Sha512(object):
    """Provides a particular auth type for encoding format for encoding and
    matching user keys.

    This class must be all lowercase except for the first character, which
    must be capitalized. encode and match methods must be provided and are
    the only ones that will be used by swauth.
    """

    def encode_w_salt(self, salt, key):
        """Encodes a user key with salt into a particular format. The result of
        this method will be used internal.

        :param salt: Salt for hashing
        :param key: User's secret key
        :returns: A string representing user credentials
        """
        enc_key = '%s%s' % (salt, key)
        if not six.PY2:
            enc_key = enc_key.encode('utf8')
        enc_val = hashlib.sha512(enc_key).hexdigest()
        return "sha512:%s$%s" % (salt, enc_val)

    def encode(self, key):
        """Encodes a user key into a particular format. The result of this method
        will be used by swauth for storing user credentials.

        If salt is not manually set in conf file, a random salt will be
        generated and used.

        :param key: User's secret key
        :returns: A string representing user credentials
        """
        salt = self.salt or base64.b64encode(os.urandom(32)).rstrip()
        if not six.PY2 and isinstance(salt, bytes):
            salt = salt.decode('ascii')
        return self.encode_w_salt(salt, key)

    def match(self, key, creds, salt, **kwargs):
        """Checks whether the user-provided key matches the user's credentials

        :param key: User-supplied key
        :param creds: User's stored credentials
        :param salt: Salt for hashing
        :param kwargs: Extra keyword args for compatibility reason with
                       other auth_type classes
        :returns: True if the supplied key is valid, False otherwise
        """
        return self.encode_w_salt(salt, key) == creds

    def validate(self, auth_rest):
        """Validate user credentials whether format is right for Sha512

        :param auth_rest: User credentials' part without auth_type
        :return: Dict with a hash and a salt part of user credentials
        :raises ValueError: If credentials' part doesn't contain delimiter
                            between a salt and a hash.
        """
        try:
            auth_salt, auth_hash = auth_rest.split('$')
        except ValueError:
            raise ValueError("Missing '$' in %s" % auth_rest)

        if len(auth_salt) == 0:
            raise ValueError("Salt must have non-zero length!")
        if len(auth_hash) != 128:
            raise ValueError("Hash must have 128 chars!")
        if not all(c in string.hexdigits for c in auth_hash):
            raise ValueError("Hash must be hexadecimal!")

        return dict(salt=auth_salt, hash=auth_hash)
