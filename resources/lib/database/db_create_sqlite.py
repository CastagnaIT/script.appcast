# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 Stefano Gottardo (script.appcast)
    Functions to create a new SQLite database

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
import sqlite3 as sql

import resources.lib.database.db_utils as db_utils
from resources.lib.helpers.logging import LOG


def create_database(db_file_path, db_filename):
    LOG.debug('The SQLite database {} is empty, creating tables', db_filename)
    _create_local_database(db_file_path)


def _create_local_database(db_file_path):
    """Create a new local database"""
    conn = sql.connect(db_file_path)
    cur = conn.cursor()

    table = str('CREATE TABLE config ('
                'ID    INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,'
                'Name  TEXT    UNIQUE NOT NULL,'
                'Value TEXT);')
    cur.execute(table)

    if conn:
        conn.close()
