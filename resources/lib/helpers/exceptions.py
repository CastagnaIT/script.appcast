# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 Stefano Gottardo (script.appcast)
    Exceptions

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
# Exceptions for DATABASE


class DBSQLiteConnectionError(Exception):
    """An error occurred in the database connection"""


class DBSQLiteError(Exception):
    """An error occurred in the database operations"""


class DBMySQLConnectionError(Exception):
    """An error occurred in the database connection"""


class DBMySQLError(Exception):
    """An error occurred in the database operations"""


class DBProfilesMissing(Exception):
    """There are no stored profiles in database"""


class DBRecordNotExistError(Exception):
    """The record do not exist in database"""
