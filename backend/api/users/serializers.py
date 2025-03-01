from rest_framework import serializers
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from api.users.models import User, Profile, Category


class ProfileSerializer(serializers.ModelSerializer):
    """
    User Profile serializer
    """
    class Meta:
        model = Profile
        exclude = ('id', 'user')


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer
    """
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = (
            'id',
            'first_name',
            'last_name',
            'email',
            'profile'
        )
        read_only_fields = ('id', 'email')


class CreateUserSerializer(serializers.ModelSerializer):
    """
    User registration serializer with email validation
    """
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = (
            'id',
            'password',
            'first_name',
            'last_name', 
            'email',
            'auth_token',
        )
        read_only_fields = ('auth_token',)

    def validate_email(self, value):
        """
        Validate email format and uniqueness
        """
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Invalid email format")
        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        
        return value

    def create(self, validated_data):
        """
        Create a new user with email as username
        """
        validated_data['username'] = validated_data.get('email')
        user = User.objects.create_user(**validated_data)
        return user


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model
    """
    note_count = serializers.ReadOnlyField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'color', 'note_count')
        read_only_fields = ('id', 'note_count')

    def validate(self, data):
        if not data.get('name'):
            raise serializers.ValidationError({'name': 'Name is required'})
        if not data.get('color'):
            raise serializers.ValidationError({'color': 'Color is required'})
        return data

    def create(self, validated_data):
        """
        Create category with authenticated user
        """
        return super().create(validated_data)

