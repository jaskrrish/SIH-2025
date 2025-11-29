from django.contrib import admin
from .models import Mailbox, Email, EmailAttachment, EmailDeliveryStatus


@admin.register(Mailbox)
class MailboxAdmin(admin.ModelAdmin):
    list_display = ['email_address', 'user', 'quota_percentage', 'used_bytes', 'created_at']
    list_filter = ['created_at']
    search_fields = ['email_address', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

    def quota_percentage(self, obj):
        return f"{obj.quota_percentage:.1f}%"
    quota_percentage.short_description = 'Quota Used'


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ['subject', 'from_address', 'mailbox', 'is_internal', 'folder', 'is_read', 'received_at']
    list_filter = ['is_internal', 'folder', 'is_read', 'is_flagged', 'received_at']
    search_fields = ['subject', 'from_address', 'message_id']
    readonly_fields = ['received_at', 'sent_at', 'size_bytes', 'message_id']
    date_hierarchy = 'received_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('mailbox', 'message_id', 'from_address', 'to_addresses', 'cc_addresses', 'bcc_addresses', 'subject')
        }),
        ('Content', {
            'fields': ('body_plain', 'body_html')
        }),
        ('QKD Encryption (Internal Only)', {
            'fields': ('is_internal', 'qkd_key_id', 'qkd_ciphertext', 'qkd_nonce', 'qkd_auth_tag'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('folder', 'is_read', 'is_flagged', 'size_bytes', 'headers')
        }),
        ('Timestamps', {
            'fields': ('received_at', 'sent_at')
        }),
    )


@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'email', 'content_type', 'size_bytes', 'is_inline', 'created_at']
    list_filter = ['content_type', 'is_inline', 'created_at']
    search_fields = ['filename', 'email__subject']
    readonly_fields = ['created_at']


@admin.register(EmailDeliveryStatus)
class EmailDeliveryStatusAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'status', 'attempts', 'last_attempt_at', 'next_retry_at', 'delivered_at']
    list_filter = ['status', 'created_at']
    search_fields = ['recipient', 'error_message']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Delivery Information', {
            'fields': ('email', 'recipient', 'status')
        }),
        ('Attempts', {
            'fields': ('attempts', 'last_attempt_at', 'next_retry_at')
        }),
        ('Response Details', {
            'fields': ('smtp_response', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('delivered_at', 'created_at', 'updated_at')
        }),
    )
