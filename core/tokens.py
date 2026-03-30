from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class MemberTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_admin'] = user.role == user.Role.ADMIN
        return token


class MemberTokenObtainPairView(TokenObtainPairView):
    serializer_class = MemberTokenObtainPairSerializer
