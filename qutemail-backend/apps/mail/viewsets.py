"""
Django REST Framework viewsets for email API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q

from mail.models import Email, Attachment, EmailLog, UserEmailSettings, Label
from mail.serializers import (
    EmailListSerializer,
    EmailDetailSerializer,
    EmailComposeSerializer,
    EmailActionSerializer,
    BulkEmailActionSerializer,
    AttachmentSerializer,
    AttachmentUploadSerializer,
    EmailLogSerializer,
    UserEmailSettingsSerializer,
    LabelSerializer,
)
from mail.services import EmailSendService, EmailReceiveService
from mail.tasks import fetch_user_emails


class EmailViewSet(viewsets.ModelViewSet):
    """
    ViewSet for email CRUD operations

    Endpoints:
    - GET /emails/ - List emails
    - POST /emails/ - Compose new email
    - GET /emails/{id}/ - Get email detail
    - PATCH /emails/{id}/ - Update email (e.g., mark as read)
    - DELETE /emails/{id}/ - Delete email
    - POST /emails/bulk_action/ - Perform bulk actions
    - POST /emails/{id}/reply/ - Reply to email
    - POST /emails/{id}/forward/ - Forward email
    """

    permission_classes = [IsAuthenticated]
    filterset_fields = ['folder', 'is_read', 'is_starred', 'is_encrypted', 'status']
    search_fields = ['subject', 'from_address', 'body_text']
    ordering_fields = ['date', 'created_at', 'size']
    ordering = ['-date']

    def get_queryset(self):
        """Filter emails for current user only"""
        return Email.objects.filter(user=self.request.user).select_related('user').prefetch_related('attachments', 'label_set')

    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return EmailListSerializer
        elif self.action == 'create':
            return EmailComposeSerializer
        return EmailDetailSerializer

    def perform_create(self, serializer):
        """Create email via EmailSendService"""
        # Serializer.create() handles the email composition
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Move email to trash instead of hard delete"""
        email = self.get_object()
        email.move_to_folder(Email.Folder.TRASH)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark email as read"""
        email = self.get_object()
        email.mark_as_read()
        return Response({'status': 'marked as read'})

    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """Mark email as unread"""
        email = self.get_object()
        email.is_read = False
        email.save()
        return Response({'status': 'marked as unread'})

    @action(detail=True, methods=['post'])
    def star(self, request, pk=None):
        """Star email"""
        email = self.get_object()
        email.toggle_star()
        return Response({'status': 'starred', 'is_starred': email.is_starred})

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Move email to different folder"""
        email = self.get_object()
        folder = request.data.get('folder')

        if folder not in dict(Email.Folder.choices):
            return Response(
                {'error': 'Invalid folder'},
                status=status.HTTP_400_BAD_REQUEST
            )

        email.move_to_folder(folder)
        return Response({'status': 'moved', 'folder': folder})

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """Reply to email"""
        original_email = self.get_object()

        # Prepare reply data
        reply_data = {
            'to_addresses': [original_email.from_address],
            'subject': f"Re: {original_email.subject}" if not original_email.subject.startswith('Re:') else original_email.subject,
            'body_text': request.data.get('body_text', ''),
            'body_html': request.data.get('body_html', ''),
            'in_reply_to': original_email.message_id,
            'references': f"{original_email.references or ''} {original_email.message_id}".strip(),
            'encrypt': request.data.get('encrypt'),
        }

        serializer = EmailComposeSerializer(data=reply_data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        email = serializer.save()

        return Response(
            EmailDetailSerializer(email, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def forward(self, request, pk=None):
        """Forward email"""
        original_email = self.get_object()

        forward_data = {
            'to_addresses': request.data.get('to_addresses', []),
            'subject': f"Fwd: {original_email.subject}" if not original_email.subject.startswith('Fwd:') else original_email.subject,
            'body_text': f"\n\n--- Forwarded message ---\nFrom: {original_email.from_address}\nDate: {original_email.date}\nSubject: {original_email.subject}\n\n{original_email.body_text}",
            'body_html': request.data.get('body_html', ''),
            'encrypt': request.data.get('encrypt'),
        }

        serializer = EmailComposeSerializer(data=forward_data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        email = serializer.save()

        # Copy attachments if requested
        if request.data.get('include_attachments', False):
            for attachment in original_email.attachments.all():
                Attachment.objects.create(
                    email=email,
                    filename=attachment.filename,
                    content_type=attachment.content_type,
                    size=attachment.size,
                    data=attachment.data,
                    checksum=attachment.checksum,
                )

        return Response(
            EmailDetailSerializer(email, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk actions on multiple emails"""
        serializer = BulkEmailActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email_ids = serializer.validated_data['email_ids']
        action_type = serializer.validated_data['action']
        folder = serializer.validated_data.get('folder')

        # Get emails
        emails = Email.objects.filter(id__in=email_ids, user=request.user)

        if not emails.exists():
            return Response(
                {'error': 'No emails found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Perform action
        count = 0
        for email in emails:
            if action_type == 'mark_read':
                email.mark_as_read()
            elif action_type == 'mark_unread':
                email.is_read = False
                email.save()
            elif action_type == 'star':
                email.is_starred = True
                email.save()
            elif action_type == 'unstar':
                email.is_starred = False
                email.save()
            elif action_type == 'move':
                email.move_to_folder(folder)
            elif action_type == 'delete':
                email.move_to_folder(Email.Folder.TRASH)

            count += 1

        return Response({
            'status': 'success',
            'action': action_type,
            'count': count
        })

    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Trigger manual email sync"""
        folder = request.data.get('folder', 'INBOX')

        # Trigger async task
        task = fetch_user_emails.delay(request.user.id, folder)

        return Response({
            'status': 'syncing',
            'task_id': task.id,
            'folder': folder
        })

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Get logs for specific email"""
        email = self.get_object()
        logs = EmailLog.objects.filter(email=email).order_by('-created_at')
        serializer = EmailLogSerializer(logs, many=True)
        return Response(serializer.data)


class AttachmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for email attachments (read-only)

    Endpoints:
    - GET /attachments/ - List attachments
    - GET /attachments/{id}/ - Get attachment detail
    - GET /attachments/{id}/download/ - Download attachment
    - POST /attachments/upload/ - Upload attachment for composing
    """

    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter attachments for current user's emails only"""
        return Attachment.objects.filter(email__user=self.request.user).select_related('email')

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download attachment as binary file"""
        from django.http import HttpResponse

        attachment = self.get_object()

        response = HttpResponse(
            bytes(attachment.data),
            content_type=attachment.content_type
        )
        response['Content-Disposition'] = f'attachment; filename="{attachment.filename}"'
        response['Content-Length'] = attachment.size

        return response

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload attachment before composing email"""
        serializer = AttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attachment_data = serializer.save()

        # For now, return the attachment data
        # In production, you might store this temporarily (e.g., in Redis or temp file)
        return Response({
            'filename': attachment_data['filename'],
            'content_type': attachment_data['content_type'],
            'size': attachment_data['size'],
            'checksum': attachment_data['checksum'],
        }, status=status.HTTP_201_CREATED)


class UserEmailSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user email settings

    Endpoints:
    - GET /settings/ - Get current user's settings
    - PATCH /settings/ - Update settings
    """

    serializer_class = UserEmailSettingsSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        """Return only current user's settings"""
        return UserEmailSettings.objects.filter(user=self.request.user)

    def get_object(self):
        """Get or create settings for current user"""
        obj, created = UserEmailSettings.objects.get_or_create(
            user=self.request.user,
            defaults={
                'email_address': f"{self.request.user.username}@qutemail.local",
                'display_name': self.request.user.get_full_name() or self.request.user.username,
            }
        )
        return obj

    def list(self, request, *args, **kwargs):
        """Return single settings object instead of list"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def update_storage(self, request):
        """Manually trigger storage usage update"""
        settings = self.get_object()
        settings.update_storage_usage()

        return Response({
            'storage_used_mb': settings.storage_used_mb,
            'storage_quota_mb': settings.storage_quota_mb,
            'storage_usage_percentage': settings.get_storage_usage_percentage(),
        })


class LabelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for email labels/tags

    Endpoints:
    - GET /labels/ - List labels
    - POST /labels/ - Create label
    - PATCH /labels/{id}/ - Update label
    - DELETE /labels/{id}/ - Delete label
    - POST /labels/{id}/apply/ - Apply label to emails
    """

    serializer_class = LabelSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter labels for current user"""
        return Label.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Set user when creating label"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Apply label to emails"""
        label = self.get_object()
        email_ids = request.data.get('email_ids', [])

        if not email_ids:
            return Response(
                {'error': 'email_ids required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get emails
        emails = Email.objects.filter(id__in=email_ids, user=request.user)

        # Apply label
        for email in emails:
            email.labels.add(label)

        return Response({
            'status': 'success',
            'label': label.name,
            'applied_to': emails.count()
        })

    @action(detail=True, methods=['post'])
    def remove(self, request, pk=None):
        """Remove label from emails"""
        label = self.get_object()
        email_ids = request.data.get('email_ids', [])

        if not email_ids:
            return Response(
                {'error': 'email_ids required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get emails
        emails = Email.objects.filter(id__in=email_ids, user=request.user)

        # Remove label
        for email in emails:
            email.labels.remove(label)

        return Response({
            'status': 'success',
            'label': label.name,
            'removed_from': emails.count()
        })
