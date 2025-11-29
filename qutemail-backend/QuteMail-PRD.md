# **PRODUCT REQUIREMENTS DOCUMENT (PRD)**

## **Product Name: QuteMail – Quantum-Secure Email Client**

---

# **1. Product Overview**

QuteMail is a **quantum-secure email client platform** that allows users to create an email account (e.g., `user@qutemail.com`) and send/receive emails with **post-quantum security**. QuteMail integrates with:

* **QKD (Quantum Key Distribution)** for unbreakable encryption
* **ETSI GS QKD 014 Key Management API** for standardized key delivery
* **Quantum-Aided AES** for scalable encryption
* **SMTP/IMAP/POP3** servers for traditional email delivery

QuteMail looks and works like Gmail or Outlook — but all emails are encrypted on the application level **using quantum-secure keys**, and remain encrypted at rest in the database.

---

# **2. Problem Statement**

Today, over **300 billion emails** are sent daily, carrying private, financial, and business-critical information.
Current encryption relies on algorithms (RSA/ECC) that will be **breakable by quantum computers** in the near future.

There is no widely-usable email client today that supports:

* **Quantum-safe key generation**
* **Secure end-to-end encryption using QKD keys**
* **Backward compatibility with SMTP/IMAP email ecosystem**

QuteMail solves this.

---

# **3. Product Goals**

### **Primary Goals**

1. Allow users to create `@qutemail.com` email accounts.
2. Provide a full email client experience (send, receive, delete, inbox).
3. Integrate **QKD keys** for encrypting/decrypting emails.
4. Store all emails encrypted in the database.
5. Deliver emails through standard SMTP/IMAP servers.

### **Secondary Goals**

* Provide a “Quantum Secured” certificate per email.
* Support OTP (One-Time Pad) mode for very high-security messages.
* Provide normal email mode (non-QKD) if needed.
* Enable extensibility to future secure apps (chat, voice, etc.).

---

# **4. Non-Goals**

* Implementing physical QKD devices (handled by KM infrastructure).
* Providing cloud-based email hosting for external domains (e.g., gmail.com).
* Performing decryption on SMTP/IMAP layer.
* Replacing SMTP/IMAP standards.

---

# **5. User Personas**

### **1. Security-Focused Users**

* Researchers, enterprises, banks, government users
* Want quantum-safe communication

### **2. General Users**

* Want a regular email client but more secure

### **3. Developers**

* Will integrate QuteMail KM APIs

---

# **6. Core Features**

### **1. Account Creation**

* Users create `username@qutemail.com`
* Stored in Django Auth DB

### **2. Compose & Send Email**

* Compose subject, body, attachments
* Option to enable QKD encryption
* MIME formatting

### **3. QKD Key Integration**

* Request keys from ETSI QKD 014 API
* Quantum-Aided AES encryption (HKDF → AES-256-GCM)
* OTP mode for small messages
* Embed QKD metadata in headers:

  * `X-QKD-Key-ID`
  * `X-QKD-Algorithm`
  * `X-QKD-Secure: True`

### **4. SMTP Delivery**

* Send encrypted emails via Postfix SMTP server
* MX records for `qutemail.com`

### **5. Receive Email**

* Receive using Inbound SMTP
* Store ciphertext in encrypted database
* Decrypt on client request

### **6. IMAP/POP3 Retrieval**

* Fetch emails securely
* Decrypt using QKD keys

### **7. Encrypted Storage**

* AES-GCM encrypted body
* Attachments stored as encrypted blobs
* Metadata minimally stored

---

# **7. Functional Requirements**

## **7.1 User Management**

| Requirement | Details                                         |
| ----------- | ----------------------------------------------- |
| FR-1        | Users can register with `username@qutemail.com` |
| FR-2        | Support login with JWT tokens                   |
| FR-3        | Reset password flow                             |
| FR-4        | Create mailbox folders for new user             |

## **7.2 Compose & Send Email**

