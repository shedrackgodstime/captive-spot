# Active Portal - WiFi Hotspot with Captive Portal

A Python-based WiFi hotspot solution that creates a captive portal for Parrot OS. When devices connect to the hotspot, they are automatically redirected to a beautiful web portal.

## Features

- 🚀 **Easy Setup**: One command to start everything
- 📱 **Mobile Friendly**: Responsive design for all devices
- 🔒 **Secure**: WPA2 encryption for the hotspot
- 🌐 **Captive Portal**: Automatic redirection to web page
- 🎨 **Beautiful UI**: Modern, professional-looking portal pages
- ⚡ **Fast**: Lightweight and efficient
- 🔄 **Auto-Reconnect**: Improved device auto-reconnection support

## Auto-Reconnection Improvements

The hotspot now includes enhanced auto-reconnection support to fix issues where devices don't automatically reconnect when the hotspot comes back online:

### What Was Fixed

1. **DNS Resolution Issues**: Previously redirected ALL DNS queries to the portal, making devices think the network was broken
2. **DHCP Lease Management**: Improved lease persistence and client management
3. **hostapd Configuration**: Enhanced settings for better client reconnection behavior
4. **Device Compatibility**: Better support for Android, iOS, Windows, and Linux devices

### Key Changes

- **Selective DNS Redirection**: Only captive portal detection domains are redirected, allowing real DNS resolution
- **Enhanced DHCP**: Longer lease times (24h) and better persistence
- **Client-Friendly Settings**: Disabled power-saving features that interfere with reconnection
- **Device-Specific Tools**: New troubleshooting script for device-specific issues

### Troubleshooting Auto-Reconnection

```bash
# Run device-specific fixes
python3 fix_device_reconnection.py "MyHotspot" "mypassword"

# Test auto-reconnection
sudo /tmp/test_reconnection.sh

# Diagnose issues
sudo python3 hotspot_portal.py --diagnose
```

## Requirements

### System Requirements
- Parrot OS (or any Debian-based Linux)
- Root privileges (sudo)
- WiFi adapter that supports AP mode
- Internet connection (for initial setup)

### Software Dependencies
- Python 3.7+
- hostapd
- dnsmasq
- iptables

## Installation

### 1. Install System Dependencies

```bash
# Update package list
sudo apt update

# Install required system packages
sudo apt install hostapd dnsmasq iptables python3-pip

# Install Python dependencies
pip3 install -r requirements.txt
```

### 2. Configure Your System

Make sure your WiFi adapter supports AP mode:

```bash
# Check if your WiFi adapter supports AP mode
iw list | grep -A 10 "Supported interface modes"
```

Look for "AP" in the supported modes.

### 3. Prepare Your Network Interface

Identify your WiFi interface:

```bash
# List network interfaces
ip link show

# Or use iwconfig
iwconfig
```

Common interface names are `wlan0`, `wlan1`, etc.

## Usage

### One-Command Setup

```bash
# Run with default settings (fully automated)
sudo python3 hotspot_portal.py

# Default settings:
# SSID: ActivePortal
# Password: portal123
# Interface: wlan0
```

### Debugging and Development

The project now has a modular structure for easier debugging:

```bash
# Test the web application independently
python3 web/test_web_app.py

# Run web app in debug mode (for development)
python3 web/debug_web.py

# Run the full hotspot portal
sudo python3 hotspot_portal.py

# Diagnose auto-reconnection issues
sudo python3 hotspot_portal.py --diagnose
```

### Multi-Interface Support

The hotspot now supports multiple network interfaces without affecting your main internet connection:

```bash
# Choose the right interface for your setup
python3 choose_interface.py

# Use a specific interface for hotspot (keeps other interfaces running)
sudo python3 hotspot_portal.py "MyHotspot" "mypassword123" "wlx00c0ca41387c"
```

### Custom Configuration

```bash
# Custom SSID and password
sudo python3 hotspot_portal.py "MyHotspot" "mypassword123"

# Custom SSID, password, and interface
sudo python3 hotspot_portal.py "MyHotspot" "mypassword123" "wlan1"
```

**That's it!** The script automatically:
- ✅ Stops conflicting services
- ✅ Configures network interfaces
- ✅ Sets up routing and firewall rules
- ✅ Starts the hotspot and captive portal
- ✅ Handles cleanup when stopped

### Command Line Arguments

```bash
python3 hotspot_portal.py [SSID] [PASSWORD] [INTERFACE]
```

- `SSID`: WiFi network name (default: "ActivePortal")
- `PASSWORD`: WiFi password (default: "portal123")
- `INTERFACE`: WiFi interface name (default: "wlan0")

## Project Structure

The project now has a modular architecture for better maintainability:

