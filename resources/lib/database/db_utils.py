# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 Stefano Gottardo (script.appcast)

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
import os

import xbmcvfs

from resources.lib.globals import G


LOCAL_DB_FILENAME = 'database.sqlite3'


def get_local_db_path(db_filename):
    # First ensure database folder exists
    from resources.lib.helpers.file_ops import folder_exists
    db_folder = xbmcvfs.translatePath(os.path.join(G.DATA_PATH, 'database'))
    if not folder_exists(db_folder):
        xbmcvfs.mkdirs(db_folder)
    return os.path.join(db_folder, db_filename)


def sql_filtered_update(table, set_columns, where_columns, values):
    """
    Generates dynamically a sql update query by eliminating the columns that have value to None
    WARNING: RESPECT columns AND values SORT ORDER IN THE LISTS!
    If the values are positioned incorrectly with respect to the column names,
    they will be saved in the wrong column!
    """
    for index in range(len(set_columns) - 1, -1, -1):
        if values[index] is None:
            del set_columns[index]
            del values[index]
    set_columns = [col + ' = ?' for col in set_columns]
    where_columns = [col + ' = ?' for col in where_columns]
    query = 'UPDATE {} SET {} WHERE {}'.format(
        table,
        ', '.join(set_columns),
        ' AND '.join(where_columns)
    )
    return query, values


def sql_filtered_insert(table, set_columns, values):
    """
    Generates dynamically a sql insert query by eliminating the columns that have value to None
    WARNING: RESPECT columns AND values SORT ORDER IN THE LISTS!
    If the values are positioned incorrectly with respect to the column names,
    they will be saved in the wrong column!
    """
    for index in range(len(set_columns) - 1, -1, -1):
        if values[index] is None:
            del set_columns[index]
            del values[index]
    values_fields = ['?'] * len(set_columns)
    query = 'INSERT INTO {} ({}) VALUES ({})'.format(
        table,
        ', '.join(set_columns),
        ', '.join(values_fields)
    )
    return query, values
