from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Member, User


class UserSerializer(serializers.ModelSerializer):
    last_login_at = serializers.DateTimeField(source='last_login', read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'full_name', 'role', 'is_active',
            'last_login_at', 'member', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'last_login_at', 'created_at', 'updated_at']


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model  = User
        fields = ['email', 'full_name', 'password', 'role', 'member']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Member
        fields = [
            'id', 'member_number', 'first_name', 'last_name',
            'phone', 'email', 'status', 'join_date', 'exit_date',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'member_number', 'created_at', 'updated_at']


class CreateMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Member
        fields = ['first_name', 'last_name', 'phone', 'email', 'join_date']

    def create(self, validated_data):
        return Member.objects.create(**validated_data)
