# Environment Configuration Guide

## Overview

This project uses **environment variables** for all configuration and secrets management. This approach follows industry best practices for:

- 🔒 **Security** - API keys never in source code
- 🔄 **Flexibility** - Different configs for dev/staging/prod
- 📦 **Portability** - Easy deployment across environments
- 👥 **Collaboration** - Team members use their own credentials

---

## Quick Start

### 1. Copy the example file
```bash
cp .env.example .env
```

### 2. Fill in your API keys
```bash
# Edit .env with your favorite editor
nano .env

# Or on Windows
notepad .env
```

### 3. Get API keys

#### AISStream (Required)
- Sign up at: https://aisstream.io/
- Free tier: 50 vessels per key
- Recommended: Get 6+ keys for 900 vessel tracking

#### Datalastic (Optional)
- Sign up at: https://www.datalastic.com/
- Only needed for Atlantic Ocean coverage
- REST API for mid-ocean vessel positions

#### Google Gemini (Optional)
- Get API key at: https://makersuite.google.com/app/apikey
- Only needed for AI company profiling
- Free tier available

### 4. Generate Flask secret key
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Copy output to FLASK_SECRET_KEY in .env
```

---

## File Structure

```
.env.example          # Template (committed to git)
.env                  # Your actual config (NEVER commit)
config/env_loader.py  # Config loader with validation
.gitignore            # Ensures .env is never committed
```

---

## Security Best Practices

### ✅ Do:

1. **Copy `.env.example` to `.env`**
   ```bash
   cp .env.example .env
   ```

2. **Keep secrets in `.env` only**
   - Never hardcode API keys in source code
   - Use environment variables everywhere

3. **Verify `.env` is gitignored**
   ```bash
   git status
   # .env should NOT appear
   ```

4. **Use different `.env` files per environment**
   ```
   .env.development    # Local dev
   .env.staging        # Staging server
   .env.production     # Production server
   ```

5. **Rotate API keys periodically**
   - Update `.env` with new keys
   - Restart services

### ❌ Don't:

1. **Never commit `.env` to git**
   ```bash
   # BAD - This exposes all your secrets!
   git add .env
   ```

2. **Never hardcode secrets**
   ```python
   # BAD
   API_KEY = "sk-1234567890abcdef"
   
   # GOOD
   API_KEY = os.getenv('AIS_API_KEY_1')
   ```

3. **Never share `.env` via email/chat**
   - Use secure password managers
   - Use environment variable management tools

4. **Never log sensitive values**
   ```python
   # BAD
   print(f"Using API key: {api_key}")
   
   # GOOD
   print(f"Using API key: {api_key[:10]}...")
   ```

---

## Configuration Loader

### Basic Usage

```python
from config.env_loader import config

# Access configuration
api_keys = config.ais_api_keys
db_path = config.db_path
log_level = config.log_level

# Validate configuration
errors = config.validate()
if errors:
    for error in errors:
        print(f"Error: {error}")
    sys.exit(1)

# Print configuration (masks sensitive values)
config.print_config()
```

### Available Properties

```python
# API Keys
config.ais_api_keys          # List[str]
config.datalastic_api_key    # Optional[str]
config.gemini_api_key        # Optional[str]

# Database
config.db_path               # str
config.db_timeout            # int
config.db_wal_mode           # bool

# Logging
config.log_level             # str (DEBUG, INFO, WARNING, ERROR, CRITICAL)
config.log_to_file           # bool
config.log_file_path         # str

# Flask
config.flask_host            # str
config.flask_port            # int
config.flask_env             # str (development, production)
config.flask_debug           # bool
config.flask_secret_key      # str

# WebSocket
config.aisstream_ws_url      # str
config.ws_reconnect_delay    # int
config.ws_max_reconnect_delay # int

# Vessel Filtering
config.min_vessel_length     # int
config.min_ship_type         # int
config.max_ship_type         # int

# Geographic Coverage
config.bbox_southwest        # tuple[float, float]
config.bbox_northeast        # tuple[float, float]

# Feature Flags
config.enable_ai_profiling   # bool
config.enable_web_scraping   # bool
config.enable_atlantic_tracker # bool
```

### Validation

```python
from config.env_loader import Config

cfg = Config()
errors = cfg.validate()

if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("✓ Configuration valid")
```

---

## Example Configurations

### Development (`.env`)
```bash
# Local development with debug mode
AIS_API_KEY_1=your_dev_key_here
DB_PATH=data/vessel_static_data.db
LOG_LEVEL=DEBUG
FLASK_ENV=development
FLASK_DEBUG=true
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
ENABLE_AI_PROFILING=false
TEST_MODE=true
```

### Production (`.env.production`)
```bash
# Production server with optimizations
AIS_API_KEY_1=your_prod_key_1
AIS_API_KEY_2=your_prod_key_2
AIS_API_KEY_3=your_prod_key_3
AIS_API_KEY_4=your_prod_key_4
AIS_API_KEY_5=your_prod_key_5
AIS_API_KEY_6=your_prod_key_6
DATALASTIC_API_KEY=your_datalastic_key
DB_PATH=/var/www/apihub/data/vessel_static_data.db
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE_PATH=/var/www/apihub/logs/tracker.log
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_SECRET_KEY=generated_secret_key_here
ENABLE_AI_PROFILING=true
ENABLE_ATLANTIC_TRACKER=true
TEST_MODE=false
```

### Testing (`.env.test`)
```bash
# Testing environment with mocks
AIS_API_KEY_1=test_key
DB_PATH=:memory:  # In-memory SQLite
LOG_LEVEL=DEBUG
FLASK_ENV=development
FLASK_DEBUG=true
TEST_MODE=true
TEST_MAX_VESSELS=10
MOCK_API_RESPONSES=true
```

---

## Docker Integration

### Dockerfile
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Copy requirements and install
COPY config/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Environment variables from .env file
ENV PYTHONUNBUFFERED=1

# Use env_loader to load configuration
CMD ["python", "src/services/web_tracker.py"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  ais-tracker:
    build: .
    ports:
      - "${FLASK_PORT}:5000"
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    restart: unless-stopped
```

