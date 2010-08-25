#!/usr/bin/env python
"""
    WorkQueue.Policy.Start.Block tests
"""

__revision__ = "$Id: Block_t.py,v 1.8 2010/07/14 14:46:38 swakef Exp $"
__version__ = "$Revision: 1.8 $"

import unittest
import shutil
from WMCore.WorkQueue.Policy.Start.Block import Block
#from WMCore.WMSpec.StdSpecs.ReReco import rerecoWorkload
from WMCore_t.WorkQueue_t.WorkQueue_t import TestReRecoFactory, rerecoArgs
from WMCore_t.WMSpec_t.samples.MultiTaskProcessingWorkload import workload as MultiTaskProcessingWorkload
from WMCore_t.WorkQueue_t.MockDBSReader import MockDBSReader

class BlockTestCase(unittest.TestCase):

    splitArgs = dict(SliceType = 'NumberOfFiles', SliceSize = 10)

    def testTier1ReRecoWorkload(self):
        """Tier1 Re-reco workflow"""
        Tier1ReRecoWorkload = TestReRecoFactory()('ReRecoWorkload', rerecoArgs)
        inputDataset = Tier1ReRecoWorkload.taskIterator().next().inputDataset()
        dataset = "/%s/%s/%s" % (inputDataset.primary,
                                     inputDataset.processed,
                                     inputDataset.tier)
        dbs = {inputDataset.dbsurl : MockDBSReader(inputDataset.dbsurl, dataset)}
        for task in Tier1ReRecoWorkload.taskIterator():
            units = Block(**self.splitArgs)(Tier1ReRecoWorkload, task, dbs)
            self.assertEqual(2, len(units))
            blocks = [] # fill with blocks as we get work units for them
            for unit in units:
                self.assertEqual(1, unit['Jobs'])
                self.assertEqual(Tier1ReRecoWorkload, unit['WMSpec'])
                self.assertEqual(task, unit['Task'])
            self.assertEqual(len(units),
                             len(dbs[inputDataset.dbsurl].blocks[dataset]))


    def testMultiTaskProcessingWorkload(self):
        """Multi Task Processing Workflow"""
        datasets = []
        tasks, count = 0, 0
        for task in MultiTaskProcessingWorkload.taskIterator():
            tasks += 1
            inputDataset = task.inputDataset()
            datasets.append("/%s/%s/%s" % (inputDataset.primary,
                                           inputDataset.processed,
                                           inputDataset.tier))
        dbs = {inputDataset.dbsurl : MockDBSReader(inputDataset.dbsurl, *datasets)}
        for task in MultiTaskProcessingWorkload.taskIterator():
            units = Block(**self.splitArgs)(MultiTaskProcessingWorkload, task, dbs)
            self.assertEqual(2, len(units))
            blocks = [] # fill with blocks as we get work units for them
            for unit in units:
                self.assertEqual(1, unit['Jobs'])
                self.assertEqual(MultiTaskProcessingWorkload, unit['WMSpec'])
                self.assertEqual(task, unit['Task'])
            self.assertEqual(len(units),
                             len(dbs[inputDataset.dbsurl].blocks[datasets[0]]))
            count += 1
        self.assertEqual(tasks, count)


if __name__ == '__main__':
    unittest.main()