| Requirement | Details                                                |
| ----------- | ------------------------------------------------------ |
| FR-5        | Compose email with subject/body/attachments            |
| FR-6        | Choose encryption mode: Quantum-Aided AES, OTP, Normal |
| FR-7        | System requests QKD key from ETSI KM                   |
| FR-8        | System encrypts MIME payload                           |
| FR-9        | Store encrypted mail in database                       |
| FR-10       | Send via SMTP outbound server                          |

## **7.3 Receive Email**

| Requirement | Details                                  |
| ----------- | ---------------------------------------- |
| FR-11       | Receive via SMTP inbound                 |
| FR-12       | Store ciphertext in storage              |
| FR-13       | Upon user request, decrypt using QKD key |
| FR-14       | Expose inbox API with minimal metadata   |

## **7.4 QKD Integration**

| Requirement | Details                                    |
| ----------- | ------------------------------------------ |
| FR-15       | Connect to ETSI QKD 014 KM                 |
| FR-16       | Request, poll, and confirm key consumption |
| FR-17       | Validate key integrity                     |
| FR-18       | Display “Quantum Secured” badge            |

## **7.5 IMAP/POP3**

| Requirement | Details                             |
| ----------- | ----------------------------------- |
| FR-19       | Provide IMAP service for inbox sync |
| FR-20       | Allow POP3 for download mode        |

---

# **8. Technical Architecture**

### **Backend Framework**

* Django + Django REST Framework

### **Services**

* **Auth Service**
* **Mail Composer Service**
* **QKD Encryption Service**
* **SMTP Outbound**
* **SMTP Inbound**
* **IMAP/POP3 Mail Retrieval**
* **KM Connector**
* **Encrypted Storage Service**

---

# **9. System Flow (Step-by-Step)**

## **Flow A — Signup**

1. User → Register
2. Django creates account `@qutemail.com`
3. Mailbox auto-initialized

## **Flow B — Sending Email**

1. User → Compose email
2. Backend calls KM: `/key-request`
3. KM returns `key_id` + `key_bits`
4. Backend uses Quantum-Aided AES to encrypt
5. Email stored encrypted in DB
6. Encrypted MIME sent via SMTP

## **Flow C — Receiving Email**

1. SMTP server receives encrypted mail
2. Mail stored in ciphertext form
3. User fetches via IMAP/REST
4. Backend requests same key from KM
5. Backend decrypts and returns plaintext

---

# **10. APIs**

### **Authentication**

* `POST /auth/signup/`
* `POST /auth/login/`

### **Mail**

* `POST /mail/compose/`
* `GET /mail/inbox/`
* `GET /mail/{id}/decrypt/`

### **QKD**

* `POST /qkd/request_key/`
* `POST /qkd/confirm/`

---

# **11. Milestones**

| Week   | Deliverable                        |
| ------ | ---------------------------------- |
| Week 1 | Django project, Auth, signup/login |
| Week 2 | Mail models, Compose API           |
| Week 3 | QKD simulator + ETSI KM connector  |
| Week 4 | Quantum-Aided AES encryption       |
| Week 5 | SMTP Outbound + MX setup           |
| Week 6 | SMTP Inbound + Encrypted storage   |
| Week 7 | IMAP server integration            |
| Week 8 | End-to-end testing + Demo          |

---

# **12. KPIs (Success Metrics)**

| KPI                     | Target      |
| ----------------------- | ----------- |
| Encryption success rate | 99%         |
| Email delivery success  | 99.9%       |
| Key integrity failures  | < 0.1%      |
| SMTP latency            | < 2 seconds |
| User onboarding time    | < 30 sec    |

---

# **13. Risks & Mitigations**

| Risk                | Mitigation                  |
| ------------------- | --------------------------- |
| QKD key shortage    | Use hybrid PQC fallback     |
| SMTP deliverability | SPF/DKIM/DMARC setup        |
| Database breach     | Emails always encrypted     |
| KM latency          | Key caching + batching      |
| High storage usage  | Attachments in object store |

---

# **14. Future Enhancements**

* Secure chat using QKD
* Secure P2P video calling
* QKD-based multi-party sessions
* Hardware security module integration

