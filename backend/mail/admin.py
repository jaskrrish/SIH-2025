from django.contrib import admin
from .models import Email, Attachment


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ['subject', 'from_email', 'user', 'account', 'is_read', 'is_encrypted', 'sent_at']
    list_filter = ['is_read', 'is_starred', 'is_encrypted', 'account', 'sent_at']
    search_fields = ['subject', 'from_email', 'body_text']
    readonly_fields = ['message_id', 'received_at', 'sent_at']
    date_hierarchy = 'sent_at'
    
    fieldsets = (
        ('Basic Info', {'fields': ('user', 'account', 'message_id', 'subject')}),
        ('Sender/Recipients', {'fields': ('from_email', 'from_name', 'to_emails', 'cc_emails')}),
        ('Content', {'fields': ('body_text', 'body_html')}),
        ('Flags', {'fields': ('is_read', 'is_starred', 'is_encrypted')}),
        ('Timestamps', {'fields': ('sent_at', 'received_at')}),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing
            return self.readonly_fields + ['user', 'account', 'from_email']
        return self.readonly_fields


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'email', 'content_type', 'size', 'created_at']
    list_filter = ['content_type', 'created_at']
    search_fields = ['filename', 'email__subject']
    readonly_fields = ['created_at']
