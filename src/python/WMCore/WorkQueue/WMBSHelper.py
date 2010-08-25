#!/usr/bin/env python
"""
_WMBSHelper_

Use WMSpecParser to extract information for creating workflow, fileset, and subscription
"""

__revision__ = "$Id: WMBSHelper.py,v 1.32 2010/06/18 15:12:53 swakef Exp $"
__version__ = "$Revision: 1.32 $"

import logging

from WMCore.WMBS.File import File
from WMCore.WMBS.Workflow import Workflow
from WMCore.WMBS.Fileset import Fileset
from WMCore.WMBS.Subscription import Subscription
from WMCore.Services.UUID import makeUUID
from WMCore.DataStructs.Run import Run
from WMComponent.DBSBuffer.Database.Interface.DBSBufferFile import DBSBufferFile

def wmbsSubscriptionStatus(logger, dbi, conn, transaction):
    """Function to return status of wmbs subscriptions
    """
    from WMCore.DAOFactory import DAOFactory
    action = DAOFactory(package = 'WMBS',
                        logger = logger,
                        dbinterface = dbi)('Monitoring.SubscriptionStatus')
    return action.execute(conn = conn,
                          transaction = transaction)


class WMBSHelper:

    def __init__(self, wmSpec, wmSpecUrl, wmSpecOwner, taskName, 
                 taskType, whitelist, blacklist, blockName):
        #TODO: 
        # 1. get the top level task.
        # 2. get the top level step and input
        # 3. generated the spec, owner, name from task
        # 4. get input file list from top level step
        # 5. generate the file set from work flow.
       	self.wmSpecName = wmSpec.name()
        self.wmSpecUrl = wmSpecUrl
        self.wmSpecOwner = wmSpecOwner
        self.topLevelTaskName = taskName
        self.topLevelTaskType = taskType
        self.whitelist = whitelist
        self.blacklist = blacklist
        self.block = blockName or None
        self.topLevelFileset = None
        self.topLevelSubscription = None    
        self.topLevelTask = wmSpec.getTask(self.topLevelTaskName)

    def createSubscription(self, topLevelFilesetName = None):
        self.createTopLevelFileset(topLevelFilesetName)
        return self._createChildSubscription(self.topLevelTask, self.topLevelFileset)
        
    def _createChildSubscription(self, task, fileset):
        # create workflow
        # make up workflow name from wmspec name
        workflow = Workflow(self.wmSpecUrl, self.wmSpecOwner, 
                                 self.wmSpecName,
                                 task.getPathName())
        workflow.create()
        subs = Subscription(fileset = fileset, workflow = workflow,
                            split_algo = task.jobSplittingAlgorithm(),
                            type = task.taskType())
        subs.create()
        
        if self.topLevelSubscription == None:
            self.topLevelSubscription = subs
            logging.info("Top level subscription created: %s" % subs['id'])
        else:
            logging.info("Child subscription created: %s" % subs['id'])
        
        # To do: check this is the right change
        #outputModules =  task.getOutputModulesForStep(task.getTopStepName())
        outputModules = task.getOutputModulesForTask()
        for outputModule in outputModules:
            for outputModuleName in outputModule.listSections_():
                if task.taskType() == "Merge":
                    outputFilesetName = "%s/merged-%s" % (task.getPathName(),
                                                          outputModuleName)
                else:
                    outputFilesetName = "%s/unmerged-%s" % (task.getPathName(),
                                                            outputModuleName)
        
                outputFileset = Fileset(name = outputFilesetName)
                outputFileset.create()
                # this will reopen child fileset every time 
                # the fileset exist already 
                outputFileset.markOpen(True)
                workflow.addOutput(outputModuleName, outputFileset)
        
                for childTask in task.childTaskIterator():
                    if childTask.data.input.outputModule == outputModuleName:
                        self._createChildSubscription(childTask, outputFileset) 
            
        return self.topLevelSubscription

    def createTopLevelFileset(self, topLevelFilesetName = None):
        """
        _createTopLevelFileset_

        Create the top level fileset for the workflow.  If the name of the top
        level fileset is not given create one.
        """
        if topLevelFilesetName == None:
            filesetName = ("%s-%s" % (self.wmSpecName, self.topLevelTaskName))
            if self.block:
                filesetName += "-%s" % self.block
            else:
                #create empty fileset for production job
                filesetName += "-%s" % makeUUID()
        else:
            filesetName = topLevelFilesetName
            
        self.topLevelFileset = Fileset(filesetName)
        self.topLevelFileset.create()
        return

    def addMCFakeFile(self):
        mcFakeFileName = "MCFakeFile-%s" % makeUUID()
        wmbsFile = File(lfn = mcFakeFileName,
                        size = 0,
                        events = 0,
                        checksums = 0
                        )
        
        self.topLevelFileset.addFile(wmbsFile)
        self.topLevelFileset.commit()
        self.topLevelFileset.markOpen(False)
    
    def addFiles(self, dbsBlock):
        """
        _createFiles_
        
        create wmbs files from given dbs block.
        as well as run lumi update
        """

        for dbsFile in dbsBlock['Files']:
            self.topLevelFileset.addFile(self._convertDBSFileToWMBSFile(dbsFile, 
                                              dbsBlock['StorageElements']))
                    
        self.topLevelFileset.commit()
        self.topLevelFileset.markOpen(False)
        
        #add to DBSBuffer
        
    def _addToDBSBuffer(self, dbsFile, checksums, locations):
        """
        This step is just for increase the performance for 
        Accountant doesn't neccessary to check the parentage
        """
        dbsBuffer = DBSBufferFile(lfn = dbsFile["LogicalFileName"], 
                                  size = dbsFile["FileSize"],
                                  events = dbsFile["NumberOfEvents"], 
                                  checksums = checksums,
                                  locations = locations, 
                                  status = "AlreadyInDBS")
        dbsBuffer.setDatasetPath('bogus')
        dbsBuffer.setAlgorithm(appName = "cmsRun", appVer = "Unknown", 
                             appFam = "Unknown", psetHash = "Unknown", 
                             configContent = "Unknown")
        dbsBuffer.create()
    
    def _convertDBSFileToWMBSFile(self, dbsFile, storageElements):
        """
        There are two assumptions made to make this method behave properly,
        1. DBS returns only one level of ParentList.
           If DBS returns multiple level of parentage, it will be still get handled.
           However that might not be what we wanted. In that case, restrict to one level.
        2. Assumes parents files are in the same location as child files.
           This is not True in general case, but workquue should only select work only
           where child and parent files are in the same location  
        """
        wmbsParents = []
        
        for parent in dbsFile["ParentList"]:
            wmbsParents.append(self._convertDBSFileToWMBSFile(parent, storageElements))
        
        checksums = {}
        if dbsFile.get('Checksum'):
            checksums['cksum'] = dbsFile['Checksum']
        if dbsFile.get('Adler32'):
            checksums['adler32'] = dbsFile['Adler32']
            
        wmbsFile = File(lfn = dbsFile["LogicalFileName"],
                        size = dbsFile["FileSize"],
                        events = dbsFile["NumberOfEvents"],
                        checksums = checksums,
                        #TODO: need to get list of parent lfn
                        parents = wmbsParents,
                        locations = set(storageElements))
        
        for lumi in dbsFile['LumiList']:
            run = Run(lumi['RunNumber'], lumi['LumiSectionNumber']) 
            wmbsFile.addRun(run)
        
        self._addToDBSBuffer(dbsFile, checksums, storageElements)
            
        logging.info("WMBS File: %s\n on Location: %s" 
                     % (wmbsFile['lfn'], wmbsFile['newlocations']))
        return wmbsFile
        
        
    def _convertDBSFileToDBSBufferFile(self, dbsFile):
        """
        There are two assumptions made to make this method behave properly,
        1. DBS returns only one level of ParentList.
           If DBS returns multiple level of parentage, it will be still get handled.
           However that might not be what we wanted. In that case, restrict to one level.
        2. Assumes parents files are in the same location as child files.
           This is not True in general case, but workquue should only select work only
           where child and parent files are in the same location  
        """
        wmbsParents = []
        
        for parent in dbsFile["ParentList"]:
            wmbsParents.append(self._convertDBSFileToWMBSFile(parent, storageElements))
        
        checksums = {}
        if dbsFile.get('Checksum'):
            checksums['cksum'] = dbsFile['Checksum']
        if dbsFile.get('Adler32'):
            checksums['adler32'] = dbsFile['Adler32']
            
        wmbsFile = File(lfn = dbsFile["LogicalFileName"],
                        size = dbsFile["FileSize"],
                        events = dbsFile["NumberOfEvents"],
                        checksums = checksums,
                        #TODO: need to get list of parent lfn
                        parents = wmbsParents,
                        locations = set(storageElements))
        
        for lumi in dbsFile['LumiList']:
            run = Run(lumi['RunNumber'], lumi['LumiSectionNumber']) 
            wmbsFile.addRun(run)
            
        logging.info("WMBS File: %s\n on Location: %s" 
                     % (wmbsFile['lfn'], wmbsFile['newlocations']))
        return wmbsFile
        

