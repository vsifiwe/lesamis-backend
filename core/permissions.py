from rest_framework.permissions import BasePermission


class IsAdminMember(BasePermission):
    message = 'Access restricted to admin members only.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == request.user.Role.ADMIN
        )
