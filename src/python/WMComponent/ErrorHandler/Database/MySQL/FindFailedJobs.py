#!/usr/bin/env python
#pylint: disable-msg=E1103

"""
_FindFailedCreates_

This module implements the mysql backend for the 
errorhandler, for locating the failed job after they were run
basically in JobFailed status

"""


    "$Id: FindFailedJobs.py,v 1.2 2010/08/18 15:38:24 meloam Exp $"

    "$Revision: 1.2 $"

    "anzar@fnal.gov"

import threading

from WMCore.Database.DBFormatter import DBFormatter

class FindFailedJobs(FindFailed):
    """
    This module implements the mysql backend for the 
    create job error handler.
    
    """

    def execute(self, conn=None, transaction = False):
	jobStatus = 'jobfailed'
	result FindFailed.execute(self.sql, binds,
                         conn = conn, transaction = transaction)

