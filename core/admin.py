from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import ContributionCycle, ContributionReceipt, ContributionReceiptItem, FundAccount, Member, MemberContributionObligation, MemberShareAccount, Penalty, SystemConfig, User


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


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Contribution Cycle Rules', {
            'fields': ('cycle_due_day', 'late_penalty_start_day', 'extra_penalty_start_day'),
        }),
        ('Fixed Contribution Amounts', {
            'fields': ('social_amount', 'social_plus_amount'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def has_add_permission(self, request):
        return not SystemConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


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


class ContributionReceiptItemInline(admin.TabularInline):
    model       = ContributionReceiptItem
    extra       = 0
    fields      = ('obligation', 'amount_applied')
    readonly_fields = ('created_at',)


@admin.register(ContributionReceipt)
class ContributionReceiptAdmin(admin.ModelAdmin):
    list_display   = ('__str__', 'received_date', 'payment_method', 'amount_received', 'status', 'created_by')
    list_filter    = ('status', 'payment_method')
    search_fields  = ('id',)
    ordering       = ('-received_date', '-created_at')
    readonly_fields = ('created_at', 'updated_at')
    inlines        = [ContributionReceiptItemInline]


@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display    = ('__str__', 'penalty_type', 'amount', 'auto_generated', 'waived', 'created_at')
    list_filter     = ('penalty_type', 'auto_generated', 'waived')
    search_fields   = ('contribution_obligation__member__member_number',)
    readonly_fields = ('created_at', 'updated_at')
