# Domain Migration: qutemail.com → qutemail.tech

## Overview
QuteMail has been migrated from `qutemail.com` to `qutemail.tech` domain with Zoho Mail hosting.

## Changes Summary

### Backend Changes (✅ Complete)

#### 1. accounts/models.py
- **Change**: Email generation updated from `@qutemail.com` to `@qutemail.tech`
- **Impact**: All new user registrations will receive `username@qutemail.tech` email addresses

#### 2. accounts/views.py
- **Change**: Added auto-configuration for `aalan` user during registration
- **Details**: When `username == 'aalan'`, the system automatically creates an `EmailAccount` with:
  - Provider: `qutemail`
  - Email: `aalan@qutemail.tech`
  - IMAP: `imappro.zoho.in:993` (SSL)
  - SMTP: `smtppro.zoho.in:587` (TLS)
  - Password: `Surya@123` (encrypted)

#### 3. email_accounts/models.py
- **Change**: Added `qutemail` as a new provider option
- **Details**: 
  - Added `('qutemail', 'QuTeMail')` to `PROVIDER_CHOICES`
  - Added auto-configuration in `save()` method for `qutemail` provider with Zoho Mail settings

### Frontend Changes (✅ Complete)

#### 1. Auth.tsx
- **Line 193**: Updated description text: `"Get your own @qutemail.tech address..."`
- **Line 217**: Updated input label: `@qutemail.tech`
- **Line 223**: Updated email preview: `username@qutemail.tech`

#### 2. Dashboard.tsx
- **Change**: Added comment explaining QuTeMail provider is not in the connect modal
- **Reason**: QuTeMail requires special handling (only aalan@qutemail.tech is configured)

#### 3. Mailbox.tsx
- **New Function**: Added `isAccountConfigured()` helper function
- **Updated**: Sync button now checks if account is configured before syncing
- **Updated**: Compose button shows alert for unconfigured accounts
- **Updated**: Reply button shows alert for unconfigured accounts
- **Updated**: Send email checks configuration before sending
- **Updated**: Email loading skips unconfigured accounts

## Configuration Details

### Zoho Mail Settings
```
IMAP Server: imappro.zoho.in
IMAP Port: 993
IMAP Security: SSL

SMTP Server: smtppro.zoho.in
SMTP Port: 587
SMTP Security: TLS
```

### Configured Account
- **Email**: aalan@qutemail.tech
- **Password**: Surya@123
- **Status**: Auto-configured on registration

### Other Accounts
- **Email Format**: `username@qutemail.tech`
- **SMTP/IMAP**: Not configured
- **Behavior**: Shows "not configured" message when attempting to sync/compose

## User Experience

### For User 'aalan'
1. Register with username `aalan`
2. Email `aalan@qutemail.tech` is automatically assigned
3. EmailAccount is auto-created with Zoho Mail configuration
4. Can immediately sync and send emails using QuTeMail account

### For Other Users
1. Register with any username (e.g., `john`)
2. Email `john@qutemail.tech` is assigned
3. No SMTP/IMAP configuration is created
4. Attempting to sync/compose shows: *"QuTeMail accounts are not yet configured for email services. Only aalan@qutemail.tech is currently operational. Please connect external email accounts (Gmail, Outlook, etc.) to send and receive emails."*
5. Users must connect external email accounts (Gmail, Outlook, Yahoo, Custom IMAP) to use the system

## Testing Checklist

- [ ] Register as `aalan` - should auto-configure EmailAccount
- [ ] Register as another user - should NOT auto-configure
- [ ] Login as `aalan` - should see aalan@qutemail.tech in dashboard
- [ ] Click on aalan@qutemail.tech account - should open mailbox
- [ ] Sync emails - should connect to Zoho Mail IMAP
- [ ] Compose and send email with QKD+AES encryption
- [ ] Login as other user - should see their @qutemail.tech email
- [ ] Click on their QuTeMail account - should show "not configured" alert when trying to sync/compose
- [ ] Connect external Gmail/Outlook account - should work normally

## Migration Status

| Component | Status | Notes |
|-----------|--------|-------|
| Backend Domain Change | ✅ Complete | All models updated to qutemail.tech |
| Backend Auto-Config | ✅ Complete | aalan user auto-configures on registration |
| Frontend Domain Change | ✅ Complete | Auth.tsx updated with new domain |
| Frontend Account Checks | ✅ Complete | Mailbox prevents actions on unconfigured accounts |
| Zoho Mail Integration | ✅ Complete | IMAP/SMTP settings configured |
| Testing | ⏳ Pending | Awaiting user testing |

## Next Steps

1. Test registration flow with `aalan` username
2. Test registration flow with other usernames
3. Verify Zoho Mail SMTP/IMAP connections work for aalan
4. Test QKD+AES encryption with aalan@qutemail.tech
5. Verify alerts show for unconfigured accounts
6. Document any issues or edge cases discovered during testing
