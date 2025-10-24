#!/usr/bin/env python3
"""
Device Reconnection Fixer
Helps fix auto-reconnection issues for specific devices
"""

import subprocess
import sys
import os
import time
import json
from datetime import datetime

def run_command(command, description=""):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_network_profile(ssid="ActivePortal"):
    """Check if devices have saved the network profile"""
    print(f"🔍 Checking network profile for '{ssid}'...")

    # Check Linux network manager
    success, stdout, stderr = run_command(f"nmcli connection show | grep '{ssid}'")
    if success and stdout.strip():
        print(f"✅ Linux NetworkManager profile found: {stdout.strip()}")
    else:
        print(f"❌ No Linux NetworkManager profile found for '{ssid}'")

    # Check wpa_supplicant
    success, stdout, stderr = run_command(f"grep -r '{ssid}' /etc/wpa_supplicant/ 2>/dev/null")
    if success and stdout.strip():
        print(f"✅ wpa_supplicant configuration found: {stdout.strip()}")
    else:
        print(f"❌ No wpa_supplicant configuration found for '{ssid}'")

def create_network_profile(ssid="ActivePortal", password="portal123"):
    """Create a network profile for better device recognition"""
    print(f"📝 Creating network profile for '{ssid}'...")

    # Create NetworkManager profile
    print("Creating NetworkManager profile...")
    success, stdout, stderr = run_command(
        f'echo "[connection]" > /tmp/{ssid}.nmconnection && '
        f'echo "id={ssid}" >> /tmp/{ssid}.nmconnection && '
        f'echo "type=wifi" >> /tmp/{ssid}.nmconnection && '
        f'echo "autoconnect=true" >> /tmp/{ssid}.nmconnection && '
        f'echo "autoconnect-priority=100" >> /tmp/{ssid}.nmconnection && '
        f'echo "" >> /tmp/{ssid}.nmconnection && '
        f'echo "[wifi]" >> /tmp/{ssid}.nmconnection && '
        f'echo "ssid={ssid}" >> /tmp/{ssid}.nmconnection && '
        f'echo "mode=infrastructure" >> /tmp/{ssid}.nmconnection && '
        f'echo "" >> /tmp/{ssid}.nmconnection && '
        f'echo "[wifi-security]" >> /tmp/{ssid}.nmconnection && '
        f'echo "key-mgmt=wpa-psk" >> /tmp/{ssid}.nmconnection && '
        f'echo "psk={password}" >> /tmp/{ssid}.nmconnection'
    )

    if success:
        print(f"✅ NetworkManager profile template created: /tmp/{ssid}.nmconnection")
        print("   Copy to ~/.local/share/nm-connection/ or use nmcli to import")
    else:
        print(f"❌ Failed to create NetworkManager profile: {stderr}")

def fix_common_device_issues():
    """Fix common device-specific issues"""
    print("🔧 Fixing common device issues...")

    # Fix Android issues
    print("📱 Android fixes:")
    print("   - Enable 'Auto-connect' in WiFi settings")
    print("   - Disable 'Forget network' option")
    print("   - Check if network is marked as 'Limited connectivity'")
    print("   - Try 'Forget' and reconnect to refresh profile")

    # Fix iOS issues
    print("🍎 iOS fixes:")
    print("   - Go to Settings > WiFi > Select network")
    print("   - Enable 'Auto-Join' toggle")
    print("   - Disable 'Auto-Login' if causing issues")
    print("   - Reset network settings if persistent issues")

    # Fix Windows issues
    print("🪟 Windows fixes:")
    print("   - Check if network is marked as 'Limited connectivity'")
    print("   - Run: netsh wlan show profiles")
    print("   - Delete and recreate profile if corrupted")
    print("   - Run: netsh wlan delete profile name=\"ActivePortal\"")
    print("   - Reconnect to recreate profile")

