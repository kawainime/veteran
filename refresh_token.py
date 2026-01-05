#!/usr/bin/env python3
"""
Helper script to get fresh ChatGPT access token.
Run this after logging into ChatGPT in your browser.
"""

import json
import sys
from pathlib import Path

def update_token(new_token: str, config_file: str = "config.json"):
    """Update access token in config file."""
    config_path = Path(config_file)
    
    if not config_path.exists():
        print(f"Error: {config_file} not found")
        sys.exit(1)
    
    with open(config_path) as f:
        config = json.load(f)
    
    old_token = config.get("accessToken", "")
    config["accessToken"] = new_token
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Token updated successfully!")
    print(f"   Old token: {old_token[:30]}... ({len(old_token)} chars)")
    print(f"   New token: {new_token[:30]}... ({len(new_token)} chars)")

def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           ChatGPT Access Token Refresh Helper                    ║
╚══════════════════════════════════════════════════════════════════╝

HOW TO GET YOUR ACCESS TOKEN:

1. Open browser and go to: https://chatgpt.com
2. Make sure you are logged in
3. Open browser DevTools (F12)
4. Go to: Application → Local Storage → https://chatgpt.com
5. Find key that starts with 'accessToken' or go to Console tab
6. In Console, type: copy(JSON.parse(localStorage.getItem('accessToken')).accessToken)
7. Or go to: https://chatgpt.com/api/auth/session and copy the accessToken value

ALTERNATIVE METHOD (Network tab):
1. Go to https://chatgpt.com/veterans-claim
2. Open DevTools → Network tab
3. Click "Verify Eligibility" button  
4. Find request to 'create_verification'
5. Copy the 'authorization' header value (without 'Bearer ')

""")
    
    if len(sys.argv) > 1:
        new_token = sys.argv[1]
    else:
        new_token = input("Paste your new access token here:\n> ").strip()
    
    if not new_token:
        print("Error: No token provided")
        sys.exit(1)
    
    if new_token.startswith("Bearer "):
        new_token = new_token[7:]
    
    if len(new_token) < 100:
        print("Warning: Token seems too short. Are you sure it's correct?")
        confirm = input("Continue anyway? (y/n): ")
        if confirm.lower() != 'y':
            sys.exit(1)
    
    update_token(new_token)
    
    # Test the token
    print("\nTesting token...")
    try:
        import cloudscraper
        session = cloudscraper.create_scraper()
        
        resp = session.post(
            'https://chatgpt.com/backend-api/veterans/create_verification',
            headers={
                'authorization': f'Bearer {new_token}',
                'content-type': 'application/json',
                'origin': 'https://chatgpt.com',
            },
            json={'program_id': '690415d58971e73ca187d8c9'},
            timeout=30
        )
        
        if resp.status_code == 200:
            vid = resp.json().get('verification_id', 'N/A')
            print(f"✅ Token works! Verification ID: {vid}")
            
            # Check verification status
            status_resp = session.get(
                f'https://services.sheerid.com/rest/v2/verification/{vid}',
                timeout=15
            )
            if status_resp.status_code == 200:
                data = status_resp.json()
                step = data.get('currentStep', 'unknown')
                errors = data.get('errorIds', [])
                print(f"   Current step: {step}")
                if errors:
                    print(f"   ⚠️ Errors: {errors}")
                    print("   You may need a new ChatGPT account for fresh verification")
                else:
                    print("   ✅ Verification ID is fresh and ready!")
        elif resp.status_code == 403:
            if '<html>' in resp.text:
                print("❌ Cloudflare blocked the request. Try with a proxy or wait.")
            else:
                print("❌ Token is invalid or expired")
        else:
            print(f"❌ Error: {resp.status_code} - {resp.text[:200]}")
            
    except ImportError:
        print("Note: cloudscraper not installed, skipping token test")
    except Exception as e:
        print(f"Error testing token: {e}")

if __name__ == "__main__":
    main()
