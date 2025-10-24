#!/usr/bin/env python3
"""
Connection Troubleshooting Script
Helps diagnose why devices disconnect during DHCP
"""

import subprocess
import sys
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_interface(interface):
    """Check if interface exists and is up"""
    try:
        result = subprocess.run(['ip', 'link', 'show', interface], capture_output=True, text=True)
        if result.returncode == 0:
            if "UP" in result.stdout:
                logger.info(f"✅ Interface {interface} is UP")
                return True
            else:
                logger.warning(f"⚠️ Interface {interface} is DOWN")
                return False
        else:
            logger.error(f"❌ Interface {interface} not found")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking interface: {e}")
        return False

def check_dhcp_leases():
    """Check DHCP lease file"""
    lease_file = "/tmp/dnsmasq.leases"
    if os.path.exists(lease_file):
        with open(lease_file, 'r') as f:
            leases = f.read()
            if leases.strip():
                logger.info(f"✅ DHCP leases found: {len(leases.strip().split(chr(10)))} devices")
                for line in leases.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            mac = parts[1]
                            ip = parts[2]
                            hostname = parts[3] if len(parts) > 3 else "unknown"
                            logger.info(f"  📱 {hostname} ({mac}) -> {ip}")
                return True
            else:
                logger.warning("⚠️ No DHCP leases found")
                return False
    else:
        logger.warning("⚠️ DHCP lease file not found")
        return False

def check_services():
    """Check if required services are running"""
    services = ['hostapd', 'dnsmasq']
    all_running = True
    
    for service in services:
        try:
            result = subprocess.run(['pgrep', service], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"✅ {service} is running (PID: {result.stdout.strip()})")
            else:
                logger.error(f"❌ {service} is not running")
                all_running = False
        except Exception as e:
            logger.error(f"❌ Error checking {service}: {e}")
            all_running = False
    
    return all_running

def check_network_config(interface):
    """Check network configuration"""
    try:
        # Check IP address
        result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
        if "192.168.4.1" in result.stdout:
            logger.info("✅ Interface has correct IP address (192.168.4.1)")
        else:
            logger.error("❌ Interface missing IP address 192.168.4.1")
            return False
        
        # Check iptables rules
        result = subprocess.run(['iptables', '-t', 'nat', '-L'], capture_output=True, text=True)
        if "192.168.4.1:5000" in result.stdout:
            logger.info("✅ Captive portal iptables rules present")
        else:
            logger.warning("⚠️ Captive portal iptables rules missing")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error checking network config: {e}")
        return False

def monitor_connections(interface, duration=30):
    """Monitor device connections for specified duration"""
    logger.info(f"🔍 Monitoring connections on {interface} for {duration} seconds...")
    
    start_time = time.time()
    connections = set()
    
    while time.time() - start_time < duration:
        try:
            # Check for new connections
            result = subprocess.run(['iw', 'dev', interface, 'station', 'dump'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_connections = set()
                for line in lines:
                    if 'Station' in line:
                        mac = line.split()[1]
                        current_connections.add(mac)
                
                # Check for new connections
                new_connections = current_connections - connections
                if new_connections:
                    for mac in new_connections:
                        logger.info(f"📱 New device connected: {mac}")
                        connections.add(mac)
                
                # Check for disconnections
                disconnected = connections - current_connections
                if disconnected:
                    for mac in disconnected:
                        logger.warning(f"📱 Device disconnected: {mac}")
                        connections.discard(mac)
                
                connections = current_connections
            else:
                logger.warning("⚠️ Could not check station status")
            
            time.sleep(2)
        except Exception as e:
            logger.error(f"❌ Error monitoring connections: {e}")
            break
    
    logger.info(f"📊 Total unique connections during monitoring: {len(connections)}")

def main():
    """Main troubleshooting function"""
    logger.info("🔧 Active Portal Connection Troubleshooter")
    logger.info("=" * 50)
    
    # Get interface from command line or use default
    interface = sys.argv[1] if len(sys.argv) > 1 else "wlo1"
    
    logger.info(f"🔍 Checking interface: {interface}")
    
    # Check interface
    if not check_interface(interface):
        logger.error("❌ Interface check failed")
        return
    
    # Check services
    if not check_services():
        logger.error("❌ Service check failed")
        return
    
    # Check network configuration
    if not check_network_config(interface):
        logger.error("❌ Network configuration check failed")
        return
    
    # Check DHCP leases
    check_dhcp_leases()
    
    # Monitor connections
    logger.info("\n🔍 Starting connection monitoring...")
    monitor_connections(interface, 30)
    
    logger.info("\n💡 Troubleshooting Tips:")
    logger.info("1. Ensure device WiFi is not in power-saving mode")
    logger.info("2. Check if device has 'Auto-connect' enabled")
    logger.info("3. Try forgetting and reconnecting to the network")
    logger.info("4. Check device logs for DHCP errors")
    logger.info("5. Ensure device supports WPA2-PSK")

if __name__ == "__main__":
    main()
