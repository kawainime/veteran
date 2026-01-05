# 🎖️ Veterans Verification CLI

A powerful CLI tool for ChatGPT Plus US Veterans verification via SheerID.

## ✨ Features

- 🎨 **Rich Terminal UI** - Beautiful colored output with progress indicators
- 🔄 **Auto-retry** - Automatic retry with exponential backoff
- 📧 **Email Integration** - IMAP support for automatic email token retrieval
- 🌐 **Proxy Support** - HTTP/SOCKS proxy support with rotation
- 📊 **Batch Processing** - Process multiple veterans from file
- 🔐 **Deduplication** - Track used records to avoid duplicates
- ⚡ **Async Ready** - Optimized for speed
- 🛡️ **Cloudflare Bypass** - Built-in cloudscraper support
- 🕷️ **Data Scraper** - Built-in scraper for VA.gov Veterans Legacy Memorial

## 📋 Requirements

- Python 3.8+
- ChatGPT Plus account with veterans claim access
- Email account with IMAP access (aaPanel mail server, Gmail, etc.)

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy example config
cp config.example.json config.json

# Edit with your credentials
nano config.json
```

### 3. Add veteran data

```bash
# Copy example data
cp data.example.txt data.txt

# Add your veteran records (one per line)
# Format: FirstName|LastName|Branch|BirthDate|DischargeDate
nano data.txt
```

### 4. Run

```bash
# Basic usage
python main.py

# With proxy
python main.py --proxy http://user:pass@host:port

# Skip deduplication
python main.py --no-dedup

# Verbose mode
python main.py -v

# Single record mode
python main.py --single "John|Smith|Army|1990-01-15|2024-06-01"
```

## ⚙️ Configuration

### config.json

```json
{
    "accessToken": "YOUR_CHATGPT_ACCESS_TOKEN",
    "programId": "690415d58971e73ca187d8c9",
    "email": {
        "imap_server": "mail.yourdomain.com",
        "imap_port": 993,
        "email_address": "verify@yourdomain.com",
        "email_password": "your_email_password",
        "use_ssl": true
    },
    "settings": {
        "max_retries": 3,
        "retry_delay": 2,
        "email_poll_interval": 5,
        "email_max_attempts": 24,
        "request_timeout": 30
    }
}
```

### Getting Access Token

1. Login to https://chatgpt.com
2. Open DevTools (F12) → Network tab
3. Visit https://chatgpt.com/api/auth/session
4. Copy the `accessToken` value

### aaPanel Mail Server Setup

1. Install Mail Server di aaPanel
2. Buat email account (misal: verify@yourdomain.com)
3. Setting di config.json:
   ```json
   "email": {
       "imap_server": "mail.yourdomain.com",
       "imap_port": 993,
       "email_address": "verify@yourdomain.com",
       "email_password": "password_email_kamu",
       "use_ssl": true
   }
   ```

## 📝 Data Format

Each line in `data.txt`:

```
FirstName|LastName|Branch|BirthDate|DischargeDate
```

### Supported Branches

- Army
- Navy
- Air Force
- Marine Corps
- Coast Guard
- Space Force
- Army National Guard
- Army Reserve
- Air National Guard
- Air Force Reserve
- Navy Reserve
- Marine Corps Reserve
- Coast Guard Reserve

### Example

```
John|Smith|Army|1985-03-15|2024-01-15
Jane|Doe|Navy|1990-07-22|2024-06-01
Mike|Johnson|Air Force|1988-11-30|2023-12-20
```

## 🕷️ Data Scraper

Scrape veteran data dari VA.gov Veterans Legacy Memorial:

```bash
# Scrape 100 records
python scraper.py --count 100

# Output ke file tertentu
python scraper.py --count 500 --output veterans.txt

# Output format JSON
python scraper.py --count 100 --format json
```

## 🌐 Proxy Configuration

### proxy.txt format

```
# Simple format
host:port

# With authentication
host:port:username:password

# Full URL format
http://user:pass@host:port
socks5://user:pass@host:port
```

## 📊 CLI Options

| Option | Description |
|--------|-------------|
| `--proxy URL` | Use specific proxy |
| `--proxy-file FILE` | Load proxies from file |
| `--no-dedup` | Disable deduplication |
| `--single "DATA"` | Verify single record |
| `-v, --verbose` | Verbose output |
| `--dry-run` | Test without submitting |
| `--max-retries N` | Max retry attempts (default: 3) |
| `--delay N` | Delay between records in seconds |

## 🔧 Troubleshooting

### 403 Forbidden

Token expired. Get a new one from ChatGPT.

### Email not received

- Check spam folder
- Verify IMAP settings
- Ensure email password is correct
- Check mail server logs di aaPanel

### IMAP Login Failed

- Pastikan IMAP enabled di mail server
- Cek port 993 (SSL) atau 143 (non-SSL)
- Verifikasi email dan password benar

### Rate limited

- Use proxies
- Increase delay between requests

## 📄 License

MIT License
