from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import EmailAccount
from .serializers import EmailAccountSerializer, EmailAccountListSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def connect_account(request):
    """
    Connect a new email account (Gmail, Outlook, etc.)
    POST /api/email-accounts/connect
    Body: { provider, email, app_password, [custom imap/smtp settings] }
    """
    serializer = EmailAccountSerializer(data=request.data)
    if serializer.is_valid():
        # Associate with current user
        account = serializer.save(user=request.user)
        
        # Return account info (without password)
        return Response(
            EmailAccountListSerializer(account).data,
            status=status.HTTP_201_CREATED
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_accounts(request):
    """
    List all connected email accounts for current user
    GET /api/email-accounts/
    """
    accounts = EmailAccount.objects.filter(user=request.user, is_active=True)
    serializer = EmailAccountListSerializer(accounts, many=True)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request, account_id):
    """
    Delete/disconnect an email account
    DELETE /api/email-accounts/{account_id}
    """
    try:
        account = EmailAccount.objects.get(id=account_id, user=request.user)
        account.delete()
        return Response({'message': 'Account deleted successfully'}, status=status.HTTP_200_OK)
    except EmailAccount.DoesNotExist:
        return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
