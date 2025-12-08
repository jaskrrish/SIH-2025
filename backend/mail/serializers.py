from rest_framework import serializers
from .models import Email, Attachment
import json


class EmailSerializer(serializers.ModelSerializer):
    """Serializer for emails"""
    to_emails = serializers.SerializerMethodField()
    cc_emails = serializers.SerializerMethodField()
    bcc_emails = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    
    class Meta:
        model = Email
        fields = [
            'id', 'message_id', 'subject', 'from_email', 'from_name',
            'to_emails', 'cc_emails', 'bcc_emails',
            'body_text', 'body_html',
            'is_read', 'is_starred', 'is_encrypted',
            'sent_at', 'received_at', 'attachments'
        ]
    
    def get_to_emails(self, obj):
        try:
            return json.loads(obj.to_emails)
        except:
            return []
    
    def get_cc_emails(self, obj):
        try:
            return json.loads(obj.cc_emails) if obj.cc_emails else []
        except:
            return []
    
    def get_bcc_emails(self, obj):
        try:
            return json.loads(obj.bcc_emails) if obj.bcc_emails else []
        except:
            return []
    
    def get_attachments(self, obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for attachments"""
    class Meta:
        model = Attachment
        fields = [
            'id', 'filename', 'content_type', 'size', 
            'is_encrypted', 'security_level', 'encryption_metadata',
            'created_at'
        ]


class SendEmailSerializer(serializers.Serializer):
    """Serializer for sending emails with attachments"""
    account_id = serializers.IntegerField()
    to_emails = serializers.ListField(child=serializers.EmailField())
    subject = serializers.CharField()
    body_text = serializers.CharField()
    body_html = serializers.CharField(required=False, allow_blank=True)
    security_level = serializers.ChoiceField(
        choices=['regular', 'aes', 'qkd', 'qrng_pqc'],
        default='regular'
    )
    # Attachments will be handled via request.FILES, not in serializer
    # This allows multipart/form-data uploads
