from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Member


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone',
            'national_id', 'status', 'role', 'join_date',
            'exit_date', 'suspended_date', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateMemberSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Member
        fields = [
            'first_name', 'last_name', 'email', 'password',
            'phone', 'national_id', 'role', 'join_date',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        member = Member(**validated_data)
        member.set_password(password)
        member.save()
        return member
