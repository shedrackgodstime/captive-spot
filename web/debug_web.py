#!/usr/bin/env python3
"""
Debug script for the web application
Run this to test the Flask app in debug mode
"""

import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.web_app import WebApp

def main():
    """Run web app in debug mode"""
    print("🐛 Starting Web App in Debug Mode")
    print("=" * 40)
    
    # Create web app with debug settings
    web_app = WebApp(host='127.0.0.1', port=5000)
    
    print("🌐 Web app will be available at: http://127.0.0.1:5000")
    print("🔧 Debug mode enabled - auto-reload on code changes")
    print("📝 Logs will show detailed request information")
    print("\nPress Ctrl+C to stop")
    print("=" * 40)
    
    try:
        web_app.run(debug=True)
    except KeyboardInterrupt:
        print("\n🛑 Debug server stopped")

if __name__ == "__main__":
    main()
