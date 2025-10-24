#!/usr/bin/env python3
"""
Active Portal - Hotspot with Captive Portal
Creates a WiFi hotspot and serves a captive portal web page
Compatible with Parrot OS
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

            # Check if interface is wireless
            if not any(wireless in self.interface for wireless in ['wlan', 'wlo', 'wlx', 'wifi']):
                logger.error(f"Interface {self.interface} does not appear to be wireless")
                return False

            # Check if interface supports AP mode
            try:
                result = subprocess.run(['iw', 'list'], capture_output=True, text=True)
                if f"Interface {self.interface}" in result.stdout:
                    # Try to get capabilities for this specific interface
                    result = subprocess.run(['iw', 'dev', self.interface, 'info'], capture_output=True, text=True)
                    if result.returncode == 0 and 'type AP' in result.stdout:
                        logger.info(f"Interface {self.interface} supports AP mode")
                        return True
            except FileNotFoundError:
                logger.warning("iw command not found, assuming interface supports AP mode")

            logger.info(f"Interface {self.interface} validation passed")
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
    
    def create_hostapd_config(self):
        """Create hostapd configuration file"""
        config = f"""interface={self.interface}
driver=nl80211
ssid={self.ssid}
hw_mode=g
channel=7
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={self.password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP

# Enhanced settings for better client reconnection
# Faster beacon for quicker reconnection detection
beacon_int=100
# DTIM for power saving devices
dtim_period=2

# Disable power saving features that interfere with reconnection
ap_max_inactivity=300
skip_inactivity_poll=0
max_listen_interval=65535

# Enable country code for regulatory compliance and better compatibility
country_code=US
ieee80211d=1
ieee80211h=1

# Enhanced wireless settings
ieee80211n=1
ieee80211ac=1
ht_capab=[HT40+][SHORT-GI-20][SHORT-GI-40][DSSS_CCK-40]

# Better client management
max_num_sta=50
preamble=1

# Enable WMM for better device compatibility
wmm_enabled=1

# Disable AP isolation for better connectivity
ap_isolate=0

# Enhanced logging for debugging reconnection issues
logger_syslog=-1
logger_stdout=-1
logger_syslog_level=2
logger_stdout_level=2
"""
        
        with open('/tmp/hostapd.conf', 'w') as f:
            f.write(config)
        
        logger.info("Created hostapd configuration")
    
    def create_dnsmasq_config(self):
        """Create dnsmasq configuration file"""
        config = f"""interface={self.interface}
dhcp-range=192.168.4.2,192.168.4.50,255.255.255.0,24h
# Persistent DHCP lease file in /tmp (survives restarts)
dhcp-leasefile=/tmp/dnsmasq.leases
# DHCP authoritative mode for better client handling
dhcp-authoritative
# Longer lease time for better persistence (24 hours instead of 12)
dhcp-lease-max=100
# Enhanced DHCP options for better device compatibility
dhcp-option=1,255.255.255.0
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
dhcp-option=15,ActivePortal
dhcp-option=28,192.168.4.255
dhcp-option=42,192.168.4.1
dhcp-option=43,192.168.4.1
# Enable rapid commit for faster DHCP
dhcp-rapid-commit
# DNS servers (allow real DNS resolution)
server=8.8.8.8
server=1.1.1.1
server=208.67.222.222
# Enable logging
log-queries
log-dhcp
# Listen addresses
listen-address=127.0.0.1
listen-address=192.168.4.1
bind-interfaces
no-dhcp-interface=eth0
no-dhcp-interface=lo
# Redirect all DNS queries to portal
# Redirect ONLY captive portal detection domains to portal
# Android connectivity check
address=/clients3.google.com/192.168.4.1
address=/connectivitycheck.gstatic.com/192.168.4.1
address=/connectivitycheck.android.com/192.168.4.1
address=/google.com/192.168.4.1
# iOS connectivity check
address=/captive.apple.com/192.168.4.1
address=/www.apple.com/192.168.4.1
# Windows connectivity check
address=/www.msftconnecttest.com/192.168.4.1
address=/msftconnecttest.com/192.168.4.1
# Microsoft NCSI
address=/ncsi.txt/192.168.4.1
# Common captive portal detection
address=/hotspot-detect.html/192.168.4.1
address=/generate_204/192.168.4.1
address=/connectivity-check.html/192.168.4.1
address=/success.txt/192.168.4.1
address=/redirect/192.168.4.1
address=/canonical.html/192.168.4.1
address=/hotspot.html/192.168.4.1
address=/mobile/redirect/192.168.4.1
address=/windows/redirect/192.168.4.1
# Allow real DNS resolution for internet connectivity verification
# This prevents devices from thinking the network is broken
# Enable DNS caching
cache-size=1000
# Enable negative caching
neg-ttl=3600
# Additional DHCP options for better compatibility
dhcp-option=252,"\\n"
dhcp-option=114,http://192.168.4.1:5000/
"""
        
        with open('/tmp/dnsmasq.conf', 'w') as f:
            f.write(config)
        
        logger.info("Created dnsmasq configuration")
    
    def find_internet_interface(self):
        """Find the main internet interface (not the hotspot interface)"""
        try:
            # Get all interfaces
            result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True)
            if result.returncode == 0:
                # Parse the default route to find the interface
                for line in result.stdout.split('\n'):
                    if 'default via' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'dev':
                                interface = parts[i + 1]
                                if interface != self.interface:
                                    logger.info(f"Found internet interface: {interface}")
                                    return interface
            
            # Fallback to common interfaces (including eno1 which is common in modern systems)
            common_interfaces = ['eth0', 'eno1', 'ens192', 'wlo1', 'wlan0', 'enp0s3', 'enp1s0']
            for interface in common_interfaces:
                if interface != self.interface:
                    try:
                        result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
                        if result.returncode == 0 and 'inet ' in result.stdout and '127.0.0.1' not in result.stdout:
                            logger.info(f"Using fallback internet interface: {interface}")
                            return interface
                    except:
                        continue
            
            # Default fallback
            logger.warning("Could not determine internet interface, using eth0")
            return 'eth0'
            
        except Exception as e:
            logger.warning(f"Error finding internet interface: {e}, using eth0")
            return 'eth0'
    
    def stop_conflicting_services(self):
        """Stop conflicting services only for the hotspot interface"""
        logger.info("🛑 Stopping conflicting services for hotspot interface...")
        
        # Stop any existing dnsmasq
        subprocess.run(['pkill', 'dnsmasq'], check=False)
        
        # Stop any existing hostapd
        subprocess.run(['pkill', 'hostapd'], check=False)
        
        # Stop any existing dhcpcd on the specific interface
        subprocess.run(['pkill', '-f', f'dhcpcd.*{self.interface}'], check=False)
        
        # Only clear iptables rules related to our interface
        internet_interface = self.find_internet_interface()
        subprocess.run(['iptables', '-t', 'nat', '-D', 'POSTROUTING', '-o', internet_interface, '-j', 'MASQUERADE'], check=False)
        subprocess.run(['iptables', '-D', 'FORWARD', '-i', self.interface, '-o', internet_interface, '-j', 'ACCEPT'], check=False)
        subprocess.run(['iptables', '-D', 'FORWARD', '-i', internet_interface, '-o', self.interface, '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'], check=False)
        subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', self.interface, '-p', 'tcp', '--dport', '80', '-j', 'DNAT', '--to-destination', '192.168.4.1:5000'], check=False)
        subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', self.interface, '-p', 'tcp', '--dport', '443', '-j', 'DNAT', '--to-destination', '192.168.4.1:5000'], check=False)
        subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', self.interface, '-p', 'udp', '--dport', '53', '-j', 'DNAT', '--to-destination', '192.168.4.1:53'], check=False)
        
        time.sleep(2)
        logger.info("✅ Conflicting services stopped for hotspot interface")

    def setup_network(self):
        """Setup network interface and routing"""
        try:
            # Stop conflicting services first
            self.stop_conflicting_services()
            
            # Bring down interface
            subprocess.run(['ip', 'link', 'set', self.interface, 'down'], check=True)
            
            # Clear any existing IP addresses
            subprocess.run(['ip', 'addr', 'flush', 'dev', self.interface], check=False)
            
            # Configure interface
            subprocess.run(['ip', 'addr', 'add', '192.168.4.1/24', 'dev', self.interface], check=True)
            subprocess.run(['ip', 'link', 'set', self.interface, 'up'], check=True)
            
            # Enable IP forwarding
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('1')
            
            # Find the main internet interface (not the hotspot interface)
            internet_interface = self.find_internet_interface()
            
            # Setup iptables rules for NAT using the internet interface
            subprocess.run(['iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', internet_interface, '-j', 'MASQUERADE'], check=True)
            subprocess.run(['iptables', '-A', 'FORWARD', '-i', self.interface, '-o', internet_interface, '-j', 'ACCEPT'], check=True)
            subprocess.run(['iptables', '-A', 'FORWARD', '-i', internet_interface, '-o', self.interface, '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'], check=True)
            
            # Redirect ALL HTTP traffic to captive portal
            subprocess.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', self.interface, '-p', 'tcp', '--dport', '80', '-j', 'DNAT', '--to-destination', '192.168.4.1:5000'], check=True)
            
            # Redirect HTTPS traffic to captive portal (for apps)
            subprocess.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', self.interface, '-p', 'tcp', '--dport', '443', '-j', 'DNAT', '--to-destination', '192.168.4.1:5000'], check=True)
            
            # Redirect DNS queries to our server
            subprocess.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', self.interface, '-p', 'udp', '--dport', '53', '-j', 'DNAT', '--to-destination', '192.168.4.1:53'], check=True)
            
            # Add additional iptables rules for better device compatibility
            # Allow ICMP for ping
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'icmp', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-A', 'OUTPUT', '-o', self.interface, '-p', 'icmp', '-j', 'ACCEPT'], check=False)
            
            # Allow DHCP traffic
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'udp', '--dport', '67', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'udp', '--dport', '68', '-j', 'ACCEPT'], check=False)
            
            # Allow DNS traffic
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'udp', '--dport', '53', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'tcp', '--dport', '53', '-j', 'ACCEPT'], check=False)
            
            # Allow captive portal detection traffic
            subprocess.run(['iptables', '-A', 'INPUT', '-i', self.interface, '-p', 'tcp', '--dport', '5000', '-j', 'ACCEPT'], check=False)
            
            logger.info("Network setup completed")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Network setup failed: {e}")
            raise
    
    def start_hostapd(self):
        """Start hostapd daemon"""
        try:
            self.hostapd_process = subprocess.Popen(['hostapd', '/tmp/hostapd.conf'])
            logger.info("Started hostapd")
            time.sleep(2)  # Give hostapd time to start
        except Exception as e:
            logger.error(f"Failed to start hostapd: {e}")
            raise
    
    def start_dnsmasq(self):
        """Start dnsmasq daemon"""
        try:
            # Kill any existing dnsmasq processes
            subprocess.run(['pkill', 'dnsmasq'], check=False)
            time.sleep(1)
            
            # Test dnsmasq configuration first
            test_result = subprocess.run(['dnsmasq', '--test', '--conf-file=/tmp/dnsmasq.conf'], 
                                       capture_output=True, text=True)
            if test_result.returncode != 0:
                logger.error(f"DNSmasq configuration error: {test_result.stderr}")
                raise Exception(f"DNSmasq configuration invalid: {test_result.stderr}")
            
            # Start dnsmasq with our config
            self.dnsmasq_process = subprocess.Popen(['dnsmasq', '--conf-file=/tmp/dnsmasq.conf', '--no-daemon'])
            logger.info("Started dnsmasq")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Failed to start dnsmasq: {e}")
            raise
    
    def start_flask(self):
        """Start Flask web server"""
        try:
            self.flask_thread = threading.Thread(
                target=lambda: self.web_app.run(debug=False)
            )
            self.flask_thread.daemon = True
            self.flask_thread.start()
            logger.info("Started Flask web server")
        except Exception as e:
            logger.error(f"Failed to start Flask: {e}")
            raise
    
    def cleanup(self):
        """Clean up processes and network configuration"""
        logger.info("Cleaning up hotspot services...")
        
        # Stop processes
        if self.hostapd_process:
            self.hostapd_process.terminate()
            self.hostapd_process.wait()
        
        if self.dnsmasq_process:
            self.dnsmasq_process.terminate()
            self.dnsmasq_process.wait()
        
        # Clean up only our iptables rules (don't affect other interfaces)
        try:
            # Find the internet interface that was used
            internet_interface = self.find_internet_interface()
            
            # Remove our specific NAT rules
            subprocess.run(['iptables', '-t', 'nat', '-D', 'POSTROUTING', '-o', internet_interface, '-j', 'MASQUERADE'], check=False)
            subprocess.run(['iptables', '-D', 'FORWARD', '-i', self.interface, '-o', internet_interface, '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-D', 'FORWARD', '-i', internet_interface, '-o', self.interface, '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', self.interface, '-p', 'tcp', '--dport', '80', '-j', 'DNAT', '--to-destination', '192.168.4.1:5000'], check=False)
            subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', self.interface, '-p', 'tcp', '--dport', '443', '-j', 'DNAT', '--to-destination', '192.168.4.1:5000'], check=False)
            subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-i', self.interface, '-p', 'udp', '--dport', '53', '-j', 'DNAT', '--to-destination', '192.168.4.1:53'], check=False)
            
            # Remove our interface-specific rules
            subprocess.run(['iptables', '-D', 'INPUT', '-i', self.interface, '-p', 'icmp', '-j', 'ACCEPT'], check=False)
            subprocess.run(['iptables', '-D', 'OUTPUT', '-o', self.interface, '-p', 'icmp', '-j', 'ACCEPT'], check=False)
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
        
        logger.info("Hotspot cleanup completed - other interfaces unaffected")
    
    def diagnose_issues(self):
        """Diagnose common auto-reconnection issues"""
        logger.info("🔍 Diagnosing auto-reconnection issues...")
        
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
        
        # Check DHCP lease file
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
                logger.error("Use 'python3 choose_interface.py' to find a suitable interface")
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

            logger.info(f"Starting hotspot '{self.ssid}' on interface {self.interface}")

            # Create configuration files
            self.create_hostapd_config()
            self.create_dnsmasq_config()

            # Setup network
            self.setup_network()

            # Start services
            self.start_hostapd()
            self.start_dnsmasq()
            self.start_flask()

            self.running = True
            logger.info("Hotspot portal is running!")
            logger.info(f"SSID: {self.ssid}")
            logger.info(f"Password: {self.password}")
            logger.info("Connect to the hotspot and open any website to see the portal")

            # Keep running until interrupted
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")

        except Exception as e:
            logger.error(f"Error starting hotspot portal: {e}")
            self.cleanup()
            sys.exit(1)
        finally:
            self.cleanup()

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    logger.info("Received signal, shutting down...")
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
