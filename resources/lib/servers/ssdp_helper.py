# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014 Netflix, Inc.
    Copyright (C) 2021 Stefano Gottardo (python porting)
    SSDP Server helper

    SPDX-License-Identifier: BSD-2-Clause
    See LICENSES/BSD-2-Clause-Netflix.md for more information.
"""
# IMPORTANT: Make sure to maintain the header structure with exact spaces between header name and value,
#            or some mobile apps may not recognise the values correctly.
# CACHE-CONTROL: max-age Amount of time in seconds that the NOTIFY packet should be cached by clients receiving it
# DATE: the format type is "Sat, 09 Jan 2021 09:27:22 GMT"

# M-SEARCH response let know where is the device descriptor XML
SEARCH_RESPONSE = '''\
HTTP/1.1 200 OK
LOCATION: http://{ip_addr}:{port}/ssdp/device-desc.xml
CACHE-CONTROL: max-age=1800
DATE: {date_timestamp}
EXT: 
BOOTID.UPNP.ORG: {boot_id}
SERVER: Linux/2.6 UPnP/1.1 appcast_ssdp/1.0
ST: urn:dial-multiscreen-org:service:dial:1
USN: uuid:{device_uuid}::urn:dial-multiscreen-org:service:dial:1

'''

# Notify that the service is changed
ADV_UPDATE = '''\
NOTIFY * HTTP/1.1
HOST: {udp_ip_addr}:{udp_port}
CACHE-CONTROL: max-age=1800
NT: urn:dial-multiscreen-org:service:dial:1
NTS: ssdp:alive
LOCATION: http://{ip_addr}:{port}/dd.xml
USN: uuid:{device_uuid}::urn:dial-multiscreen-org:service:dial:1

'''

# Notify that the service is not available
ADV_BYEBYE = '''\
NOTIFY * HTTP/1.1
HOST: {udp_ip_addr}:{udp_port}
NT: urn:dial-multiscreen-org:service:dial:1
NTS: ssdp:byebye
USN: uuid:{device_uuid}::urn:dial-multiscreen-org:service:dial:1

'''

# Device descriptor XML
DD_XML = '''\
HTTP/1.1 200 OK
Content-Type: text/xml
Application-URL: http://{ip_addr}:{dial_port}/apps/

<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:r="urn:restful-tv-org:schemas:upnp-dd">
  <specVersion>
  <major>1</major>
  <minor>0</minor>
  </specVersion>
  <device>
    <deviceType>urn:schemas-upnp-org:device:tvdevice:1</deviceType>
    <friendlyName>{friendly_name}</friendlyName>
    <manufacturer>{manufacturer_name}</manufacturer>
    <modelName>{model_name}</modelName>
    <UDN>uuid:{device_uuid}</UDN>
  </device>
</root>

'''
