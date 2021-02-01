# -*- coding: utf-8 -*-
"""
    Copyright (C) 2014-2020 Netflix, Inc.
    Copyright (C) 2021 Stefano Gottardo (python porting)
    DIAL server helper

    SPDX-License-Identifier: BSD-2-Clause
    See LICENSES/BSD-2-Clause-Netflix.md for more information.
"""
import json

import resources.lib.helpers.file_ops as fileops

OPTIONS_RESPONSE = '''\
HTTP/1.1 204 No Content\r
Access-Control-Allow-Methods: {methods}\r
Access-Control-Max-Age: 86400\r
Access-Control-Allow-Origin: {origin}\r
Content-Length: 0\r
\r
'''

STOP_RESPONSE = '''\
HTTP/1.1 200 OK\r
Content-Type: text/plain\r
Access-Control-Allow-Origin: {origin}\r
\r
'''

CREATED_RESPONSE = '''\
HTTP/1.1 201 Created\r
Content-Type: text/plain\r
Location: http://{address}:{dial_port}/apps/{app_name}/run\r
Access-Control-Allow-Origin: {origin}\r
\r
'''

STATUS_RESPONSE = '''\
HTTP/1.1 200 OK\r
Content-Type: text/xml\r
Access-Control-Allow-Origin: {origin}\r
\r
<?xml version="1.0" encoding="UTF-8"?>\r
<service xmlns="urn:dial-multiscreen-org:schemas:dial" dialVer="{dial_version}">\r
  <name>{app_name}</name>\r
  <options allowStop="{can_stop}"/>\r
  <state>{dial_state}</state>\
{link}\r
  <additionalData>{dial_data}</additionalData>\r
</service>\r
\r
'''

RESPONSE_OK = '''\
HTTP/1.1 200 OK\r
Content-Type: text/plain\r
Access-Control-Allow-Origin: {origin}\r
\r
'''


class DialStatus:  # Copy on helpers/utils.py
    STOPPED = 0
    HIDE = 1
    RUNNING = 2
    ERROR_NOT_IMPLEMENTED = 3
    ERROR_FORBIDDEN = 4
    ERROR_UNAUTH = 5
    ERROR = 6


def store_dial_data(app_name, data):
    """Store the DIAL data key/value pairs in to a file"""
    # NOTE: the reference code store the file in the application folder, we save the file in our data folder
    #   perhaps other changes will be needed to allow USE_ADDITIONAL_DATA feature to work
    file_path = 'dial_data/' + app_name + '.json'
    fileops.save_file_def(file_path, json.dumps(data).encode('utf-8'))


def retrieve_dial_data(app_name):
    """Retrieve the DIAL data key/value pairs from a file"""
    # NOTE: the reference code store the file in the application folder, we read the file in our data folder
    #   perhaps other changes will be needed to allow USE_ADDITIONAL_DATA feature to work
    file_path = 'dial_data/' + app_name + '.json'
    if not fileops.file_exists(file_path):
        return {}
    data = fileops.load_file_def(file_path)
    return json.loads(data)
