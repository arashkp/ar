# 🔐 Security Setup Guide

## Quick Setup - API Key Protection

Your app is now protected with API key authentication. Here's how to set it up:

### Step 1: Set Your API Key

**For Local Development:**
1. Create a `.env` file in your project root (if not exists)
2. Add your API key:
   ```env
   API_KEY=your-super-secret-api-key-here
   DATABASE_URL=your-database-url
   ```

**For Deployment (Railway/Render/Fly.io):**
1. Add environment variable in your deployment platform:
   - `API_KEY=your-super-secret-api-key-here`

### Step 2: Access Your Protected App

**Option A: Frontend Login (Recommended)**
1. Start your frontend: `cd frontend && npm run dev`
2. Visit `http://localhost:5173`
3. Enter your API key in the login form
4. Access your dashboard securely

**Option B: Direct API Access**
1. Use any API client (Postman, curl, etc.)
2. Add header: `X-API-Key: your-super-secret-api-key-here`
3. Access endpoints like: `GET /health`

### Step 3: Test the Protection

Try accessing without the API key:
```bash
curl http://localhost:8000/health
# Should return: 401 Unauthorized
```

With API key:
```bash
curl -H "X-API-Key: your-super-secret-api-key-here" http://localhost:8000/health
# Should return: {"status": "ok", "message": "AR Trading API is running"}
```

## 🔧 How It Works

### Backend Protection
- All API endpoints (except `/health`) require the `X-API-Key` header
- The API key is checked against the `API_KEY` environment variable
- Invalid or missing API keys return 401 Unauthorized

### Frontend Protection
- Login form validates API key before allowing access
- API key is stored in localStorage for convenience
- Logout button clears the stored key
- All API requests automatically include the API key

## 🛡️ Security Features

✅ **API Key Protection**: All endpoints require valid API key
✅ **Frontend Login**: User-friendly login interface
✅ **Automatic Headers**: API key automatically added to requests
✅ **Session Persistence**: Login persists until logout
✅ **Secure Storage**: API key stored in browser localStorage

## 🔄 Alternative Authentication Methods

If you want something more secure, here are other options:

### Option 2: Username/Password (Basic Auth)
```python
# In src/utils/auth.py
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status
import secrets

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    username = "admin"
    password = "your-password"
    
    is_username_correct = secrets.compare_digest(credentials.username, username)
    is_password_correct = secrets.compare_digest(credentials.password, password)
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
```

### Option 3: JWT Tokens (Most Secure)
For production use, consider implementing JWT token authentication.

## 🚀 Deployment with Security

When deploying, make sure to:

1. **Set the API_KEY environment variable** in your deployment platform
2. **Use a strong, unique API key** (at least 32 characters)
3. **Never commit your API key** to version control
4. **Consider using environment-specific keys** for dev/prod

## 📝 Example API Key Generation

Generate a secure API key:
```bash
# Option 1: Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Option 2: Using OpenSSL
openssl rand -base64 32

# Option 3: Online generator
# Visit: https://generate-secret.vercel.app/32
```

## 🔍 Testing Your Security

1. **Test without API key**: Should return 401
2. **Test with wrong API key**: Should return 401  
3. **Test with correct API key**: Should work normally
4. **Test frontend login**: Should require valid API key

Your app is now protected! Only users with the correct API key can access your trading dashboard. 🔒 