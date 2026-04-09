from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Member, MemberShareAccount, User


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
    default_password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model  = Member
        fields = ['first_name', 'last_name', 'phone', 'email', 'join_date', 'default_password']
        extra_kwargs = {
            'email': {'required': True, 'allow_blank': False},
        }

    def create(self, validated_data):
        password = validated_data.pop('default_password')
        member = Member.objects.create(**validated_data)
        User.objects.create_user(
            email=member.email,
            password=password,
            full_name=member.get_full_name(),
            role=User.Role.VIEWER,
            member=member,
        )
        MemberShareAccount.objects.create(member=member)
        return member


class MemberShareAccountSerializer(serializers.ModelSerializer):
    total_value = serializers.IntegerField(read_only=True)

    class Meta:
        model  = MemberShareAccount
        fields = [
            'id', 'member', 'share_count', 'share_unit_value',
            'total_value', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'total_value', 'created_at', 'updated_at']


class AdjustSharesSerializer(serializers.Serializer):
    action    = serializers.ChoiceField(choices=['INCREASE', 'DECREASE'])
    member_id = serializers.UUIDField()
    amount    = serializers.IntegerField(min_value=1)
