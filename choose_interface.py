#!/usr/bin/env python3
"""
Interface Selection Helper
Helps choose the right interface for the hotspot
"""

import subprocess
import sys
import os

def get_network_interfaces():
    """Get all available network interfaces"""
    interfaces = []
    
    try:
        result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if ': ' in line and not line.startswith(' '):
                    parts = line.split(': ')
                    if len(parts) >= 2:
                        interface_name = parts[1].split('@')[0]  # Remove @ part
                        if interface_name not in ['lo']:  # Skip loopback
                            interfaces.append(interface_name)
    except Exception as e:
        print(f"Error getting interfaces: {e}")
    
    return interfaces

def get_interface_info(interface):
    """Get information about a specific interface"""
    info = {
        'name': interface,
        'status': 'DOWN',
        'ip': None,
        'type': 'Unknown',
        'is_wireless': False,
        'ap_support': 'Unknown'
    }

    try:
        # Check if interface is up
        result = subprocess.run(['ip', 'link', 'show', interface], capture_output=True, text=True)
        if result.returncode == 0:
            if 'UP' in result.stdout:
                info['status'] = 'UP'

            # Check if it's wireless
            if 'wlan' in interface or 'wlo' in interface or 'wlx' in interface:
                info['is_wireless'] = True
                info['type'] = 'Wireless'
            elif 'eth' in interface or 'eno' in interface:
                info['type'] = 'Ethernet'

        # Get IP address
        result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'inet ' in line and '127.0.0.1' not in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'inet':
                            info['ip'] = parts[i + 1].split('/')[0]
                            break

        # Check AP mode support
        ap_support, ap_message = check_ap_mode_support(interface)
        info['ap_support'] = ap_message

    except Exception as e:
        print(f"Error getting info for {interface}: {e}")

    return info

def find_internet_interface():
    """Find the interface with internet connection"""
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'default via' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'dev':
                            return parts[i + 1]
    except:
        pass
    return None

def check_ap_mode_support(interface):
    """Check if interface supports AP mode"""
    try:
        result = subprocess.run(['iw', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            # Check if interface is listed
            if f"Interface {interface}" in result.stdout:
                # Get detailed info
                result = subprocess.run(['iw', 'dev', interface, 'info'], capture_output=True, text=True)
                if result.returncode == 0 and 'type AP' in result.stdout:
                    return True, "Supports AP mode"
                else:
                    return False, "Does not support AP mode"
        else:
            return True, "iw not available, assuming AP support"
    except FileNotFoundError:
        return True, "iw not available, assuming AP support"
    except Exception as e:
        return False, f"Error checking AP mode: {e}"

def main():
    """Main interface selection function"""
    print("🔍 Network Interface Selection Helper")
    print("=" * 50)

    # Get all interfaces
    interfaces = get_network_interfaces()
    if not interfaces:
        print("❌ No network interfaces found")
        return
    
    # Get interface information
    interface_info = []
    for interface in interfaces:
        info = get_interface_info(interface)
        interface_info.append(info)

    # Find internet interface
    internet_interface = find_internet_interface()

    print("📋 Available Network Interfaces:")
    print()

    for i, info in enumerate(interface_info):
        status_icon = "🟢" if info['status'] == 'UP' else "🔴"
        type_icon = "📶" if info['is_wireless'] else "🔌"
        ip_info = f" ({info['ip']})" if info['ip'] else ""
        internet_marker = " 🌐" if info['name'] == internet_interface else ""
        ap_icon = "✅" if "Supports AP" in info['ap_support'] else "❌"

        print(f"{i+1:2d}. {status_icon} {type_icon} {info['name']:16} {info['status']:4} {info['type']:8} {ip_info}{internet_marker}")
        print(f"    AP Support: {ap_icon} {info['ap_support']}")

    print()
    print("💡 Recommendations:")
    print()

    # Find wireless interfaces
    wireless_interfaces = [info for info in interface_info if info['is_wireless']]
    if wireless_interfaces:
        print("📶 For Hotspot (Wireless interfaces):")
        for info in wireless_interfaces:
            if info['status'] == 'DOWN' or not info['ip']:
                ap_status = "✅" if "Supports AP" in info['ap_support'] else "❌"
                print(f"   {ap_status} {info['name']} - Good for hotspot (not in use)")
            else:
                print(f"   ⚠️  {info['name']} - Currently in use ({info['ip']})")
        print()

    # Show internet interface
    if internet_interface:
        print(f"🌐 Internet Interface: {internet_interface}")
        print("   This interface will be used for internet routing")
        print()

    print("🚀 Usage Examples:")
    print()

    # Show examples
    for info in interface_info:
        if info['is_wireless'] and (info['status'] == 'DOWN' or not info['ip']) and "Supports AP" in info['ap_support']:
            print(f"sudo python3 hotspot_portal.py \"MyHotspot\" \"password123\" \"{info['name']}\"")

    print()
    print("⚠️  Important Notes:")
    print("• Choose a wireless interface that's NOT currently in use")
    print("• Interface must support AP mode (✅)")
    print("• The internet interface will remain connected")
    print("• Other interfaces will be unaffected")
    print("• Use Ctrl+C to stop the hotspot")
    print("• Avoid trailing colons (:) in interface names")

if __name__ == "__main__":
    main()
