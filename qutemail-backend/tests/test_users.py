from django.contrib.auth import get_user_model
from mail.models import UserEmailSettings

User = get_user_model()

# Create test users
users_data = [
    ('alice', 'alice@qutemail.local', 'Alice Smith'),
    ('bob', 'bob@qutemail.local', 'Bob Johnson'),
    ('charlie', 'charlie@qutemail.local', 'Charlie Brown'),
]

for username, email, display_name in users_data:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email}
    )
    if created:
        user.set_password('testpass123')
        user.save()

    UserEmailSettings.objects.get_or_create(
        user=user,
        defaults={
            'email_address': email,
            'display_name': display_name,
            'enable_qkd_encryption': True,
            'auto_fetch_interval': 60,
            'storage_quota_mb': 1024,
        }
    )
    print(f"Created user: {username}")