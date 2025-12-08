from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import UserRegistrationSerializer, UserSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new QuteMail user
    POST /api/auth/register
    Body: { username, name, password, confirm_password }
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Auto-configure email account for aalan@qutemail.tech
        if user.username == 'aalan':
            from email_accounts.models import EmailAccount
            try:
                EmailAccount.objects.create(
                    user=user,
                    provider='qutemail',
                    email=user.email,
                    imap_host='imappro.zoho.in',
                    imap_port=993,
                    imap_use_ssl=True,
                    smtp_host='smtppro.zoho.in',
                    smtp_port=587,
                    smtp_use_tls=True,
                    _app_password=EmailAccount._get_cipher().encrypt(b'Surya@123')
                )
                print(f"[REGISTER] Auto-configured email account for {user.email}")
            except Exception as e:
                print(f"[REGISTER] Failed to auto-configure email: {str(e)}")
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login user and get JWT tokens
    POST /api/auth/login
    Body: { username, password }
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Get current user info
    GET /api/auth/me
    Requires: Authorization: Bearer <token>
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)
