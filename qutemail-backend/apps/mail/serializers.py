"""
Django REST Framework serializers for email models
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from mail.models import Email, Attachment, EmailQueue, EmailLog, UserEmailSettings, Label, EmailLabel

User = get_user_model()


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for email attachments"""

    # Don't expose raw binary data in list views
    data = serializers.SerializerMethodField()
    size_kb = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            'id',
            'filename',
            'content_type',
            'size',
            'size_kb',
            'checksum',
            'content_id',
            'is_inline',
            'created_at',
            'data',  # Only included in detail view
        ]
        read_only_fields = ['id', 'checksum', 'created_at', 'size_kb']

    def get_data(self, obj):
        """Only return data in detail view, not list view"""
        view = self.context.get('view')
        if view and view.action == 'retrieve':
            # Return base64 encoded data for download
            import base64
            return base64.b64encode(bytes(obj.data)).decode('utf-8')
        return None

    def get_size_kb(self, obj):
        """Return size in KB"""
        return round(obj.size / 1024, 2)


class LabelSerializer(serializers.ModelSerializer):
    """Serializer for email labels/tags"""

    class Meta:
        model = Label
        fields = ['id', 'name', 'color', 'created_at']
        read_only_fields = ['id', 'created_at']


class EmailListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for email list views"""

    from_name = serializers.CharField(source='from_address', read_only=True)
    to_count = serializers.SerializerMethodField()
    has_attachments = serializers.BooleanField(read_only=True)
    is_encrypted = serializers.BooleanField(read_only=True)
    labels = LabelSerializer(many=True, read_only=True, source='label_set')

    class Meta:
        model = Email
        fields = [
            'id',
            'message_id',
            'folder',
            'subject',
            'from_address',
            'from_name',
            'to_addresses',
            'to_count',
            'date',
            'is_read',
            'is_starred',
            'has_attachments',
            'is_encrypted',
            'status',
            'size',
            'created_at',
            'labels',
        ]
        read_only_fields = ['id', 'message_id', 'created_at']

    def get_to_count(self, obj):
        """Return count of recipients"""
        return len(obj.to_addresses) if obj.to_addresses else 0


class EmailDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single email view"""

    attachments = AttachmentSerializer(many=True, read_only=True)
    labels = LabelSerializer(many=True, read_only=True, source='label_set')
    from_name = serializers.CharField(source='from_address', read_only=True)

    class Meta:
        model = Email
        fields = [
            'id',
            'message_id',
            'folder',
            'subject',
            'from_address',
            'from_name',
            'to_addresses',
            'cc_addresses',
            'bcc_addresses',
            'date',
            'body_text',
            'body_html',
            'is_read',
            'is_starred',
            'has_attachments',
            'is_encrypted',
            'qkd_key_id',
            'in_reply_to',
            'references',
            'status',
            'size',
            'sent_at',
            'created_at',
            'updated_at',
            'attachments',
            'labels',
        ]
        read_only_fields = [
            'id',
            'message_id',
            'is_encrypted',
            'qkd_key_id',
            'status',
            'sent_at',
            'created_at',
            'updated_at',
        ]


class EmailComposeSerializer(serializers.Serializer):
    """Serializer for composing new emails"""

    to_addresses = serializers.ListField(
        child=serializers.EmailField(),
        required=True,
        min_length=1
    )
    cc_addresses = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        default=list
    )
    bcc_addresses = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        default=list
    )
    subject = serializers.CharField(max_length=998, required=True)
    body_text = serializers.CharField(required=True, allow_blank=False)
    body_html = serializers.CharField(required=False, allow_blank=True, default='')
    encrypt = serializers.BooleanField(required=False, default=None)
    save_draft = serializers.BooleanField(required=False, default=False)
    in_reply_to = serializers.CharField(required=False, allow_null=True, default=None)
    references = serializers.CharField(required=False, allow_null=True, default=None)

    # Attachments handled separately via multipart upload
    attachment_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        help_text="List of attachment IDs (upload attachments first)"
    )

    def validate_to_addresses(self, value):
        """Validate recipient email addresses"""
        if not value:
            raise serializers.ValidationError("At least one recipient is required")
        return value

    def create(self, validated_data):
        """Create email using EmailSendService"""
        from mail.services import EmailSendService

        user = self.context['request'].user
        service = EmailSendService(user)

        # Extract attachment data if needed
        attachment_ids = validated_data.pop('attachment_ids', [])

        # Compose email
        email = service.compose_email(**validated_data)

        return email


