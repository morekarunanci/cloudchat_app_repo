import logging
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Profile   # adjust if your model path is different

logger = logging.getLogger(__name__)


class RegisterService:
    """
    Service layer for handling user registration logic
    """

    @staticmethod
    def validate_data(data):
        required_fields = [
            "first_name", "last_name", "username",
            "email", "password", "dob"
        ]

        # Check required fields
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f"{field} is required")

        # Username exists
        if User.objects.filter(username=data["username"]).exists():
            raise ValidationError("Username already exists")

        # Email exists
        if User.objects.filter(email=data["email"]).exists():
            raise ValidationError("Email already exists")

        # Password validation
        if len(data["password"]) < 6:
            raise ValidationError("Password must be at least 6 characters")

    @staticmethod
    @transaction.atomic
    def create_user(data):
        """
        Creates user + profile inside a transaction
        """

        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )

        profile = Profile.objects.create(
            user=user,
            dob=data["dob"]
        )

        logger.info(f"[REGISTER] New user created: {user.username}")

        return user, profile

    @classmethod
    def register(cls, data):
        """
        Main entry point for registration
        """

        cls.validate_data(data)
        return cls.create_user(data)