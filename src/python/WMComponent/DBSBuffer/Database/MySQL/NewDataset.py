#!/usr/bin/env python
"""
_NewDataset_

MySQL implementation of DBSBuffer.NewDataset
"""




from WMCore.Database.DBFormatter import DBFormatter

class NewDataset(DBFormatter):
    existsSQL = "SELECT id FROM dbsbuffer_dataset WHERE path = :path FOR UPDATE"
    sql = "INSERT IGNORE INTO dbsbuffer_dataset (path, valid_status) VALUES (:path, valid_status)"

    def execute(self, datasetPath, validStatus,  conn = None, transaction = False):
        binds = {"path": datasetPath, 'valid_status': validStatus}

        result = self.dbi.processData(self.existsSQL, binds, conn = conn,
                                      transaction = transaction)
        result = self.format(result)

        if len(result) == 0:
            self.dbi.processData(self.sql, binds, conn = conn,
                                 transaction = transaction)

        return 
