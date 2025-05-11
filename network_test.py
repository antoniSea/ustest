#!/usr/bin/env python3
"""
Network test script to verify if port 5001 is accessible
and if there are any firewall or network issues.
"""

import socket
import sys
import subprocess
import platform
import logging
import argparse
import time
from concurrent.futures import ThreadPoolExecutor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_port(ip, port, timeout=2):
    """Check if a port is open on a given IP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking {ip}:{port} - {str(e)}")
        return False

def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't need to be reachable
        s.connect(('8.8.8.8', 1))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.error(f"Could not determine local IP: {str(e)}")
        return socket.gethostbyname(socket.gethostname())

def run_command(command):
    """Run a shell command and return the output."""
    try:
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )
        stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode
    except Exception as e:
        logger.error(f"Error running command '{command}': {str(e)}")
        return "", str(e), -1

def check_firewall_status():
    """Check the status of the firewall on various platforms."""
    system = platform.system().lower()
    
    if system == 'linux':
        # Check for common Linux firewalls
        logger.info("Checking Linux firewall status...")
        
        # Check iptables
        stdout, stderr, _ = run_command("iptables -L -n | grep 5001")
        if stdout:
            logger.info(f"iptables has rules for port 5001: {stdout.strip()}")
        else:
            logger.info("No specific iptables rules found for port 5001")
        
        # Check UFW if installed
        stdout, stderr, _ = run_command("which ufw && ufw status")
        if "not found" not in stderr and stdout:
            logger.info(f"UFW status: {stdout.strip()}")
        
        # Check firewalld if installed
        stdout, stderr, _ = run_command("which firewall-cmd && firewall-cmd --list-all")
        if "not found" not in stderr and stdout:
            logger.info(f"firewalld status: {stdout.strip()}")
            
    elif system == 'darwin':  # macOS
        logger.info("Checking macOS firewall status...")
        stdout, stderr, _ = run_command("/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate")
        if stdout:
            logger.info(f"macOS firewall status: {stdout.strip()}")
            
    elif system == 'windows':
        logger.info("Checking Windows firewall status...")
        stdout, stderr, _ = run_command("netsh advfirewall show allprofiles state")
        if stdout:
            logger.info(f"Windows firewall status: {stdout.strip()}")
    
    # Generic netstat check for all platforms
    logger.info("Checking if port 5001 is listening...")
    if system in ('linux', 'darwin'):
        stdout, stderr, _ = run_command("netstat -tuln | grep 5001")
    else:  # Windows
        stdout, stderr, _ = run_command("netstat -an | findstr 5001")
        
    if stdout:
        logger.info(f"Port 5001 is listening: {stdout.strip()}")
    else:
        logger.warning("Port 5001 does not appear to be listening!")

def scan_network_for_port(base_ip, port, count=20):
    """Scan the local network to find devices with the given port open."""
    # Extract the base of the IP (assuming it's a /24 network)
    ip_parts = base_ip.split('.')
    base = '.'.join(ip_parts[0:3]) + '.'
    
    logger.info(f"Scanning network {base}0/24 for open port {port}...")
    
    def check_ip(i):
        ip = f"{base}{i}"
        if check_port(ip, port):
            return ip
        return None
    
    # Use threads to speed up scanning
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(check_ip, range(1, count+1)))
    
    # Filter out None results
    open_ips = [ip for ip in results if ip]
    
    if open_ips:
        logger.info(f"Found {len(open_ips)} devices with port {port} open: {', '.join(open_ips)}")
    else:
        logger.info(f"No devices found with port {port} open in the first {count} IPs of the network")
    
    return open_ips

def test_flask_app(server_ip, port=5001, path='/'):
    """Test if a Flask app is responding on the given IP and port."""
    try:
        import requests
        url = f"http://{server_ip}:{port}{path}"
        logger.info(f"Testing Flask app at {url}...")
        
        response = requests.get(url, timeout=5)
        
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        
        if response.status_code == 200:
            logger.info("Flask app is responding correctly!")
            return True
        else:
            logger.warning(f"Flask app responded with status code {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection refused to {server_ip}:{port}. The server might not be running or the port is blocked.")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"Connection to {server_ip}:{port} timed out. The server might be slow or unresponsive.")
        return False
    except Exception as e:
        logger.error(f"Error testing Flask app: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Network test for Flask application")
    parser.add_argument("--ip", help="Server IP to test", default=None)
    parser.add_argument("--port", type=int, help="Port to test", default=5001)
    parser.add_argument("--scan", action="store_true", help="Scan network for open ports")
    args = parser.parse_args()
    
    logger.info(f"Starting network test for Flask application on port {args.port}")
    local_ip = get_local_ip()
    logger.info(f"Local IP: {local_ip}")
    
    # Check firewall status
    check_firewall_status()
    
    # Test loopback connection
    logger.info("Testing loopback connection (127.0.0.1)...")
    if check_port('127.0.0.1', args.port):
        logger.info(f"Port {args.port} is OPEN on loopback (127.0.0.1)")
        test_flask_app('127.0.0.1', args.port)
    else:
        logger.warning(f"Port {args.port} is CLOSED on loopback (127.0.0.1). Is the Flask app running?")
    
    # Test local IP
    logger.info(f"Testing local IP connection ({local_ip})...")
    if check_port(local_ip, args.port):
        logger.info(f"Port {args.port} is OPEN on local IP ({local_ip})")
        test_flask_app(local_ip, args.port)
    else:
        logger.warning(f"Port {args.port} is CLOSED on local IP ({local_ip}).")
    
    # Test specific IP if provided
    if args.ip:
        logger.info(f"Testing connection to specified IP ({args.ip})...")
        if check_port(args.ip, args.port):
            logger.info(f"Port {args.port} is OPEN on {args.ip}")
            test_flask_app(args.ip, args.port)
        else:
            logger.warning(f"Port {args.port} is CLOSED on {args.ip}.")
    
    # Scan network if requested
    if args.scan:
        scan_network_for_port(local_ip, args.port)
    
    logger.info("Network test completed.")

if __name__ == "__main__":
    main() 