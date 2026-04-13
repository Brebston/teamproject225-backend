import re
from django.core.exceptions import ValidationError


class PasswordUppercaseLetterValidator:
    """
    This class is a custom password validator that enforces specific security
    requirements for passwords. Its purpose is to ensure that passwords meet
    predefined conditions, such as containing at least one uppercase letter.

    :ivar validate: Validates whether the password meets the requirements.
    :type validate: method
    :ivar get_help_text: Returns a user-friendly message describing the
        password requirements.
    :type get_help_text: method
    """

    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError("Password must contain at least 1 uppercase letter")

    def get_help_text(self):
        return "Your password must contain att least 1 uppercase letter"


class MaxLengthPasswordValidator:
    """
    Validator for password maximum length.

    This class ensures that passwords do not exceed a maximum length limitation.
    Intended for use in scenarios where overly long passwords can cause issues
    with system constraints or security policies.

    Methods:
        validate: Validates whether the given password exceeds the maximum
                  allowable length.
    """
    def validate(self, password, user=None):
        if len(password) > 128:
            raise ValidationError("Password must be less than 128 characters")

    def get_help_text(self):
        return "Your password must be less than 128 characters"
