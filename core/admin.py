from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Member


@admin.register(Member)
class MemberAdmin(UserAdmin):
    model = Member
    list_display  = ('email', 'first_name', 'last_name', 'role', 'status', 'is_staff')
    list_filter   = ('role', 'status', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name', 'national_id')
    ordering      = ('-created_at',)

    fieldsets = (
        (None,             {'fields': ('email', 'password')}),
        (_('Personal'),    {'fields': ('first_name', 'last_name', 'phone', 'national_id')}),
        (_('Membership'),  {'fields': ('role', 'status', 'join_date', 'exit_date', 'suspended_date')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Timestamps'),  {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'role', 'status'),
        }),
    )

    readonly_fields = ('created_at', 'updated_at')