class EmailActionSerializer(serializers.Serializer):
    """Serializer for email actions (mark read, star, move, etc.)"""

    action = serializers.ChoiceField(
        choices=['mark_read', 'mark_unread', 'star', 'unstar', 'move', 'delete'],
        required=True
    )
    folder = serializers.ChoiceField(
        choices=[choice[0] for choice in Email.Folder.choices],
        required=False
    )

    def validate(self, data):
        """Validate that folder is provided for move action"""
        if data.get('action') == 'move' and not data.get('folder'):
            raise serializers.ValidationError("Folder is required for move action")
        return data


class EmailLogSerializer(serializers.ModelSerializer):
    """Serializer for email event logs"""

    class Meta:
        model = EmailLog
        fields = [
            'id',
            'event_type',
            'message',
            'metadata',
            'error_message',
            'traceback',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class UserEmailSettingsSerializer(serializers.ModelSerializer):
    """Serializer for user email settings"""

    storage_usage_mb = serializers.SerializerMethodField()
    storage_usage_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UserEmailSettings
        fields = [
            'id',
            'email_address',
            'display_name',
            'signature',
            'enable_qkd_encryption',
            'auto_fetch_interval',
            'storage_quota_mb',
            'storage_used_mb',
            'storage_usage_mb',
            'storage_usage_percentage',
            'last_sync_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'email_address',
            'storage_used_mb',
            'last_sync_at',
            'created_at',
            'updated_at',
        ]

    def get_storage_usage_mb(self, obj):
        """Return storage usage in MB"""
        return obj.storage_used_mb

    def get_storage_usage_percentage(self, obj):
        """Return storage usage percentage"""
        return obj.get_storage_usage_percentage()


class AttachmentUploadSerializer(serializers.Serializer):
    """Serializer for uploading attachments before composing email"""

    file = serializers.FileField(required=True)
    is_inline = serializers.BooleanField(default=False)
    content_id = serializers.CharField(required=False, allow_null=True)

    def validate_file(self, value):
        """Validate file size (max 25MB)"""
        max_size = 25 * 1024 * 1024  # 25 MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size ({value.size} bytes) exceeds maximum allowed size (25 MB)"
            )
        return value

    def create(self, validated_data):
        """Create temporary attachment"""
        import hashlib

        file = validated_data['file']
        file_data = file.read()

        # Calculate checksum
        checksum = hashlib.sha256(file_data).hexdigest()

        # This would typically be stored temporarily
        # For now, return the data for immediate use
        return {
            'filename': file.name,
            'content_type': file.content_type,
            'size': len(file_data),
            'data': file_data,
            'checksum': checksum,
            'is_inline': validated_data.get('is_inline', False),
            'content_id': validated_data.get('content_id'),
        }


class BulkEmailActionSerializer(serializers.Serializer):
    """Serializer for bulk email actions"""

    email_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        min_length=1
    )
    action = serializers.ChoiceField(
        choices=['mark_read', 'mark_unread', 'star', 'unstar', 'move', 'delete'],
        required=True
    )
    folder = serializers.ChoiceField(
        choices=[choice[0] for choice in Email.Folder.choices],
        required=False
    )

    def validate(self, data):
        """Validate bulk action data"""
        if data.get('action') == 'move' and not data.get('folder'):
            raise serializers.ValidationError("Folder is required for move action")
        return data
