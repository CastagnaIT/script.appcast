# -*- coding: utf-8 -*-
"""
    Copyright (C) 2021 Stefano Gottardo (script.appcast)
    Local database access and functions

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
import resources.lib.database.db_base_sqlite as db_sqlite
import resources.lib.database.db_utils as db_utils
from resources.lib.helpers import file_ops


class NFLocalDatabase(db_sqlite.SQLiteDatabase):
    def __init__(self):
        super().__init__(db_utils.LOCAL_DB_FILENAME)

    def reset_database(self):
        """Delete the entire database and recreate it from scratch"""
        if file_ops.file_exists(self.db_file_path):
            file_ops.delete_file(self.db_file_path)
        self.initialize_connection()
