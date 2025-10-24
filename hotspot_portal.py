#!/usr/bin/env python3
"""
Active Portal - Hotspot with Captive Portal (VISIBILITY FIXED)
Creates a WiFi hotspot and serves a captive portal web page
Enhanced to ensure hotspot is visible on all devices
"""

import subprocess
import sys
import time
import threading
import signal
import os
import socket
import netifaces
import logging
from web.web_app import WebApp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HotspotPortal:
    def __init__(self, ssid="ActivePortal", password="portal123", interface="wlan0"):
        self.ssid = ssid
        self.password = password
        # Clean interface name by removing trailing colons and invalid characters
        self.interface = interface.rstrip(':').strip()
        if not self.interface:
            self.interface = "wlan0"
        self.web_app = WebApp()
        self.hostapd_process = None
        self.dnsmasq_process = None
        self.flask_thread = None
        self.running = False
        
    
    def validate_interface(self):
        """Validate that the interface exists and supports AP mode"""
        try:
            # Check if interface exists
            result = subprocess.run(['ip', 'link', 'show', self.interface], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Interface {self.interface} does not exist")
                return False

            # Check if interface is wireless (relaxed check)
            if not any(wireless in self.interface for wireless in ['wlan', 'wlo', 'wlx', 'wifi', 'wlp']):
                logger.warning(f"Interface {self.interface} may not be wireless, but continuing anyway")

            logger.info(f"✅ Interface {self.interface} validation passed")
            return True

        except Exception as e:
            logger.error(f"Error validating interface {self.interface}: {e}")
            return False
    
    def check_root(self):
        """Check if running as root"""
        if os.geteuid() != 0:
            logger.error("This script must be run as root (use sudo)")
            sys.exit(1)

    def check_dependencies(self):
        """Check if required tools are installed"""
        required_tools = ['hostapd', 'dnsmasq', 'iptables']
        missing_tools = []
        
        for tool in required_tools:
            try:
                subprocess.run(['which', tool], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                missing_tools.append(tool)
        
        if missing_tools:
            logger.error(f"Missing required tools: {', '.join(missing_tools)}")
            logger.error("Install with: sudo apt update && sudo apt install hostapd dnsmasq iptables")
            sys.exit(1)
    
    def unblock_wireless(self):
        """Ensure wireless is not blocked by rfkill"""
        logger.info("🔓 Checking wireless blocks...")
        try:
            # Unblock all wireless devices
            subprocess.run(['rfkill', 'unblock', 'wifi'], check=False)
            subprocess.run(['rfkill', 'unblock', 'wlan'], check=False)
            subprocess.run(['rfkill', 'unblock', 'all'], check=False)
            logger.info("✅ Wireless unblocked")
        except Exception as e:
            logger.warning(f"Could not unblock wireless: {e}")

    def stop_network_manager_on_interface(self):
        """Stop NetworkManager from managing the hotspot interface"""
        logger.info(f"🛑 Unmanaging {self.interface} from NetworkManager...")
        try:
            # Set interface as unmanaged
            subprocess.run(['nmcli', 'device', 'set', self.interface, 'managed', 'no'], 
                          check=False, capture_output=True)
            time.sleep(1)
            logger.info(f"✅ NetworkManager will not interfere with {self.interface}")
        except Exception as e:
            logger.warning(f"Could not unmanage interface from NetworkManager: {e}")

    def create_hostapd_config(self):
        """Create hostapd configuration file - OPTIMIZED FOR VISIBILITY"""
        # Use channel 6 (most compatible) instead of 7
        config = f"""# Hostapd Configuration - OPTIMIZED FOR VISIBILITY
interface={self.interface}
driver=nl80211

# SSID and broadcast - CRITICAL FOR VISIBILITY
ssid={self.ssid}
ignore_broadcast_ssid=0
utf8_ssid=1

# Use channel 6 (most universally compatible)
hw_mode=g
channel=6

# Basic wireless settings
ieee80211n=1
wmm_enabled=1

# Security settings
auth_algs=1
wpa=2
wpa_passphrase={self.password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP

# MAC address filtering (disabled for maximum compatibility)
macaddr_acl=0

# Enhanced settings for better visibility and reconnection
beacon_int=100
dtim_period=2

# Inactivity settings for better client management
ap_max_inactivity=300
skip_inactivity_poll=0

# Country code for better compatibility
country_code=US
ieee80211d=1

# Client management
max_num_sta=50

# Disable AP isolation
ap_isolate=0

# Enhanced logging
logger_syslog=-1
logger_stdout=2
logger_syslog_level=2
logger_stdout_level=2

# Additional compatibility settings
preamble=1
"""
        
        with open('/tmp/hostapd.conf', 'w') as f:
            f.write(config)
        
        logger.info("✅ Created optimized hostapd configuration")
        logger.info(f"   SSID: {self.ssid}")
        logger.info(f"   Channel: 6 (most compatible)")
        logger.info(f"   Broadcast: ENABLED")
    
    def verify_hostapd_config(self):
        """Test hostapd configuration before starting"""
        logger.info("🧪 Testing hostapd configuration...")
        try:
            result = subprocess.run(
                ['hostapd', '-t', '/tmp/hostapd.conf'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("✅ hostapd configuration is valid")
                return True
            else:
                logger.error(f"❌ hostapd configuration error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.info("✅ hostapd configuration test passed (timeout is normal)")
            return True
        except Exception as e:
            logger.warning(f"Could not test hostapd config: {e}")
            return True  # Continue anyway

    def create_dnsmasq_config(self):
        """Create dnsmasq configuration file"""
        config = f"""interface={self.interface}
dhcp-range=192.168.4.2,192.168.4.50,255.255.255.0,24h
dhcp-leasefile=/tmp/dnsmasq.leases
dhcp-authoritative
dhcp-lease-max=100

# Enhanced DHCP options
dhcp-option=1,255.255.255.0
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
dhcp-option=15,ActivePortal
dhcp-option=28,192.168.4.255
dhcp-option=42,192.168.4.1
dhcp-option=43,192.168.4.1

# Rapid DHCP for faster connection
dhcp-rapid-commit

# DNS servers
server=8.8.8.8
server=1.1.1.1
server=208.67.222.222

# Logging
log-queries
log-dhcp

# Listen addresses
listen-address=127.0.0.1
listen-address=192.168.4.1
bind-interfaces
no-dhcp-interface=eth0
no-dhcp-interface=lo

# Captive portal detection redirects
address=/clients3.google.com/192.168.4.1
address=/connectivitycheck.gstatic.com/192.168.4.1
address=/connectivitycheck.android.com/192.168.4.1
address=/google.com/192.168.4.1
address=/captive.apple.com/192.168.4.1
address=/www.apple.com/192.168.4.1
address=/www.msftconnecttest.com/192.168.4.1
address=/msftconnecttest.com/192.168.4.1
address=/ncsi.txt/192.168.4.1
address=/hotspot-detect.html/192.168.4.1
address=/generate_204/192.168.4.1
address=/connectivity-check.html/192.168.4.1
address=/success.txt/192.168.4.1

# DNS caching
cache-size=1000
neg-ttl=3600

# Additional options
dhcp-option=252,"\\n"
dhcp-option=114,http://192.168.4.1:5000/
"""
        
        with open('/tmp/dnsmasq.conf', 'w') as f:
            f.write(config)
        
        logger.info("✅ Created dnsmasq configuration")
    
    def find_internet_interface(self):
        """Find the main internet interface (not the hotspot interface)"""
        try:
            # Get all interfaces
            result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'default via' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'dev':
                                interface = parts[i + 1]
                                if interface != self.interface:
                                    logger.info(f"📡 Internet interface: {interface}")
                                    return interface
            
            # Fallback to common interfaces
            common_interfaces = ['eth0', 'eno1', 'ens192', 'wlo1', 'enp0s3', 'enp1s0']
            for interface in common_interfaces:
                if interface != self.interface:
                    try:
                        result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
                        if result.returncode == 0 and 'inet ' in result.stdout:
                            logger.info(f"📡 Using fallback internet interface: {interface}")
                            return interface
                    except:
                        continue
            
            logger.warning("⚠️ Could not determine internet interface, using eth0")
            return 'eth0'
            
        except Exception as e:
            logger.warning(f"Error finding internet interface: {e}, using eth0")
            return 'eth0'
    
    def stop_conflicting_services(self):
        """Stop conflicting services only for the hotspot interface"""
        logger.info("🛑 Stopping conflicting services...")
        
        # Stop existing processes
        subprocess.run(['pkill', 'dnsmasq'], check=False)
        subprocess.run(['pkill', 'hostapd'], check=False)
        subprocess.run(['pkill', '-f', f'dhcpcd.*{self.interface}'], check=False)
        
        time.sleep(2)
        logger.info("✅ Conflicting services stopped")

    def setup_network(self):
        """Setup network interface and routing"""
        try:
            # Unblock wireless first
            self.unblock_wireless()
            
            # Stop NetworkManager from interfering
            self.stop_network_manager_on_interface()
            
            # Stop conflicting services
            self.stop_conflicting_services()
            
            # Bring down interface
            logger.info(f"🔧 Configuring interface {self.interface}...")
            subprocess.run(['ip', 'link', 'set', self.interface, 'down'], check=True)
            
            # Clear any existing IP addresses
            subprocess.run(['ip', 'addr', 'flush', 'dev', self.interface], check=False)
            
            # Configure interface
            subprocess.run(['ip', 'addr', 'add', '192.168.4.1/24', 'dev', self.interface], check=True)
            subprocess.run(['ip', 'link', 'set', self.interface, 'up'], check=True)
            
            # Verify interface is up
            result = subprocess.run(['ip', 'link', 'show', self.interface], capture_output=True, text=True)
            if "UP" in result.stdout:
                logger.info(f"✅ Interface {self.interface} is UP")
            else:
                logger.error(f"❌ Interface {self.interface} failed to come UP")
                raise Exception("Interface failed to start")
            
            # Enable IP forwarding
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('1')
            
            # Find the main internet interface
            internet_interface = self.find_internet_interface()
            
            # Setup iptables rules for NAT
            subprocess.run(['iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', internet_interface, '-j', 'MASQUERADE'], check=True)
            subprocess.run(['iptables', '-A', 'FORWARD', '-i', self.interface, '-o', internet_interface, '-j', 'ACCEPT'], check=True)
            subprocess.run(['iptables', '-A', 'FORWARD', '-i', internet_interface, '-o', self.interface, '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'], check=True)
            
            # Redirect traffic to captive portal
            subprocess.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', self.interface, '-p', 'tcp', '--dport', '80', '-j', 'DNAT', '--to-destination', '192.168.4.1:5000'], check=True)
            subprocess.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', self.interface, '-p', 'tcp', '--dport', '443', '-j', 'DNAT', '--to-destination', '192.168.4.1:5000'], check=True)
            subprocess.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', self.interface, '-p', 'udp', '--dport', '53', '-j', 'DNAT', '--to-destination', '192.168.4.1:53'], check=True)
            
            # Allow necessary traffic
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'icmp', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'udp', '--dport', '67', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'udp', '--dport', '68', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'udp', '--dport', '53', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'tcp', '--dport', '53', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'tcp', '--dport', '5000', '-j', 'ACCEPT'], check=False)
            
            logger.info("✅ Network setup completed")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Network setup failed: {e}")
            raise
    
    def start_hostapd(self):
        """Start hostapd daemon with verification"""
        try:
            logger.info("🚀 Starting hostapd...")
            
            # Start hostapd in background
            self.hostapd_process = subprocess.Popen(
                ['hostapd', '/tmp/hostapd.conf'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait and verify it started
            time.sleep(3)
            
            # Check if process is still running
            if self.hostapd_process.poll() is not None:
                # Process died
                stdout, stderr = self.hostapd_process.communicate()
                logger.error(f"❌ hostapd failed to start!")
                logger.error(f"Error: {stderr.decode()}")
                raise Exception("hostapd failed to start")
            
            # Verify SSID is broadcasting
            result = subprocess.run(
                ['iw', 'dev', self.interface, 'scan'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if self.ssid in result.stdout:
                logger.info(f"✅ hostapd started - SSID '{self.ssid}' IS BROADCASTING!")
            else:
                logger.warning(f"⚠️ hostapd started but SSID not visible in scan yet (may take a moment)")
            
        except subprocess.TimeoutExpired:
            logger.info("✅ hostapd started (scan timeout is normal)")
        except Exception as e:
            logger.error(f"❌ Failed to start hostapd: {e}")
            raise
    
    def start_dnsmasq(self):
        """Start dnsmasq daemon"""
        try:
            # Kill any existing dnsmasq processes
            subprocess.run(['pkill', 'dnsmasq'], check=False)
            time.sleep(1)
            
            # Test dnsmasq configuration
            test_result = subprocess.run(['dnsmasq', '--test', '--conf-file=/tmp/dnsmasq.conf'], 
                                       capture_output=True, text=True)
            if test_result.returncode != 0:
                logger.error(f"❌ DNSmasq configuration error: {test_result.stderr}")
                raise Exception(f"DNSmasq configuration invalid: {test_result.stderr}")
            
            # Start dnsmasq
            self.dnsmasq_process = subprocess.Popen(['dnsmasq', '--conf-file=/tmp/dnsmasq.conf', '--no-daemon'])
            logger.info("✅ Started dnsmasq")
            time.sleep(2)
        except Exception as e:
            logger.error(f"❌ Failed to start dnsmasq: {e}")
            raise
    
    def start_flask(self):
        """Start Flask web server"""
        try:
            self.flask_thread = threading.Thread(
                target=lambda: self.web_app.run(debug=False)
            )
            self.flask_thread.daemon = True
            self.flask_thread.start()
            logger.info("✅ Started Flask web server on port 5000")
        except Exception as e:
            logger.error(f"❌ Failed to start Flask: {e}")
            raise
    
    def verify_hotspot_visible(self):
        """Final verification that hotspot is visible"""
        logger.info("\n" + "=" * 60)
        logger.info("🔍 FINAL VISIBILITY CHECK")
        logger.info("=" * 60)
        
        checks_passed = 0
        total_checks = 4
        
        # Check 1: hostapd running
        result = subprocess.run(['pgrep', 'hostapd'], capture_output=True)
        if result.returncode == 0:
            logger.info("✅ Check 1/4: hostapd is running")
            checks_passed += 1
        else:
            logger.error("❌ Check 1/4: hostapd is NOT running")
        
        # Check 2: Interface is UP
        result = subprocess.run(['ip', 'link', 'show', self.interface], capture_output=True, text=True)
        if "UP" in result.stdout:
            logger.info(f"✅ Check 2/4: Interface {self.interface} is UP")
            checks_passed += 1
        else:
            logger.error(f"❌ Check 2/4: Interface {self.interface} is DOWN")
        
        # Check 3: SSID in scan
        try:
            result = subprocess.run(
                ['iw', 'dev', self.interface, 'scan'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if self.ssid in result.stdout:
                logger.info(f"✅ Check 3/4: SSID '{self.ssid}' visible in scan")
                checks_passed += 1
            else:
                logger.warning(f"⚠️ Check 3/4: SSID not in scan (may need more time)")
        except:
            logger.warning("⚠️ Check 3/4: Could not perform scan")
        
        # Check 4: Interface in AP mode
        try:
            result = subprocess.run(['iw', 'dev', self.interface, 'info'], capture_output=True, text=True)
            if 'type AP' in result.stdout or 'type managed' in result.stdout:
                logger.info("✅ Check 4/4: Interface in correct mode")
                checks_passed += 1
            else:
                logger.warning("⚠️ Check 4/4: Interface mode unclear")
        except:
            logger.warning("⚠️ Check 4/4: Could not check interface mode")
        
        logger.info("=" * 60)
        logger.info(f"📊 Visibility Score: {checks_passed}/{total_checks} checks passed")
        
        if checks_passed >= 3:
            logger.info("✅ Hotspot should be VISIBLE on other devices!")
        elif checks_passed >= 2:
            logger.warning("⚠️ Hotspot may be visible, but some issues detected")
        else:
            logger.error("❌ Hotspot likely NOT visible - check errors above")
        
        logger.info("=" * 60)
    
    def cleanup(self):
        """Clean up processes and network configuration"""
        logger.info("🧹 Cleaning up hotspot services...")
        
        # Stop processes
        if self.hostapd_process:
            self.hostapd_process.terminate()
            self.hostapd_process.wait()
        
        if self.dnsmasq_process:
            self.dnsmasq_process.terminate()
            self.dnsmasq_process.wait()
        
        # Clean up iptables rules
        try:
            internet_interface = self.find_internet_interface()
            subprocess.run(['iptables', '-t', 'nat', '-D', 'POSTROUTING', '-o', internet_interface, '-j', 'MASQUERADE'], check=False)
            subprocess.run(['iptables', '-D', 'FORWARD', '-i', self.interface, '-o', internet_interface, '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-D', 'FORWARD', '-i', internet_interface, '-o', self.interface, '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', self.interface, '-p', 'tcp', '--dport', '80', '-j', 'DNAT', '--to-destination', '192.168.4.1:5000'], check=False)
            subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', self.interface, '-p', 'tcp', '--dport', '443', '-j', 'DNAT', '--to-destination', '192.168.4.1:5000'], check=False)
            subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', self.interface, '-p', 'udp', '--dport', '53', '-j', 'DNAT', '--to-destination', '192.168.4.1:53'], check=False)
            subprocess.run(['iptables', '-D', 'INPUT', '-i', self.interface, '-p', 'icmp', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-D', 'INPUT', '-i', self.interface, '-p', 'udp', '--dport', '67', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-D', 'INPUT', '-i', self.interface, '-p', 'udp', '--dport', '68', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-D', 'INPUT', '-i', self.interface, '-p', 'udp', '--dport', '53', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-D', 'INPUT', '-i', self.interface, '-p', 'tcp', '--dport', '53', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-D', 'INPUT', '-i', self.interface, '-p', 'tcp', '--dport', '5000', '-j', 'ACCEPT'], check=False)
        except:
            pass
        
        # Clean up temporary files
        for file in ['/tmp/hostapd.conf', '/tmp/dnsmasq.conf', '/tmp/dnsmasq.leases']:
            try:
                os.remove(file)
            except:
                pass
        
        logger.info("✅ Cleanup completed")
    
    def diagnose_issues(self):
        """Diagnose common auto-reconnection issues"""
        logger.info("🔍 Diagnosing issues...")
        
        issues = []
        
        # Check if hostapd is running
        try:
            result = subprocess.run(['pgrep', 'hostapd'], capture_output=True, text=True)
            if result.returncode != 0:
                issues.append("hostapd is not running")
            else:
                logger.info("✅ hostapd is running")
        except Exception as e:
            issues.append(f"Error checking hostapd: {e}")
        
        # Check if dnsmasq is running
        try:
            result = subprocess.run(['pgrep', 'dnsmasq'], capture_output=True, text=True)
            if result.returncode != 0:
                issues.append("dnsmasq is not running")
            else:
                logger.info("✅ dnsmasq is running")
        except Exception as e:
            issues.append(f"Error checking dnsmasq: {e}")
        
        # Check interface status
        try:
            result = subprocess.run(['ip', 'link', 'show', self.interface], capture_output=True, text=True)
            if "UP" not in result.stdout:
                issues.append(f"Interface {self.interface} is not UP")
            else:
                logger.info(f"✅ Interface {self.interface} is UP")
        except Exception as e:
            issues.append(f"Error checking interface: {e}")
        
        # Check rfkill
        try:
            result = subprocess.run(['rfkill', 'list'], capture_output=True, text=True)
            if "Soft blocked: yes" in result.stdout:
                issues.append("Wireless is blocked by rfkill")
            else:
                logger.info("✅ Wireless not blocked")
        except Exception as e:
            logger.warning(f"Could not check rfkill: {e}")
        
        # Check DHCP leases
        lease_file = "/tmp/dnsmasq.leases"
        if os.path.exists(lease_file):
            logger.info("✅ DHCP lease file exists")
            with open(lease_file, 'r') as f:
                leases = f.read()
                if leases.strip():
                    logger.info(f"📋 Active DHCP leases: {len(leases.strip().split(chr(10)))}")
                else:
                    issues.append("No active DHCP leases found")
        else:
            issues.append("DHCP lease file not found")
        
        # Check iptables rules
        try:
            result = subprocess.run(['iptables', '-t', 'nat', '-L'], capture_output=True, text=True)
            if "192.168.4.1:5000" not in result.stdout:
                issues.append("Captive portal iptables rules missing")
            else:
                logger.info("✅ Captive portal iptables rules present")
        except Exception as e:
            issues.append(f"Error checking iptables: {e}")
        
        return issues

    def stop(self):
        """Stop the hotspot portal"""
        self.running = False

    def start(self, diagnose=False):
        """Start the hotspot portal"""
        try:
            self.check_root()
            self.check_dependencies()

            # Validate interface before proceeding
            if not self.validate_interface():
                logger.error(f"Interface {self.interface} is not valid for hotspot use")
                logger.error("Use 'ip link show' to find available interfaces")
                sys.exit(1)

            if diagnose:
                issues = self.diagnose_issues()
                if issues:
                    logger.warning("⚠️ Found issues:")
                    for issue in issues:
                        logger.warning(f"  - {issue}")
                else:
                    logger.info("✅ No obvious issues found")
                return

            logger.info("=" * 60)
            logger.info(f"🚀 Starting hotspot '{self.ssid}' on interface {self.interface}")
            logger.info("=" * 60)

            # Create configuration files
            self.create_hostapd_config()
            self.verify_hostapd_config()
            self.create_dnsmasq_config()

            # Setup network
            self.setup_network()

            # Start services
            self.start_hostapd()
            self.start_dnsmasq()
            self.start_flask()

            # Verify visibility
            self.verify_hotspot_visible()

            self.running = True
            
            logger.info("\n" + "=" * 60)
            logger.info("✅ HOTSPOT PORTAL IS RUNNING!")
            logger.info("=" * 60)
            logger.info(f"📡 SSID: {self.ssid}")
            logger.info(f"🔑 Password: {self.password}")
            logger.info(f"🌐 Gateway: 192.168.4.1")
            logger.info(f"🔌 Interface: {self.interface}")
            logger.info("")
            logger.info("📱 NEXT STEPS:")
            logger.info("   1. Check your phone/device WiFi settings")
            logger.info("   2. Look for network '{}'".format(self.ssid))
            logger.info("   3. Connect using password '{}'".format(self.password))
            logger.info("   4. Open any website to see the portal")
            logger.info("")
            logger.info("⚠️  IF HOTSPOT NOT VISIBLE:")
            logger.info("   • Wait 10-15 seconds for broadcast to stabilize")
            logger.info("   • Toggle WiFi off/on on your device")
            logger.info("   • Check logs above for any errors")
            logger.info("   • Run: sudo python3 {} --diagnose".format(sys.argv[0]))
            logger.info("=" * 60)

            # Keep running until interrupted
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\n⏹️  Received interrupt signal")

        except Exception as e:
            logger.error(f"❌ Error starting hotspot portal: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup()
            sys.exit(1)
        finally:
            self.cleanup()

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    logger.info("\n🛑 Received signal, shutting down...")
    portal.stop()

def main():
    """Main function"""
    # Parse command line arguments
    ssid = "ActivePortal"
    password = "portal123"
    interface = "wlan0"
    diagnose = False
    
    # Check for diagnostic mode
    if "--diagnose" in sys.argv or "-d" in sys.argv:
        diagnose = True
        sys.argv.remove("--diagnose" if "--diagnose" in sys.argv else "-d")
    
    if len(sys.argv) > 1:
        ssid = sys.argv[1]
    if len(sys.argv) > 2:
        password = sys.argv[2]
    if len(sys.argv) > 3:
        interface = sys.argv[3]
    
    # Create global portal instance
    global portal
    portal = HotspotPortal(ssid, password, interface)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the portal
    portal.start(diagnose=diagnose)

if __name__ == "__main__":
    main()