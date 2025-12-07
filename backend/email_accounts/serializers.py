from rest_framework import serializers
from .models import EmailAccount


class EmailAccountSerializer(serializers.ModelSerializer):
    """Serializer for email accounts"""
    app_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = EmailAccount
        fields = [
            'id', 'provider', 'email', 'app_password',
            'imap_host', 'imap_port', 'imap_use_ssl',
            'smtp_host', 'smtp_port', 'smtp_use_tls',
            'is_active', 'last_synced', 'created_at'
        ]
        read_only_fields = ['id', 'last_synced', 'created_at']
    
    def create(self, validated_data):
        app_password = validated_data.pop('app_password')
        account = EmailAccount(**validated_data)
        account.set_app_password(app_password)
        account.save()
        return account


class EmailAccountListSerializer(serializers.ModelSerializer):
    """Serializer for listing email accounts (without credentials)"""
    class Meta:
        model = EmailAccount
        fields = [
            'id', 'provider', 'email', 'is_active', 'last_synced', 'created_at'
        ]