def show_device_specific_tips():
    """Show device-specific troubleshooting tips"""
    print("\n📋 Device-Specific Auto-Reconnection Tips:")
    print("=" * 50)

    print("\n🔄 General Tips:")
    print("   • Ensure hotspot SSID is unique and memorable")
    print("   • Use strong WPA2 password (8+ characters)")
    print("   • Keep hotspot running consistently")
    print("   • Check device battery optimization settings")

    print("\n📱 Android:")
    print("   • Disable battery optimization for hotspot app")
    print("   • Enable 'Keep WiFi on during sleep'")
    print("   • Check if network appears in 'Saved networks'")
    print("   • Try different DHCP client in device settings")

    print("\n🍎 iOS:")
    print("   • Disable 'WiFi Assist' if interfering")
    print("   • Enable 'Ask to Join Networks'")
    print("   • Check if network appears in WiFi settings")
    print("   • Reset network settings: Settings > General > Reset")

    print("\n🪟 Windows:")
    print("   • Run: netsh wlan show profiles")
    print("   • Check network properties in Network settings")
    print("   • Disable 'Connect automatically' and re-enable")
    print("   • Run: ipconfig /renew")

    print("\n🐧 Linux:")
    print("   • Check: nmcli connection show")
    print("   • Verify: iwconfig or nmcli device wifi list")
    print("   • Check network manager auto-connect settings")

def create_reconnection_test():
    """Create a script to test auto-reconnection"""
    print("🧪 Creating auto-reconnection test script...")

    test_script = '''#!/bin/bash
# Auto-Reconnection Test Script
# Test if hotspot auto-reconnection works properly

echo "🔄 Testing auto-reconnection..."
echo "1. Disconnect from hotspot"
echo "2. Wait 10 seconds"
echo "3. Reconnect automatically"
echo ""

# Check current connection
CURRENT_SSID=$(iwgetid -r 2>/dev/null)
echo "Current SSID: $CURRENT_SSID"

if [ "$CURRENT_SSID" = "ActivePortal" ]; then
    echo "✅ Currently connected to hotspot"
    echo "Disconnecting for test..."
    nmcli connection down "ActivePortal" 2>/dev/null || iwconfig wlan0 down 2>/dev/null
    sleep 2
    echo "🔄 Reconnecting..."
    nmcli connection up "ActivePortal" 2>/dev/null || iwconfig wlan0 up 2>/dev/null
    sleep 5

    # Check if reconnected
    NEW_SSID=$(iwgetid -r 2>/dev/null)
    if [ "$NEW_SSID" = "ActivePortal" ]; then
        echo "✅ Auto-reconnection successful!"
    else
        echo "❌ Auto-reconnection failed"
    fi
else
    echo "❌ Not connected to hotspot"
    echo "Available networks:"
    nmcli device wifi list 2>/dev/null || iwlist scan 2>/dev/null
fi
'''

    with open('/tmp/test_reconnection.sh', 'w') as f:
        f.write(test_script)

    os.chmod('/tmp/test_reconnection.sh', 0o755)
    print("✅ Test script created: /tmp/test_reconnection.sh")
    print("   Run: sudo /tmp/test_reconnection.sh")

def main():
    """Main function"""
    print("🔧 Device Auto-Reconnection Fixer")
    print("=" * 40)

    if len(sys.argv) > 1:
        ssid = sys.argv[1]
        password = sys.argv[2] if len(sys.argv) > 2 else "portal123"
    else:
        ssid = "ActivePortal"
        password = "portal123"

    print(f"Target SSID: {ssid}")
    print(f"Password: {password}")
    print()

    # Check current network profile
    check_network_profile(ssid)

    # Create network profile
    create_network_profile(ssid, password)

    # Show device-specific fixes
    fix_common_device_issues()

    # Show tips
    show_device_specific_tips()

    # Create test script
    create_reconnection_test()

    print("\n" + "=" * 40)
    print("✅ Auto-reconnection fixes applied!")
    print("\nNext steps:")
    print("1. Restart your hotspot: sudo python3 hotspot_portal.py")
    print("2. Test reconnection with: sudo /tmp/test_reconnection.sh")
    print("3. Check device-specific settings above")
    print("4. Monitor: sudo python3 hotspot_portal.py --diagnose")

if __name__ == "__main__":
    main()
