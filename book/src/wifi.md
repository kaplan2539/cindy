# Enable WiFi

In this chapter we are connecting CHIP to the Internet using its on-board WiFi.
CHIP comes with a Realtek RTL8723BS that supports WiFi and Bluetooth.
The Realtek RTL8732BS isn't officially supported in mainline Linux yet.
However, a driver is available in the staging area.

## Enable Wifi in the DTS

Luckily, the CHIP DTS in mainline Linux is already setup for WiFi, so nothing
do here.

## Enable Wifi in the Linux config

```
cat <<EOF >"${BR2_EXTERNAL}"/board/nextthingco/CHIP/linux/wifi.cfg
CONFIG_WLAN=y
CONFIG_CFG80211=y
CONFIG_RTL8723BS=m
EOF
```

## Add WiFi packages in Buildroot

The following adds a couple of WiFi related packages and adds the configuration
fragment defined above to our Linux configuration:
```
cat <<EOF >>"${BR2_EXTERNAL}"/configs/nextthingco_chip_defconfig
BR2_PACKAGE_LINUX_FIRMWARE=y
BR2_PACKAGE_LINUX_FIRMWARE_RTL_87XX=y
BR2_PACKAGE_WIRELESS_REGDB=y
BR2_PACKAGE_WIRELESS_TOOLS=y
BR2_PACKAGE_DHCPCD=y
BR2_PACKAGE_WPA_SUPPLICANT=y
BR2_PACKAGE_WPA_SUPPLICANT_NL80211=y
BR2_PACKAGE_WPA_SUPPLICANT_WPA3=y
BR2_PACKAGE_WPA_SUPPLICANT_PASSPHRASE=y
BR2_PACKAGE_UTIL_LINUX_RFKILL=y
EOF

sed -i -e 's%\(BR2_LINUX_KERNEL_CONFIG_FRAGMENT_FILES\)=.*%\1="\${BR2_EXTERNAL}/board/nextthingco/CHIP/linux/nand.cfg \${BR2_EXTERNAL}/board/nextthingco/CHIP/linux/wifi.cfg"%' "${BR2_EXTERNAL}"/configs/nextthingco_chip_defconfig
```

## 2024-02-19:
- `modprobe r8723bs` crashes without stuff in /lib/firmware
- copied `/lib/firmware` from MacroMorgans Debian into `buildroot-2023.10/build/target/lib/firmware`
  - regulartory.db still doesn't seem to load
  - BUT: `modprobe r8723bs` no longer crashes and there is a wifi0 device:
```
# ip addr
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
2: sit0@NONE: <NOARP> mtu 1480 qdisc noop qlen 1000
    link/sit 0.0.0.0 brd 0.0.0.0
3: wlan0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq qlen 1000
    link/ether 7c:c7:09:0f:f0:fe brd ff:ff:ff:ff:ff:ff
```

- Now, connmanctl says wifi is not available?
- TODO: install lower-level missing tools:
    - rfkill
    - dhclient
    - iwconfig
    - wpa_password (we already have wpa_supplicant, but without wpa_password cannot create a config file c.f.
      https://www.linuxbabe.com/command-line/ubuntu-server-16-04-wifi-wpa-supplicant)


### Connect to WIFI
```
modprobe r8723bs
wpa_passphrase ESSID passphrase > /etc/wpa_supplicant.conf
wpa_supplicant -c /etc/wpa_supplicant.conf -i wlan0
```

Change contents of `/etc/network/interfaces` to:
```
auto lo
iface lo inet loopback

auto wlan0
iface wlan0 inet dhcp
```

Obtain IP address via dhcp and setup routing:
```
ifup wlan0
```
 
