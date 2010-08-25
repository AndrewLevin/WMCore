#!/usr/bin/env python
"""
_WorkflowSummary_

List the task name and number of jobs running for a given site and subscription
type.
"""

__revision__ = "$Id: WorkflowSummary.py,v 1.1 2010/08/16 22:23:56 sryu Exp $"
__version__  = "$Revision: 1.1 $"

from WMCore.Database.DBFormatter import DBFormatter
from WMCore.JobStateMachine.Transitions import Transitions

class WorkflowSummary(DBFormatter):
    sql = """SELECT MAX(wmbs_workflow.id) AS id, wmbs_workflow.name AS wmspec, 
                    COUNT(wmbs_workflow.id) AS num_task, 
                    COUNT(wmbs_job.id) AS num_job, 
                    SUM(wmbs_job.outcome) AS success, wmbs_job_state.name AS state 
             FROM wmbs_workflow
               INNER JOIN wmbs_subscription ON
                 wmbs_workflow.id = wmbs_subscription.workflow
               INNER JOIN wmbs_jobgroup ON
                 wmbs_subscription.id = wmbs_jobgroup.subscription
               INNER JOIN wmbs_job ON
                 wmbs_jobgroup.id = wmbs_job.jobgroup
               INNER JOIN wmbs_job_state ON
                 wmbs_job.state = wmbs_job_state.id
            GROUP BY wmbs_workflow.name, wmbs_job_state.name 
            ORDER BY id DESC"""

    def formatWorkflow(self, results):
        workflow = {}
        tran = Transitions()
        for result in results:
            if not workflow.has_key(result["wmspec"]):
                workflow[result["wmspec"]] = {}
                for state in tran.states():
                    workflow[result["wmspec"]][state] = 0
                    
                workflow[result["wmspec"]][result["state"]] = result["num_job"]
                workflow[result["wmspec"]]["num_task"] = result["num_task"]
                workflow[result["wmspec"]]["real_success"] = int(result["success"])
                workflow[result["wmspec"]]["id"] = result["id"]
                workflow[result["wmspec"]]["wmspec"] = result["wmspec"] 
            else:
                workflow[result["wmspec"]][result["state"]] = result["num_job"]
                workflow[result["wmspec"]]["num_task"] += result["num_task"]
                workflow[result["wmspec"]]["real_success"] += int(result["success"])
        
        # need to order by id (client side)        
        return workflow.values()
    
    def execute(self, conn = None, transaction = False):
        results = self.dbi.processData(self.sql,
                                       conn = conn, transaction = transaction)
        return self.formatWorkflow(self.formatDict(results))
