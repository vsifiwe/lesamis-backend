from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Member, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model         = User
    list_display  = ('email', 'full_name', 'role', 'is_active', 'is_staff')
    list_filter   = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'full_name')
    ordering      = ('-created_at',)

    fieldsets = (
        (None,             {'fields': ('email', 'password')}),
        (_('Personal'),    {'fields': ('full_name',)}),
        (_('Access'),      {'fields': ('role', 'member')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Timestamps'),  {'fields': ('last_login', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'role'),
        }),
    )

    readonly_fields = ('last_login', 'created_at', 'updated_at')


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display  = ('member_number', 'first_name', 'last_name', 'email', 'status', 'join_date')
    list_filter   = ('status',)
    search_fields = ('member_number', 'first_name', 'last_name', 'email')
    ordering      = ('-created_at',)
    readonly_fields = ('member_number', 'created_at', 'updated_at')
