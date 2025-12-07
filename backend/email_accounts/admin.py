from django.contrib import admin
from .models import EmailAccount


@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ['email', 'provider', 'user', 'is_active', 'last_synced', 'created_at']
    list_filter = ['provider', 'is_active', 'created_at']
    search_fields = ['email', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'last_synced']
    
    fieldsets = (
        (None, {'fields': ('user', 'provider', 'email', 'is_active')}),
        ('IMAP Settings', {'fields': ('imap_host', 'imap_port', 'imap_use_ssl')}),
        ('SMTP Settings', {'fields': ('smtp_host', 'smtp_port', 'smtp_use_tls')}),
        ('Status', {'fields': ('last_synced', 'created_at', 'updated_at')}),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing
            return self.readonly_fields + ['user', 'provider', 'email']
        return self.readonly_fields
