# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014 Netflix, Inc.
    Copyright (C) 2021 Stefano Gottardo (python porting)
    DIAL Service Discovery (UPnP SSDP protocol)

    SPDX-License-Identifier: BSD-2-Clause
    See LICENSES/BSD-2-Clause-Netflix.md for more information.
"""
import socket
from email.utils import formatdate
from socketserver import DatagramRequestHandler, ThreadingUDPServer

import resources.lib.servers.ssdp_helper as ssdp_msgs
from resources.lib.globals import G
from resources.lib.helpers import kodi_ops
from resources.lib.helpers import utils
from resources.lib.helpers.logging import GetLogger, LOG

# LOGGER = GetLogger('SSDP-Server', LOG.TYPE_SSDP_SERVER)
LOGGER_UDP = GetLogger('SSDP-UDP-Server', LOG.TYPE_SSDP_SERVER)


# This server return only the device descriptor xml, in order to save resources this has been moved to dial server.
#   the code has been preserved by reference to the original source code
# class SSDPServer(ThreadingMixIn, HTTPServer):
#     """SSDP HTTP Server"""
#     # Mixin to handle multiple requests in separate threads
#     # NOTE: if shared variables are used, they must be protected with Lock
#
#
# # pylint: disable=invalid-name
# class SPHttpRequestHandler(BaseHTTPRequestHandler):
#     """Handles SSDP HTTP requests"""
#
#     def do_GET(self):
#         LOGGER.debug('Received GET request {} {}', self.path, self.client_address)
#         parsed_url = urlparse(self.path)
#         if parsed_url.path == '/dd.xml':
#             data = ssdp_msgs.DD_XML.format(
#                 ip_addr=kodi_ops.get_local_ip(),
#                 dial_port=G.DIAL_SERVER_PORT,
#                 friendly_name=G.SP_FRIENDLY_NAME,
#                 manufacturer_name=G.SP_MANUFACTURER_NAME,
#                 model_name=G.SP_MODEL_NAME,
#                 device_uuid=G.DEVICE_UUID
#             )
#             self.wfile.write(utils.fix_return_chars(data).encode('utf-8'))
#         else:
#             self.send_response(404, 'Not Found')
#             self.end_headers()
#
#     def log_message(self, *args):  # pylint: disable=arguments-differ
#         """Override method to disable the BaseHTTPServer Log"""


class SSDPUDPServer(ThreadingUDPServer):
    """SSDP UDP Broadcast Server"""
    def __init__(self):
        super().__init__(('', G.SSDP_UPNP_PORT), SSDPUDPHandler)

    def server_bind(self):
        try:  # Allow multiple sockets to use the same port
            if hasattr(socket, "SO_REUSEADDR"):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception as exc:
            LOGGER_UDP.error('Set socket option SO_REUSEADDR error: {}', exc)
        self.socket.bind(('0.0.0.0', G.SSDP_UPNP_PORT))
        self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                               socket.inet_aton(G.SSDP_BROADCAST_ADDR) + socket.inet_aton(kodi_ops.get_local_ip()))
        # Alternative, but sometimes happen that not receive anymore messages (at least on Windows)
        # self.server_bind()
        # group = socket.inet_aton(G.SSDP_BROADCAST_ADDR)
        # mreq = struct.pack('=4sl', group, socket.INADDR_ANY)
        # self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    def server_close(self):
        # We notify the clients
        send_advertisement(ssdp_msgs.ADV_BYEBYE)


class SSDPUDPHandler(DatagramRequestHandler):
    """Handles SSDP UDP datagram requests"""
    def handle(self):
        try:
            request_data = self.rfile.read()
            # LOGGER.debug('Received message from address: {}; Data:\n{}', self.client_address, request_data)
            # Todo: check MX value and wait until about half of timeout, and ignore all others same requests
            if request_data.startswith(b'M-SEARCH') and b'urn:dial-multiscreen-org:service:dial:1' in request_data:
                LOGGER_UDP.debug('Received [M-SEARCH] message from address: {}; Data:\n{}',
                                 self.client_address, request_data)
                # Build the M-SEARCH response message
                response_data = ssdp_msgs.SEARCH_RESPONSE.format(
                    ip_addr=kodi_ops.get_local_ip(),
                    port=G.DIAL_SERVER_PORT,  # G.SSDP_SERVER_PORT,
                    date_timestamp=formatdate(timeval=None, localtime=False, usegmt=True),
                    device_uuid=G.DEVICE_UUID,
                    boot_id=G.sp_upnp_boot_id
                )
                # Send reply to the client
                LOGGER_UDP.debug('Sending reply message to {}; Data:\n{}', self.client_address, response_data)
                self.wfile.write(utils.fix_return_chars(response_data).encode('ascii'))
                # G.sp_upnp_boot_id += 1
        except Exception as exc:
            LOGGER_UDP.error('An error occurred while processing the request\nError: {}\nAddress: {}',
                             exc, self.client_address)


def send_advertisement(message):
    """Broadcast SSDP message"""
    # NOTICE: These messages are not handled by all mobile apps,
    #         some apps handle server status changes "themselves" and other apps wait these messages,
    #         all standard UPnP header fields seem not required
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            try:  # Allow multiple sockets to use the same port
                if hasattr(socket, "SO_REUSEADDR"):
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except Exception as exc:
                LOGGER_UDP.error('Set socket option SO_REUSEADDR error: {}', exc)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
            sock.settimeout(3)
            sock.connect((G.SSDP_BROADCAST_ADDR, G.SSDP_UPNP_PORT))
            # Fill the key parameters of the message
            # (we add all the keys for all types of messages, only those needed for the message will be taken)
            data = message.format_map(utils.FormatMapSubCls(
                udp_ip_addr=G.SSDP_BROADCAST_ADDR,
                udp_port=G.SSDP_UPNP_PORT,
                ip_addr=kodi_ops.get_local_ip(),
                port=G.DIAL_SERVER_PORT,  # G.SSDP_SERVER_PORT,
                device_uuid=G.DEVICE_UUID
            ))
            sock.sendall(utils.fix_return_chars(data).encode('ascii'))
            LOGGER_UDP.debug('Sent advertisement message with data:\n{}', data)
    except socket.timeout as exc:
        LOGGER_UDP.error('Socket timeout error on send advertisement message')
        LOGGER_UDP.debug('Error: {}\nOn sending data:\n{}', exc, message)
    except socket.error as exc:
        LOGGER_UDP.error('Socket error on send advertisement message')
        LOGGER_UDP.debug('Error: {}\nOn sending data:\n{}', exc, message)
    except Exception as exc:
        LOGGER_UDP.error('Error: {}\nOn sending data:\n{}', exc, message)