```
cactive-portal/
├── hotspot_portal.py      # Main hotspot controller
├── web/                   # Web application module
│   ├── __init__.py       # Package initialization
│   ├── web_app.py        # Flask web application
│   ├── test_web_app.py   # Web app testing utility
│   └── debug_web.py      # Debug mode for web development
├── choose_interface.py    # Interface selection utility
├── troubleshoot_connection.py # Connection diagnostics
├── fix_device_reconnection.py # Auto-reconnection troubleshooting
├── requirements.txt      # Python dependencies
├── setup.sh              # Automated setup script
├── test_portal.sh        # Portal testing utilities
├── README.md             # This documentation
└── templates/            # HTML portal pages
    ├── portal.html       # Registration form
    ├── welcome.html      # Welcome page
    └── success.html      # Success confirmation
```

## How It Works

1. **Network Setup**: Creates a WiFi hotspot with WPA2 encryption
2. **DHCP Server**: Assigns IP addresses to connected devices (192.168.4.x)
3. **DNS Redirection**: Redirects all HTTP traffic to the portal
4. **Web Server**: Serves the captive portal pages (modular Flask app)
5. **Internet Access**: Provides internet access after portal interaction

## Portal Pages

The system includes three beautiful portal pages:

1. **Main Portal** (`/`): User registration form
2. **Welcome Page** (`/welcome`): Information about the service
3. **Success Page** (`/success`): Confirmation of connection

## Customization

### Modifying Portal Pages

Edit the HTML templates in the `templates/` directory:

- `portal.html`: Main registration page
- `welcome.html`: Welcome information page
- `success.html`: Success confirmation page

### Changing Network Settings

Modify the network configuration in `hotspot_portal.py`:

```python
# Change IP range
subprocess.run(['ip', 'addr', 'add', '192.168.4.1/24', 'dev', self.interface])

# Change DHCP range in dnsmasq config
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Make sure you're running as root
   sudo python3 hotspot_portal.py
   ```

2. **Interface Not Found**
   ```bash
   # Check available interfaces
   ip link show
   # Use the correct interface name
   sudo python3 hotspot_portal.py "MyHotspot" "password" "wlan1"
   ```

3. **hostapd/dnsmasq Not Found**
   ```bash
   # Install missing packages
   sudo apt install hostapd dnsmasq
   ```

4. **No Internet Access**
   - Check if your main internet interface is `eth0`
   - Modify the iptables rules in the script if using a different interface

5. **Interface Name Issues**
   ```bash
   # Check available interfaces (note: no trailing colons)
   python3 choose_interface.py

   # Use correct interface name without trailing colons
   sudo python3 hotspot_portal.py "MyHotspot" "password123" "wlx00c0ca41387c"

   # Not this (will cause errors):
   sudo python3 hotspot_portal.py "MyHotspot" "password123" "wlx00c0ca41387c:"
   ```

6. **Auto-Reconnection Issues**
   ```bash
   # Fix device auto-reconnection problems
   python3 fix_device_reconnection.py "MyHotspot" "mypassword"

   # Test auto-reconnection
   sudo /tmp/test_reconnection.sh
   ```

7. **Multi-Interface Issues**
   ```bash
   # Check available interfaces
   python3 choose_interface.py
   
   # Monitor connections
   python3 troubleshoot_connection.py wlx00c0ca41387c
   ```
   - Choose an interface that's not currently in use
   - Ensure your main internet connection remains active
   - Check that the hotspot interface supports AP mode

### Debug Mode

Enable debug logging by modifying the script:

```python
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
```

## Security Considerations

- The hotspot uses WPA2 encryption
- All HTTP traffic is redirected to the portal
- HTTPS traffic bypasses the portal (by design)
- Consider implementing HTTPS for the portal in production

## Stopping the Hotspot

Press `Ctrl+C` to stop the hotspot. The script will automatically:

- Stop all services (hostapd, dnsmasq, Flask)
- Clean up iptables rules
- Remove temporary configuration files

## Advanced Configuration

### Custom DNS Servers

Edit the dnsmasq configuration in the script:

```python
config = f"""interface={self.interface}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
server=8.8.8.8
server=1.1.1.1
log-queries
log-dhcp
listen-address=127.0.0.1
listen-address=192.168.4.1
"""
```

### Custom Portal Logic

Modify the Flask routes in `hotspot_portal.py` to implement custom logic:

```python
@self.app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    
    # Add your custom logic here
    # e.g., save to database, send email, etc.
    
    return redirect(url_for('success'))
```

## License

This project is open source and available under the MIT License.

## Contributing

Feel free to submit issues and enhancement requests!

## Support

For issues and questions, please check the troubleshooting section or create an issue in the repository.




