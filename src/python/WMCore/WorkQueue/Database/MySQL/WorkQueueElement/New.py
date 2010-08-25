"""
_New_

MySQL implementation of WorkQueueElement.New
"""

__all__ = []
__revision__ = "$Id: New.py,v 1.11 2010/07/26 13:10:10 swakef Exp $"
__version__ = "$Revision: 1.11 $"

import time
from WMCore.Database.DBFormatter import DBFormatter
from WMCore.WorkQueue.Database import States

class New(DBFormatter):
    sql = """INSERT INTO wq_element (wmtask_id, input_id, num_jobs, priority,
                         parent_flag, status, insert_time,
                         parent_queue_id, update_time, request_name, team_name)
                 VALUES ((SELECT wt.id FROM wq_wmtask wt
                           INNER JOIN wq_wmspec ws ON ws.id = wt.wmspec_id
                          WHERE ws.name = :wmSpecName AND wt.name = :wmTaskName),
                         (SELECT id FROM wq_data WHERE name = :input),
                         :numJobs, :priority, :parentFlag, :available,
                         :insertTime, :parentQueueId, :insertTime,
                         :request_name, :team_name)
          """
    sql_no_input = """INSERT INTO wq_element (wmtask_id, num_jobs, priority,
                         parent_flag, status, insert_time,
                         parent_queue_id, update_time, request_name, team_name)
                 VALUES ((SELECT wt.id FROM wq_wmtask wt
                           INNER JOIN wq_wmspec ws ON ws.id = wt.wmspec_id
                          WHERE ws.name = :wmSpecName AND wt.name = :wmTaskName),
                         :numJobs, :priority, :parentFlag, :available,
                         :insertTime, :parentQueueId,
                         :insertTime, :request_name, :team_name)
          """
    # for the previous version than  MySQL 5.1.12 has different meaning.
    # Check the http://dev.mysql.com/doc/refman/5.1/en/information-functions.html#function_last-insert-id
    # this is not the good way: not sure safe for the race condition even in one transaction
    # Need to define some unique values for the table other than id
    sql_get_id = """SELECT LAST_INSERT_ID()"""
    
    def execute(self, wmSpecName, wmTaskName,  input, numJobs, priority,
                parentFlag, parentQueueId, requestName, teamName,
                conn = None, transaction = False):

        #if input == None:
        #    input = "NoBlock"
        binds = {"wmSpecName" : wmSpecName,
                 "wmTaskName" : wmTaskName,
                 "numJobs" : numJobs, "priority" : priority,
                 "parentFlag" : parentFlag, "insertTime" : int(time.time()),
                 "available" : States['Available'],
                 "parentQueueId" : parentQueueId,
                 "request_name" : requestName,
                 "team_name" : teamName}
        if input:
            sql = self.sql
            binds['input'] = input
        else:
            sql = self.sql_no_input
        self.dbi.processData(sql, binds, conn = conn,
                             transaction = transaction)
        
        result = self.dbi.processData(self.sql_get_id, {}, conn = conn,
                             transaction = transaction)
        id = self.format(result)
        return int(id[0][0])
