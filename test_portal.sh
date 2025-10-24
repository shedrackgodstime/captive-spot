#!/bin/bash

# Test script to verify captive portal is working
echo "🧪 Testing Captive Portal..."

# Test HTTP redirection
echo "Testing HTTP redirection..."
curl -s -o /dev/null -w "%{http_code}" http://192.168.4.1:5000/ || echo "Failed"

# Test HTTPS redirection  
echo "Testing HTTPS redirection..."
curl -s -k -o /dev/null -w "%{http_code}" https://192.168.4.1:5000/ || echo "Failed"

# Test DNS redirection
echo "Testing DNS redirection..."
nslookup google.com 192.168.4.1 || echo "DNS test failed"

# Test captive portal detection endpoints
echo "Testing Android captive portal detection..."
curl -s -o /dev/null -w "%{http_code}" http://192.168.4.1:5000/hotspot-detect.html || echo "Failed"

echo "Testing iOS captive portal detection..."
curl -s -o /dev/null -w "%{http_code}" http://192.168.4.1:5000/library/test/success.html || echo "Failed"

echo "✅ Portal tests completed"
