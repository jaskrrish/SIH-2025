from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager for QuteMail users"""
    
    def create_user(self, username, password=None, **extra_fields):
        """Create and return a regular user"""
        if not username:
            raise ValueError('Username is required')
        
        email = f"{username}@qutemail.tech"
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for QuteMail
    - Username becomes the email prefix (username@qutemail.tech)
    - Email is auto-generated from username
    """
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)  # Auto-generated: username@qutemail.com
    name = models.CharField(max_length=255, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = 'QuteMail User'
        verbose_name_plural = 'QuteMail Users'
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        # Auto-generate email from username
        if not self.email:
            self.email = f"{self.username}@qutemail.com"
        super().save(*args, **kwargs)
