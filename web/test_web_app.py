#!/usr/bin/env python3
"""
Test script for the separated web application
This allows testing the Flask app independently
"""

import sys
import time
import threading
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.web_app import WebApp

def test_web_app():
    """Test the web application independently"""
    print("🧪 Testing Web Application Module...")
    
    try:
        # Create web app instance
        web_app = WebApp(host='127.0.0.1', port=5001)
        
        # Start web app in a separate thread
        web_thread = threading.Thread(target=web_app.run, kwargs={'debug': False})
        web_thread.daemon = True
        web_thread.start()
        
        # Give it time to start
        time.sleep(2)
        
        print("✅ Web application started successfully")
        print("🌐 Web app running on http://127.0.0.1:5001")
        print("📱 Test endpoints:")
        print("   - Main portal: http://127.0.0.1:5001/")
        print("   - Welcome page: http://127.0.0.1:5001/welcome")
        print("   - Success page: http://127.0.0.1:5001/success")
        print("   - Android detection: http://127.0.0.1:5001/hotspot-detect.html")
        print("   - iOS detection: http://127.0.0.1:5001/library/test/success.html")
        print("\nPress Ctrl+C to stop the test server")
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping test server...")
            
    except Exception as e:
        print(f"❌ Error testing web application: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Active Portal - Web Application Test")
    print("=" * 50)
    
    success = test_web_app()
    
    if success:
        print("✅ Web application test completed successfully")
    else:
        print("❌ Web application test failed")
        sys.exit(1)
