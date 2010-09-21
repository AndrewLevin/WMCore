"""
_GetElements_

MySQL implementation of WorkQueueElement.GetElements
"""

__all__ = []



import random
import time
from WMCore.Database.DBFormatter import DBFormatter
from WMCore.WorkQueue.Database import States

#TODO: Investigate a move to one sql call (stored procedure) - should be faster
#TODO: Move end processing logic into SQL query

class GetWork(DBFormatter):
    # get elements that match each site resource ordered by priority
    # elements which do not process any data have their input_id set to NULL
    sql = """SELECT we.id, we.wmtask_id, we.subscription_id, wsite.name site_name, 
                    valid, we.num_jobs, we.input_id, we.parent_flag,
                    we.request_name, we.team_name
            FROM wq_element we
            LEFT JOIN  wq_data_site_assoc wbmap ON wbmap.data_id = we.input_id
            LEFT JOIN wq_site wsite ON wbmap.site_id = wsite.id 
            LEFT JOIN wq_element_site_validation wsv ON
                    (we.id = wsv.element_id AND
                     (we.input_id IS NULL OR (wbmap.site_id = wsv.site_id)))
            WHERE we.status = :available AND
                  -- only check team restriction if both db and query restrict
                  (we.team_name IS NULL OR :team IS NULL OR
                                                  we.team_name = :team) AND
                  -- If have input data release to site with that data,
                  -- else can release to any site
                  (wsite.name = :site OR
                          (wsite.name IS NULL AND we.input_id is NULL)) AND
                  -- can release if white listed,
                  -- or not in black list and no white list for subscription
                  (wsv.valid = 1 OR (wsv.valid IS NULL AND we.id NOT IN
                                                 (SELECT DISTINCT element_id 
                                                  FROM wq_element_site_validation
                                                  WHERE valid = 1)))
            ORDER BY (we.priority +
                    :weight * (:current_time - we.insert_time)) DESC
            """

    def execute(self, resources, team, weight, conn = None, transaction = False):
        binds = [{'available' : States['Available'], 'weight' : weight,
                  'team' : team, "site" : site,
                  "current_time": int(time.time())} \
                                    for site, jobs in resources.iteritems() if jobs > 0]
        if not binds:
            return {}, {}
        results = self.dbi.processData(self.sql, binds, conn = conn,
                         transaction = transaction)
        results = self.formatDict(results)
        acquired_ids = []
        acquired = []
        # the sql query will return all matching blocks so loop over them
        # (in priority order) and limit to the job slots at each site.
        # Strip out duplicate elements (which can run at multiple sites.)
        for result in results:
            # Work which requires input data must be assigned to a particular
            # site. If this fails something has gone wrong with the sql call
            assert (result['site_name'] is None) == \
                   (result['input_id'] is None), \
                   'Input data required but not released to a specific site'

            # Production jobs (can run anywhere) are assigned to a random site
            site = result['site_name'] or random.choice(resources.keys())

            # Release work as long as site has resources (even if resources are smaller than work)
            if result['id'] not in acquired_ids and resources.get(site, 0) > 0:
                acquired.append(result)
                acquired_ids.append(result['id'])
                newslots = int(resources[site]) - result['num_jobs']
                if newslots > 0:
                    resources[site] = newslots
                else:
                    del resources[site]
                if not resources:
                    break
        return acquired, resources
