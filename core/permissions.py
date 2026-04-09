from rest_framework.permissions import BasePermission

from .models import User


class IsAdminUser(BasePermission):
    message = 'Access restricted to admin users only.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsOperatorOrAdmin(BasePermission):
    message = 'Access restricted to operators and admins only.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in (User.Role.ADMIN, User.Role.OPERATOR)
        )
