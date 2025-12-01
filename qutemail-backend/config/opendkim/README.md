# OpenDKIM Configuration for QtEmail

## Overview

OpenDKIM is used to sign all outgoing emails with DKIM (DomainKeys Identified Mail) signatures, which helps prevent email spoofing and improves deliverability.

## Key Generation

To generate DKIM keys for your domain:

```bash
# Create keys directory
mkdir -p config/opendkim/keys

# Generate private/public key pair (2048-bit RSA)
opendkim-genkey -b 2048 -d qutemail.local -D config/opendkim/keys -s default -v

# This creates two files:
# - default.private (private key - keep secret!)
# - default.txt (public key - publish in DNS)
```

## DNS Configuration

After generating keys, you need to publish the public key in your DNS:

1. Open `config/opendkim/keys/default.txt`
2. Copy the TXT record value
3. Create a DNS TXT record:
   - Name: `default._domainkey.qutemail.local`
   - Type: TXT
   - Value: The `p=...` value from default.txt

Example DNS record:
```
default._domainkey.qutemail.local. IN TXT "v=DKIM1; k=rsa; p=MIIBIjANBgkqh..."
```

## Verification

To verify DKIM signing is working:

1. Send an email to a test address
2. Check email headers for `DKIM-Signature:` header
3. Use online tools like mail-tester.com to verify DKIM

## Files

- `opendkim.conf` - Main configuration file
- `KeyTable` - Maps key names to key files
- `SigningTable` - Maps email addresses to keys
- `TrustedHosts` - Hosts allowed to relay without DKIM verification
- `keys/default.private` - Private signing key (keep secure!)
- `keys/default.txt` - Public key for DNS publication

## Security Notes

- **NEVER** commit private keys to version control
- Set proper permissions on key files (chmod 600)
- Rotate keys periodically (every 6-12 months)
- Use at least 2048-bit RSA keys
