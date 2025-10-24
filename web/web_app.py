#!/usr/bin/env python3
"""
Web Application Module for Active Portal
Handles all Flask routes and web interface logic
"""

import logging
from flask import Flask, render_template, request, redirect, url_for

# Configure logging
logger = logging.getLogger(__name__)

class WebApp:
    def __init__(self, host='192.168.4.1', port=5000):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes for the captive portal"""
        
        @self.app.route('/')
        def index():
            """Main portal page - registration form"""
            return render_template('portal.html')
            
        @self.app.route('/welcome')
        def welcome():
            """Welcome page with service information"""
            return render_template('welcome.html')
            
        @self.app.route('/success')
        def success():
            """Success page after form submission"""
            return render_template('success.html')
            
        @self.app.route('/submit', methods=['POST'])
        def submit():
            """Handle form submission"""
            name = request.form.get('name', '')
            email = request.form.get('email', '')
            logger.info(f"Portal submission - Name: {name}, Email: {email}")
            return redirect(url_for('success'))
        
        # Handle HTTPS traffic (for apps)
        @self.app.route('/<path:path>', methods=['GET', 'POST'])
        def catch_all(path):
            """Catch-all route for any other requests"""
            # If it's a POST request, it might be an app trying to connect
            if request.method == 'POST':
                return render_template('portal.html')
            # For GET requests, show portal
            return render_template('portal.html')
        
        # Handle root domain requests
        @self.app.route('/generate_204')
        def generate_204():
            """Android connectivity check endpoint"""
            return render_template('portal.html')
        
        # Handle Android captive portal detection
        @self.app.route('/hotspot-detect.html')
        def hotspot_detect():
            """Android captive portal detection endpoint"""
            return render_template('portal.html')
        
        # Handle iOS captive portal detection
        @self.app.route('/library/test/success.html')
        def ios_detect():
            """iOS captive portal detection endpoint"""
            return render_template('portal.html')
        
        # Additional captive portal detection endpoints
        @self.app.route('/ncsi.txt')
        def ncsi_detect():
            """Windows Network Connectivity Status Indicator"""
            return "Microsoft NCSI", 200
        
        @self.app.route('/connectivity-check.html')
        def connectivity_check():
            """Generic connectivity check"""
            return render_template('portal.html')
        
        @self.app.route('/redirect')
        def redirect_detect():
            """Generic redirect endpoint"""
            return render_template('portal.html')
        
        @self.app.route('/success.txt')
        def success_txt():
            """Text-based success endpoint"""
            return "Success", 200
        
        @self.app.route('/canonical.html')
        def canonical_detect():
            """Canonical captive portal detection"""
            return render_template('portal.html')
        
        # Handle Windows 10/11 captive portal detection
        @self.app.route('/windows/redirect')
        def windows_redirect():
            """Windows captive portal redirect"""
            return render_template('portal.html')
        
        # Handle macOS captive portal detection
        @self.app.route('/hotspot.html')
        def macos_detect():
            """macOS captive portal detection"""
            return render_template('portal.html')
        
        # Handle various mobile device detection
        @self.app.route('/mobile/redirect')
        def mobile_redirect():
            """Mobile device redirect"""
            return render_template('portal.html')
        
        # Handle captive portal API endpoints
        @self.app.route('/api/v1/connectivity')
        def api_connectivity():
            """API connectivity check"""
            return {"status": "captive_portal", "redirect_url": "/"}, 200
        
        @self.app.route('/api/v1/status')
        def api_status():
            """API status check"""
            return {"connected": False, "portal_required": True}, 200
    
    def run(self, debug=False):
        """Start the Flask web server"""
        try:
            logger.info(f"Starting Flask web server on {self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port, debug=debug)
        except Exception as e:
            logger.error(f"Failed to start Flask web server: {e}")
            raise

# Standalone web server for testing
if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Parse command line arguments
    host = '192.168.4.1'
    port = 5000
    debug = False
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    if len(sys.argv) > 3 and sys.argv[3].lower() == 'debug':
        debug = True
    
    # Create and run web app
    web_app = WebApp(host, port)
    web_app.run(debug=debug)
