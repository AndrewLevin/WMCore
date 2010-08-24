#!/usr/bin/env python
#Turn off to many arguments
#pylint: disable-msg=R0913
#Turn off over riding built in id 
#pylint: disable-msg=W0622
"""
_Fileset_

A simple object representing a Fileset in WMBS.

A fileset is a collection of files for processing. This could be a 
complete block, a block in transfer, some user defined dataset etc.

workflow + fileset = subscription

"""

__revision__ = "$Id: Fileset.py,v 1.28 2008/10/29 09:24:53 metson Exp $"
__version__ = "$Revision: 1.28 $"

from sets import Set
from sqlalchemy.exceptions import IntegrityError

from WMCore.WMBS.File import File
from WMCore.WMBS.BusinessObject import BusinessObject
from WMCore.DataStructs.Fileset import Fileset as WMFileset
from WMCore.Database.Transaction import Transaction

class Fileset(BusinessObject, WMFileset):
    """
    A simple object representing a Fileset in WMBS.

    A fileset is a collection of files for processing. This could be a 
    complete block, a block in transfer, some user defined dataset, a 
    many file lumi-section etc.
    
    workflow + fileset = subscription
    
    """
    def __init__(self, name=None, id=-1, is_open=True, files=Set(), 
                 parents=Set(), parents_open=True, source=None, sourceUrl=None,
                 logger=None, dbfactory = None):
        # Set up the object
        WMFileset.__init__(self, name = name, files=files)
        # Set up all the surrounding WMBS stuff, logger, database etc
        BusinessObject.__init__(self, logger=logger, dbfactory=dbfactory)
        
        # Create a new fileset
        self.id = id
        self.open = is_open
        self.parents = parents
        self.setParentage(parents, parents_open)
        self.source = source
        self.sourceUrl = sourceUrl 
        self.lastUpdate = 0
    
    def addFile(self, file):
        """
        Add the file object to the set, but don't commit to the database
        Call commit() to do that - enables bulk operations
        """
        WMFileset.addFile(self, file)
    
    def setParentage(self, parents, parents_open):
        """
        Set parentage for this fileset - set parents to closed
        """
        if parents:
            for parent in parents:
                if isinstance(parent, Fileset):
                    self.parents.add(parent)
                else:
                    self.parents.add(Fileset(name=parent, 
                                             db_factory=self.dbfactory, 
                                             is_open=parents_open, 
                                             parents_open=False))
    
    def exists(self):
        """
        Does a fileset exist with this name in the database
        """
        return self.daofactory(classname='Fileset.Exists').execute(self.name)
        
    def create(self):
        """
        Add the new fileset to WMBS, and commit the files
        """
        self.daofactory(classname='Fileset.New').execute(self.name)
        self.commit()
        return self
    
    def delete(self):
        """
        Remove this fileset from WMBS
        """
        self.logger.warning(
                        'you are removing the following fileset from WMBS %s %s'
                         % (self.name))
        
        action = self.daofactory(classname='Fileset.Delete')
        return action.execute(name=self.name)
    
    def populate(self, method='Fileset.LoadFromName'): #, parentageLevel=0):
        """
        Load up the files in the file set from the database, this drops new 
        files that aren't in the database. If you want to keep them call commit,
        which will then populate the fileset for you.
        """
        action = self.daofactory(classname=method)    
        values = None
        #get my details
        if method == 'Fileset.LoadFromName':
            values = action.execute(fileset=self.name)
            self.id, self.open, self.lastUpdate = values
        elif method == 'Fileset.LoadFromID':
            values = action.execute(fileset=self.id)
            self.name, self.open, self.lastUpdate = values
        else:
            raise TypeError, 'Chosen populate method not supported'
        
        
        self.newfiles = Set()
        self.files = Set()
        action = self.daofactory(classname='Files.InFileset')
        values = action.execute(fileset=self.name)
        
        for v in values:
            file = File(id=v[0], logger=self.logger, dbfactory=self.dbfactory)
            file.load()
            self.files.add(file)

        return self
    
    def commit(self):
        """
        Add contents of self.newfiles to the database, 
        empty self.newfiles, reload self
        """
        if not self.exists():
            self.create()
        lfns = []
        
        trans = Transaction(dbinterface = self.dbfactory.connect())
        try:
            while len(self.newfiles) > 0:
                #Check file objects exist in the database, save those that don't
                f = self.newfiles.pop()
                self.logger.debug ( "commiting : %s" % f.dict["lfn"] )  
                try:
                    f.save(trans)
                except IntegrityError:
                    self.logger.warning(
                                'File already exists in the database %s' 
                                % f.dict["lfn"])
                lfns.append(f.dict["lfn"])
            
            self.daofactory(classname='Files.AddToFileset').execute(file=lfns, 
                                                           fileset=self.name,
                                                           conn = trans.conn, 
                                                           transaction = True)
            trans.commit()
        except Exception, e:
            trans.rollback()
            raise e
        self.populate()