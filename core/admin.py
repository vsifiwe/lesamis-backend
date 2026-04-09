from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import ContributionCycle, FundAccount, Member, MemberContributionObligation, MemberShareAccount, User


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


@admin.register(ContributionCycle)
class ContributionCycleAdmin(admin.ModelAdmin):
    list_display  = ('__str__', 'due_date', 'late_penalty_start_date', 'extra_penalty_start_date', 'status')
    list_filter   = ('status', 'year')
    ordering      = ('-year', '-month')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FundAccount)
class FundAccountAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'allow_negative', 'is_active')
    list_filter   = ('is_active', 'allow_negative')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MemberContributionObligation)
class MemberContributionObligationAdmin(admin.ModelAdmin):
    list_display   = ('member', 'contribution_cycle', 'total_amount_expected', 'status')
    list_filter    = ('status', 'contribution_cycle__year')
    search_fields  = ('member__first_name', 'member__last_name', 'member__member_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MemberShareAccount)
class MemberShareAccountAdmin(admin.ModelAdmin):
    list_display  = ('member', 'share_count', 'share_unit_value', 'total_value')
    search_fields = ('member__first_name', 'member__last_name', 'member__member_number')
    readonly_fields = ('created_at', 'updated_at')
