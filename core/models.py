import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class MemberManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required.')
        email = self.normalize_email(email)
        extra_fields.setdefault('role', Member.Role.NORMAL)
        extra_fields.setdefault('status', Member.Status.ACTIVE)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', Member.Role.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class Member(AbstractBaseUser, PermissionsMixin):

    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        SUSPENDED = 'suspended', 'Suspended'
        EXITED    = 'exited',    'Exited'

    class Role(models.TextChoices):
        ADMIN  = 'admin',  'Admin'
        NORMAL = 'normal', 'Normal'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name  = models.CharField(max_length=150)
    last_name   = models.CharField(max_length=150)
    email       = models.EmailField(unique=True)
    phone       = models.CharField(max_length=30, blank=True)
    national_id = models.CharField(max_length=50, blank=True)
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    role        = models.CharField(max_length=20, choices=Role.choices, default=Role.NORMAL)
    join_date   = models.DateField(default=timezone.now)

    exit_date      = models.DateField(null=True, blank=True)
    suspended_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    is_staff  = models.BooleanField(default=False)

    objects = MemberManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name        = 'Member'
        verbose_name_plural = 'Members'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name} <{self.email}>'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name
