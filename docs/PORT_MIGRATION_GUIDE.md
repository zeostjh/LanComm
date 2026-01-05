# Port Migration Guide
**Last Updated**: January 5, 2026

## Important: Port Changes

LanComm now uses port 6001 for both control and audio (matching industry standard HelixNet systems).

**Old setup**: TCP port 5000 for control, UDP port 5001 for audio  
**New setup**: TCP port 6001 for control, UDP port 6001 for audio

Both ports must be changed together - the old and new versions won't talk to each other.

## What You Need to Do

### 1. Update Your Firewall

**On Windows** (run PowerShell as Administrator):
```powershell
# Remove old rules if they exist
netsh advfirewall firewall delete rule name="LanComm TCP" protocol=TCP localport=5000
netsh advfirewall firewall delete rule name="LanComm UDP" protocol=UDP localport=5001

# Add new rules for port 6001
netsh advfirewall firewall add rule name="LanComm Server" dir=in action=allow protocol=TCP localport=6001
netsh advfirewall firewall add rule name="LanComm Audio" dir=in action=allow protocol=UDP localport=6001
```

**On Linux**:
```bash
# Remove old rules
sudo iptables -D INPUT -p tcp --dport 5000 -j ACCEPT
sudo iptables -D INPUT -p udp --dport 5001 -j ACCEPT

# Add new rules
sudo iptables -A INPUT -p tcp --dport 6001 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 6001 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

### 2. Update Network Equipment

If you have port forwarding or network ACLs configured:

- Change any port forwards from 5000→6001 (TCP) and 5001→6001 (UDP)
- Update VLAN or subnet ACLs that reference the old ports
- Update your network documentation

### 3. Restart Everything

**Critical**: All servers and beltpacks must be updated at the same time.

```powershell
# Stop everything running the old version
# Update the code (git pull or replace files)
# Start the server
python server.py

# Start the beltpacks
python beltpack.py
```

Mixing old and new versions won't work - they use different ports.

## Troubleshooting

### "Connection refused" on beltpack
**Problem**: Beltpack is trying port 6001 but server is still on port 5000.
**Solution**: Update and restart the server.

### "No route to host"
**Problem**: Firewall is blocking port 6001.
**Solution**: Run the firewall commands above.

### "mDNS not working"
**Problem**: Beltpack shows "mDNS discovery timeout, using fallback".
**Solution**: 
1. Enable "Network Discovery" in Windows network settings
2. Allow UDP port 5353 in firewall
3. Or just set SERVER_HOST manually in beltpack.py (line 97)
## Verify Everything Works

After migrating, check:

- [ ] Server starts without errors
- [ ] Beltpack connects within 10 seconds
- [ ] Authentication works
- [ ] Audio transmits between users
- [ ] Firewall allows port 6001 TCP and UDP
- [ ] No port conflicts with other services

## If You Need to Go Back

To revert to the old ports:

1. **server.py** (line 28-29):
   ```python
   TCP_PORT = 5000
   UDP_PORT = 5001
   ```

2. **beltpack.py** (line 97-98):
   ```python
   TCP_PORT = 5000
   UDP_PORT = 5001
   ```

3. Restore old firewall rules
4. Restart everything

## Why This Change?

We switched to port 6001 to match ClearCom HelixNet, which is the industry standard for IP intercom systems. Benefits:

1. Simpler - one port instead of two
2. Better compatibility with HelixNet monitoring tools
3. Network admins recognize port 6001 as intercom traffic
4. Industry best practice