### Run with Docker
```bash
# Load .env and run
docker-compose up -d

# Or pass env file explicitly
docker run --env-file .env ais-tracker
```

---

## VPS Deployment

### Setup on VPS

```bash
# 1. Clone repository
git clone https://github.com/yourusername/ais-vessel-tracker.git
cd ais-vessel-tracker

# 2. Create .env file
cp .env.example .env
nano .env  # Fill in your production keys

# 3. Set proper permissions (restrict access to .env)
chmod 600 .env

# 4. Load in systemd service
cat > /etc/systemd/system/ais-tracker.service << EOF
[Unit]
Description=AIS Vessel Tracker
After=network.target

[Service]
Type=simple
User=erik
WorkingDirectory=/var/www/apihub
EnvironmentFile=/var/www/apihub/.env
ExecStart=/var/www/apihub/venv/bin/python src/services/web_tracker.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 5. Start service
sudo systemctl daemon-reload
sudo systemctl enable ais-tracker
sudo systemctl start ais-tracker
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: pip install -r config/requirements.txt
      
      - name: Create test .env
        run: |
          echo "AIS_API_KEY_1=${{ secrets.AIS_API_KEY_1 }}" > .env
          echo "DB_PATH=:memory:" >> .env
          echo "LOG_LEVEL=DEBUG" >> .env
          echo "TEST_MODE=true" >> .env
      
      - name: Run tests
        run: pytest
```

**GitHub Secrets:**
1. Go to: Settings → Secrets → Actions
2. Add secrets:
   - `AIS_API_KEY_1`
   - `DATALASTIC_API_KEY`
   - `GOOGLE_GEMINI_API_KEY`

---

## Troubleshooting

### Problem: "No AISStream API keys found"

**Solution:**
```bash
# Check if .env exists
ls -la .env

# Check if keys are set
grep AIS_API_KEY .env

# Verify format (no spaces around =)
# GOOD: AIS_API_KEY_1=your_key
# BAD:  AIS_API_KEY_1 = your_key
```

### Problem: ".env file not loading"

**Solution:**
```python
# Verify path
from pathlib import Path
from dotenv import load_dotenv

env_path = Path('.env')
print(f"Loading from: {env_path.absolute()}")
print(f"Exists: {env_path.exists()}")

load_dotenv(env_path, verbose=True)  # Shows loading details
```

### Problem: "Configuration validation errors"

**Solution:**
```python
from config.env_loader import Config

cfg = Config()
errors = cfg.validate()
for error in errors:
    print(f"Fix: {error}")
```

### Problem: "Flask secret key not set"

**Solution:**
```bash
# Generate new key
python -c "import secrets; print(secrets.token_hex(32))"

# Add to .env
echo "FLASK_SECRET_KEY=<generated_key>" >> .env
```

---

## Migration from Old System

### Old System (api.txt files)
```
api.txt
config/gemini_api_key.txt
config/datalastic_api_key.txt
```

### New System (.env file)
```bash
# Migrate API keys
AIS_API_KEY_1=$(head -n 1 api.txt)
AIS_API_KEY_2=$(sed -n '2p' api.txt)
GEMINI_KEY=$(cat config/gemini_api_key.txt)
DATALASTIC_KEY=$(cat config/datalastic_api_key.txt)

# Create .env
cat > .env << EOF
AIS_API_KEY_1=$AIS_API_KEY_1
AIS_API_KEY_2=$AIS_API_KEY_2
GOOGLE_GEMINI_API_KEY=$GEMINI_KEY
DATALASTIC_API_KEY=$DATALASTIC_KEY
# ... other config
EOF
```

### Update Code
```python
# OLD
with open('api.txt') as f:
    api_key = f.read().strip()

# NEW
from config.env_loader import config
api_key = config.ais_api_keys[0]
```

---

## Testing Configuration

### Test script
```bash
# Test configuration loading
python config/env_loader.py

# Output:
# ✓ Configuration valid
# ==========================================
# Current Configuration
# ==========================================
# API Keys:
#   AISStream keys: 6 configured
#   Datalastic key: ✓ Set
#   Gemini key: ✓ Set
# ...
```

### Verification checklist

- [ ] `.env` file exists and is readable
- [ ] `.env` is in `.gitignore`
- [ ] At least 1 AISStream API key configured
- [ ] Flask secret key is set
- [ ] Configuration validation passes
- [ ] All services start without errors

---

## Summary

**Before:** API keys in text files, hardcoded paths, no validation  
**After:** Centralized `.env` config, type-safe access, automatic validation

**Benefits:**
- ✅ Secure secrets management
- ✅ Environment-specific configs
- ✅ Type-safe configuration access
- ✅ Automatic validation
- ✅ Industry best practices

**Files:**
- `.env.example` - Template (commit this)
- `.env` - Your config (never commit)
- `config/env_loader.py` - Loader with validation
- `.gitignore` - Protects `.env`

🎯 **This demonstrates professional configuration management and security awareness.**
