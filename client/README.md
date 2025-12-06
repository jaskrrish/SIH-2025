# QuteMail Frontend - React + TypeScript + Vite

Modern email client with quantum-safe encryption featuring React 19, TypeScript, and Tailwind CSS.

## 🎯 Features

- **Multi-Account Support**: Connect Gmail, Outlook, Yahoo
- **4 Security Levels**: Regular, AES-256, QKD+AES, QRNG+PQC
- **Real-time Sync**: Automatic email fetching and decryption
- **Modern UI**: Clean, responsive design with Tailwind CSS
- **Accessibility**: Screen reader support, keyboard navigation
- **JWT Authentication**: Secure token-based auth

## 📁 Project Structure

```
client/
├── src/
│   ├── pages/
│   │   ├── Auth.tsx          # Login/Register page
│   │   ├── Home.tsx          # Account management
│   │   └── Mailbox.tsx       # Email interface with compose
│   ├── components/
│   │   ├── ui/               # Reusable UI components
│   │   └── AccessibilityTools.tsx
│   ├── lib/
│   │   ├── api.ts            # API client (fetch wrapper)
│   │   └── auth.ts           # JWT token management
│   ├── App.tsx               # Main app component
│   └── main.tsx              # Entry point
├── public/                    # Static assets
└── index.html
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- Backend running at `http://127.0.0.1:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

App runs at: `http://localhost:5173`

### Build for Production

```bash
npm run build
npm run preview
```

## 🔑 Environment Variables

Create `.env` file:

```env
VITE_API_URI=http://127.0.0.1:8000/api
```

## 📡 API Integration

### Authentication Flow

```typescript
// Register
await api.register('username', 'Full Name', 'password', 'password')
// Returns: { user, tokens: { access, refresh } }

// Login
await api.login('username', 'password')
// Stores tokens in localStorage

// Get current user
const user = await api.getCurrentUser()
// Uses stored JWT token
```

### Email Operations

```typescript
// Connect Gmail account
await api.connectEmailAccount('gmail', 'email@gmail.com', 'app-password')

// List accounts
const accounts = await api.listEmailAccounts()

// Sync emails (fetch from IMAP)
await api.syncEmails(accountId)

// Send encrypted email
await api.sendEmail(
  accountId,
  ['recipient@gmail.com'],
  'Subject',
  'Body text',
  undefined, // body_html
  'qkd' // security_level
)

// List emails
const emails = await api.listEmails(accountId, limit)
```

## 🎨 UI Components

### Home Page
- Account cards with provider logos
- Connect new account modal
- Account deletion
- Navigation to mailbox

### Mailbox Page
- **Email List**: Inbox view with sender, subject, preview
- **Email Detail**: Full email view
- **Compose Modal**: 
  - To, Subject, Body fields
  - 4 security level cards:
    - Regular (gray, no encryption)
    - Standard AES (blue, AES-256-GCM)
    - QKD+AES (green, quantum keys)
    - QRNG+PQC (purple, disabled/coming soon)
  - Send button with loading state

### Security Level Selector

```tsx
<button onClick={() => setEncryptionMethod('qkd')}>
  <ShieldCheck /> QKD + AES
  <p>BB84 quantum keys</p>
</button>
```

Visual states:
- Selected: Colored background + ring
- Hover: Border color change
- Disabled: Opacity 60% + cursor-not-allowed

## 🔐 Security Implementation

### Token Storage

```typescript
// lib/auth.ts
export const authUtils = {
  setTokens(access: string, refresh: string) {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  },
  
  getAuthHeaders() {
    return {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    }
  },
  
  clearTokens() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }
}
```

### Protected Routes

```typescript
// Check for token on mount
useEffect(() => {
  if (!authUtils.getAccessToken()) {
    navigate('/auth')
  }
}, [])
```

## 🧪 Testing

### Manual Testing Flow

1. **Registration**:
   - Navigate to `/auth`
   - Enter username, name, password
   - Should receive JWT token and redirect to `/home`

2. **Connect Gmail**:
   - Click "Add Account"
   - Select Gmail provider
   - Enter email and app password
   - Should see account card appear

3. **Send Encrypted Email**:
   - Open mailbox
   - Click compose (+)
   - Select QKD+AES security
   - Fill recipient, subject, body
   - Click Send
   - Should show success

4. **Sync & Decrypt**:
   - Click sync icon
   - Should fetch emails
   - Encrypted emails auto-decrypt
   - Plain text should display

## 📦 Dependencies

### Core
- `react`: ^19.0.0
- `react-dom`: ^19.0.0
- `react-router-dom`: ^7.1.1

### UI
- `tailwindcss`: ^3.4.17
- `lucide-react`: ^0.469.0 (icons)
- `clsx`: ^2.1.1
- `tailwind-merge`: ^2.6.0

### Build
- `vite`: ^6.0.3
- `typescript`: ~5.6.2
- `@vitejs/plugin-react`: ^4.3.4

## 🎨 Styling

### Tailwind Configuration

```typescript
// tailwind.config.js
theme: {
  extend: {
    colors: {
      'isro-blue': '#0a4d8f',
    }
  }
}
```

### Custom Classes

```css
/* Gradient backgrounds */
bg-gradient-to-br from-isro-blue to-purple-600

/* Animations */
animate-in fade-in zoom-in duration-200

/* Accessibility */
focus:ring-2 focus:ring-isro-blue
```

## ♿ Accessibility

- **Keyboard Navigation**: Tab through all interactive elements
- **Screen Reader**: Descriptive labels and ARIA attributes
- **High Contrast**: Toggle via AccessibilityTools component
- **Focus Indicators**: Visible focus rings on all inputs

## 🐛 Common Issues

### CORS Errors
**Problem**: `No 'Access-Control-Allow-Origin' header`
**Solution**: Ensure backend has `CORS_ALLOW_ALL_ORIGINS = True` (dev) or configure specific origin

### Token Expired
**Problem**: 401 Unauthorized errors
**Solution**: Re-login to get fresh token (implement refresh token flow)

### Email Not Decrypting
**Problem**: Shows ciphertext instead of plaintext
**Solution**: 
- Check `X-QuteMail-*` headers present
- Verify key_id exists in KM store
- Check recipient matches requester_sae

## 🔧 Development Tips

### Hot Module Replacement
Vite provides instant HMR - changes reflect immediately without full reload

### TypeScript Strict Mode
```typescript
// Enable in tsconfig.json
"strict": true,
"noImplicitAny": true
```

### API Error Handling
```typescript
try {
  await api.sendEmail(...)
} catch (err: any) {
  alert(err.message || 'Failed to send email')
}
```

## 🚀 Build & Deploy

### Production Build
```bash
npm run build
# Output: dist/
```

### Preview Production Build
```bash
npm run preview
# Serves dist/ at http://localhost:4173
```

### Deploy to Netlify/Vercel
1. Connect GitHub repo
2. Set build command: `npm run build`
3. Set publish directory: `dist`
4. Add environment variable: `VITE_API_URI=https://api.example.com`

---

## 📚 Additional Resources

- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
