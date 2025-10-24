#!/bin/bash

# Active Portal Setup Script for Parrot OS
# This script installs all required dependencies

echo "🚀 Setting up Active Portal for Parrot OS..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script as root (use sudo)"
    exit 1
fi

# Update package list
echo "📦 Updating package list..."
apt update

# Install system dependencies
echo "🔧 Installing system dependencies..."
apt install -y hostapd dnsmasq iptables python3-pip

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements.txt

# Make the script executable
echo "🔐 Setting up permissions..."
chmod +x hotspot_portal.py

# Check if WiFi interface exists
echo "📡 Checking for WiFi interface..."
if ip link show | grep -q "wlan"; then
    echo "✅ WiFi interface found"
    ip link show | grep "wlan"
else
    echo "⚠️  No WiFi interface found. Make sure your WiFi adapter is connected."
fi

# Check if hostapd supports AP mode
echo "🔍 Checking hostapd AP mode support..."
if hostapd -h 2>&1 | grep -q "AP"; then
    echo "✅ hostapd supports AP mode"
else
    echo "⚠️  hostapd AP mode support not confirmed"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the hotspot, run:"
echo "sudo python3 hotspot_portal.py"
echo ""
echo "For custom configuration:"
echo "sudo python3 hotspot_portal.py 'MyHotspot' 'mypassword' 'wlan0'"
echo ""
echo "Auto-reconnection improvements included!"
echo "If devices don't auto-reconnect, run:"
echo "python3 fix_device_reconnection.py 'MyHotspot' 'mypassword'"
echo ""
echo "Press Ctrl+C to stop the hotspot when running."




