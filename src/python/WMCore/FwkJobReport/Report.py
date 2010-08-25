#!/usr/bin/env python
"""
_Report_

Framework job report object.
"""

__version__ = "$Revision: 1.26 $"
__revision__ = "$Id: Report.py,v 1.26 2010/06/11 21:44:35 sfoulkes Exp $"

import cPickle
import logging
import sys
import traceback

from WMCore.Configuration import ConfigSection

from WMCore.DataStructs.File import File
from WMCore.DataStructs.Run import Run

from WMCore.FwkJobReport.FileInfo import FileInfo

def checkFileForCompletion(file):
    """
    _checkFileForCompletion_

    Takes a DataStucts/File object (or derivative) and checks to see that the
    file is ready for transfer.
    """
    return True
    if file['lfn'] == "" or file['size'] == 0 or file['events'] == 0:
        return False

    return True

def addBranchNamesToFile(fileSection, branchNames):
    """
    _addBranchNamesToFile_

    Given a list of branch names add them to the file section in the FWJR.
    """
    setattr(fileSection, "branches", branchNames)
    return

def addInputToFile(fileSection, inputLFN):
    """
    _addInputToFile_

    Given the LFN of an input file add it to the input section of the output
    file.
    """
    if not hasattr(fileSection, "input"):
        setattr(fileSection, "input", [])

    fileSection.input.append(inputLFN)
    return

def addRunInfoToFile(fileSection, runInfo):
    """
    _addRunInfoToFile_

    Given a ConfigSection object corresponding to an input/output file in the
    FWJR and a WMCore.DataStructs.Run object add the run and lumi information
    to the ConfigSection.  It will have the following format:
      fileSection.runs.RUNNUMBER = [LUMI1, LUMI2, LUMI3...]

    Note that the run number will have to be cast to a string.
    """
    runSection = fileSection.section_("runs")

    if not type(runInfo) == Run:
        for singleRun in runInfo:
            setattr(fileSection.runs, str(singleRun.run), singleRun.lumis)
    else:
        setattr(fileSection.runs, str(runInfo.run), runInfo.lumis)        
    return

def addAttributesToFile(fileSection, **attributes):
    """
    _addAttributesToFiles_

    Add attributes to a file in the FWJR.
    """
    for attName in attributes.keys():
        setattr(fileSection, attName, attributes[attName])
    return

class Report:
    def __init__(self, reportname = None):
        self.data = ConfigSection("FrameworkJobReport")
        self.data.steps         = []

        if reportname:
            self.addStep(reportname = reportname)

        return

    def listSteps(self):
        """
        _listSteps_

        List the names of all the steps in the report.
        """
        return self.data.steps

    def setStepStatus(self, stepName, status):
        """
        _setStepStatus_

        Set the status for a step.
        """
        reportStep = self.retrieveStep(stepName)        
        reportStep.status = status
        return
    
    def parse(self, xmlfile):
        """
        _parse_

        Read in the FrameworkJobReport XML file produced
        by cmsRun and pull the information from it into this object
        """
        from WMCore.FwkJobReport.XMLParser import xmlToJobReport
        try:
            xmlToJobReport(self, xmlfile)
        except Exception, ex:
            msg = "Error reading XML job report file, possibly corrupt XML File:\n"
            msg += "Details: %s" % str(ex)
            crashMessage = "\nStacktrace:\n"

            stackTrace = traceback.format_tb(sys.exc_info()[2], None)
            for stackFrame in stackTrace:
                crashMessage += stackFrame
                
            print msg
            print crashMessage
            self.addError("cmsRun1", 50115, "BadFWJRXML", msg)

    def __to_json__(self, thunker):
        """
        __to_json__

        Create a JSON version of the Report.
        """
        def jsonizeFiles(reportModule):
            jsonFiles = []
            fileCount = getattr(reportModule.files, "fileCount", 0)

            for i in range(fileCount):
                reportFile = getattr(reportModule.files, "file%s" % i)
                jsonFile = reportFile.dictionary_()

                cfgSectionRuns = jsonFile["runs"]
                jsonFile["runs"] = {}
                for runNumber in cfgSectionRuns.listSections_():
                    jsonFile["runs"][int(runNumber)] = getattr(cfgSectionRuns,
                                                               runNumber)
                jsonFiles.append(jsonFile)

            return jsonFiles

        jsonReport = {}

        for stepName in self.listSteps():
            reportStep = self.retrieveStep(stepName)
            jsonStep = {}
            jsonStep["status"] = reportStep.status

            jsonStep["output"] = {}
            for outputModule in reportStep.outputModules:
                reportOutputModule = getattr(reportStep.output, outputModule)
                jsonStep["output"][outputModule] = jsonizeFiles(reportOutputModule)                

            jsonStep["input"] = {}
            for inputSource in reportStep.input.listSections_():
                reportInputSource = getattr(reportStep.input, inputSource)
                jsonStep["input"][inputSource] = jsonizeFiles(reportInputSource)                

            jsonStep["errors"] = []
            errorCount = getattr(reportStep.errors, "errorCount", 0)
            for i in range(errorCount):
                reportError = getattr(reportStep.errors, "error%i" % i)
                jsonStep["errors"].append({"type": reportError.type,
                                           "details": reportError.details,
                                           "exitCode": reportError.exitCode})
                
            jsonStep["cleanup"] = {}
            jsonStep["parameters"] = {}
            jsonStep["site"] = {}
            jsonStep["analysis"] = {}
            jsonStep["logs"] = {}
            jsonReport[stepName] = jsonStep
        
        return jsonReport

    def stepSuccessful(self, stepName):
        """
        _stepSuccessful_

        """
        reportStep = self.retrieveStep(stepName)

        if int(getattr(reportStep, "status", 1)) == 0:
            return True

        return False

    def persist(self, filename):
        """
        _persist_


        """
        handle = open(filename, 'w')
        cPickle.dump(self.data, handle)
        handle.close()
        return

    def unpersist(self, filename):
        """
        _unpersist_

        load object from file

        """

        handle = open(filename, 'r')
        self.data = cPickle.load(handle)
        handle.close()
        return




    def addOutputModule(self, moduleName):
        """
        _addOutputModule_

        Add an entry for an output module.

        """

        self.report.outputModules.append(moduleName)
        
        self.report.output.section_(moduleName)

        outMod = getattr(self.report.output, moduleName)
        outMod.section_("files")
        outMod.section_("dataset")
        outMod.files.fileCount = 0

        return outMod


    def addOutputFile(self, outputModule, file = {}):
        """
        _addFile_

        Add an output file to the outputModule provided

        """

        if not checkFileForCompletion(file):
            # Then the file is not complete, and should not be added
            print "ERROR"
            return None


        # Now load the output module and create the file object
        outMod = getattr(self.report.output, outputModule, None)
        if outMod == None:
            outMod = self.addOutputModule(outputModule)
        count = outMod.files.fileCount
        fileSection = "file%s" % count
        outMod.files.section_(fileSection)
        fileRef = getattr(outMod.files, fileSection)
        outMod.files.fileCount += 1

        # Now we need to eliminate the optional and non-primitives:
        # runs, parents, branches, locations and datasets
        keyList = file.keys()
        
        fileRef.section_("runs")
        if file.has_key("runs"):
            for run in file["runs"]:
                addRunInfoToFile(fileRef, run)
            keyList.remove('runs')

        if file.has_key("parents"):
            setattr(fileRef, 'parents', list(file['parents']))
            keyList.remove('parents')

        if file.has_key("locations"):
            fileRef.location = list(file["locations"])
            keyList.remove('locations')

        # All right, the rest should be JSONalizable python primitives
        for entry in keyList:
            setattr(fileRef, entry, file[entry])

        #And we're done
        return fileRef

    def addInputSource(self, sourceName):
        """
        _addInputSource_

        Add an input source to the report doing nothing if the input source
        already exists.
        """
        if hasattr(self.report.input, sourceName):
            return getattr(self.report.input, sourceName)
            
        self.report.input.section_(sourceName)
        srcMod = getattr(self.report.input, sourceName)
        srcMod.section_("files")
        srcMod.files.fileCount = 0

        return srcMod

    def addInputFile(self, sourceName, **attrs):
        """
        _addInputFile_

        Add an input file to the source named

        """
        srcMod = getattr(self.report.input, sourceName, None)
        if srcMod == None:
            srcMod = self.addInputSource(sourceName)
        count = srcMod.files.fileCount
        fileSection = "file%s" % count
        srcMod.files.section_(fileSection)
        fileRef = getattr(srcMod.files, fileSection)
        [ setattr(fileRef, k, v) for k, v in attrs.items()]
        srcMod.files.fileCount += 1

        fileRef.section_("runs")

        return fileRef




    def addAnalysisFile(self, filename, **attrs):
        """
        _addAnalysisFile_

        Add and Analysis File

        """
        analysisFiles = self.report.analysis
        count = self.report.analysis.fileCount
        label = "file%s" % count

        analysisFiles.section_(label)
        newFile = getattr(analysisFiles, label)
        newFile.fileName = filename

        [ setattr(newFile, x, y) for x,y in attrs.items() ]

        self.report.analysis.fileCount += 1
        return



    def addRemovedCleanupFile(self, **attrs):
        """
        _addRemovedCleanupFile_
        
        Add a file to the cleanup.removed file
        """

        removedFiles = self.report.cleanup.removed
        count = self.report.cleanup.removed.fileCount
        label = 'file%s' % count

        removedFiles.section_(label)
        newFile = getattr(removedFiles, label)

        [ setattr(newFile, x, y) for x,y in attrs.items() ]

        self.report.cleanup.removed.fileCount += 1

        return


    def addError(self, stepName, exitCode, errorType, errorDetails):
        """
        _addError_

        Add an error report with an exitCode, type/class of error and
        details of the error as a string
        """
        if self.retrieveStep(stepName) == None:
            self.addStep(stepName)

        stepSection = self.retrieveStep(stepName)

        errorCount = getattr(stepSection.errors, "errorCount", 0)
        errEntry = "error%s" % errorCount
        stepSection.errors.section_(errEntry)
        errDetails = getattr(stepSection.errors, errEntry)
        errDetails.exitCode = exitCode
        errDetails.type = str(errorType)
        errDetails.details = errorDetails
        
        setattr(stepSection.errors, "errorCount", errorCount +1)
        return


    def addSkippedFile(self, lfn, pfn):
        """
        _addSkippedFile_

        report a skipped input file

        """

        count = self.report.skipped.files.fileCount
        entry = "file%s" % count
        self.report.skipped.files.section_(entry)
        skipSect = getattr(self.report.skipped.files, entry)
        skipSect.PhysicalFileName = pfn
        skipSect.LogicalFileName = lfn
        self.report.skipped.files.fileCount += 1
        return



    def addSkippedEvent(self, run, event):
        """
        _addSkippedEvent_


        """
        self.report.skipped.events.section_(str(run))
        runsect = getattr(self.report.skipped.events, str(run))
        if not hasattr(runsect, "eventList"):
            runsect.eventList = []
        runsect.eventList.append(event)
        return


    def addStep(self, reportname):
        """
        _addStep_
        
        This creates a report section into self.report
        """

        if hasattr(self.data, reportname):
            msg = "Attempted to create pre-existing report section %s" %(reportname)
            logging.error(msg)
            return

        self.data.steps.append(reportname)

        
        self.reportname = reportname
        self.data.section_(reportname)
        self.report = getattr(self.data, reportname)
        self.report.id = None
        self.report.task = None
        self.report.workload = None
        self.report.status = 0
        self.report.outputModules = []
        
        # structure
        self.report.section_("site")
        self.report.section_("output")
        self.report.section_("input")
        self.report.section_("performance")
        self.report.section_("analysis")
        self.report.section_("errors")
        self.report.section_("skipped")
        self.report.section_("parameters")
        self.report.section_("logs")
        self.report.section_("cleanup")
        self.report.cleanup.section_("removed")
        self.report.cleanup.section_("unremoved")
        self.report.skipped.section_("events")
        self.report.skipped.section_("files")
        self.report.skipped.files.fileCount = 0
        self.report.analysis.fileCount = 0
        self.report.cleanup.removed.fileCount = 0

        return

    def setStep(self, stepName, stepSection):
        """
        _setStep_

        """
        self.data.steps.append(stepName)        
        self.data.section_(stepName)
        setattr(self.data, stepName, stepSection)
        return

    def retrieveStep(self, step):
        """
        _retrieveStep_
        
        Grabs a report in the raw and returns it.  
        """
        reportSection = getattr(self.data, step, None)
        return reportSection

    def load(self, filename):
        """
        _load_
        
        This just maps to unpersist
        """

        self.unpersist(filename)


    def save(self, filename):
        """
        _save_
        
        This just maps to persist
        """

        self.persist(filename)


    def getOutputModule(self, step, outputModule):
        """
        _getOutputModule_
        
        Get the output module from a particular step
        """

        stepReport = self.retrieveStep(step = step)

        if not stepReport:
            return None

        return getattr(stepReport.output, outputModule, None)

    def getOutputFile(self, fileName, outputModule, step):
        """
        _getOutputFile_

        Takes a fileRef object and returns a DataStructs/File object as output
        """

        outputMod = self.getOutputModule(step = step, outputModule = outputModule)

        if not outputMod:
            return None

        fileRef = getattr(outputMod.files, fileName, None)
        file = File()

        #Locations
        file.setLocation(getattr(fileRef, "location", None))

        #Runs
        runList = fileRef.runs.listSections_()
        for run in runList:
            lumis  = getattr(fileRef.runs, run)
            newRun = Run(int(run), *lumis)
            file.addRun(newRun)

        file["lfn"]          = getattr(fileRef, "lfn", None)
        file["pfn"]          = getattr(fileRef, "pfn", None)
        file["events"]       = int(getattr(fileRef, "events", 0))
        file["size"]         = int(getattr(fileRef, "size", 0))
        file["branches"]     = getattr(fileRef, "branches", [])
        file["input"]        = getattr(fileRef, "input", [])
        file["branch_hash"]  = getattr(fileRef, "branch_hash", None)
        file["catalog"]      = getattr(fileRef, "catalog", "")
        file["guid"]         = getattr(fileRef, "guid", "")
        file["module_label"] = getattr(fileRef, "module_label", "")
        file["checksums"]    = getattr(fileRef, "checksums", {})
        file["merged"]       = bool(getattr(fileRef, "merged", False))
        file["dataset"]      = getattr(fileRef, "dataset", {})
        file["outputModule"] = outputModule

        return file

    def getAllFilesFromStep(self, step):
        """
        _getAllFilesFromStep_
        
        For a given step, retrieve all the associated files
        """

        stepReport = self.retrieveStep(step = step)

        if not stepReport:
            return None

        listOfModules = getattr(stepReport, 'outputModules', None)

        if not listOfModules:
            return None

        listOfFiles = []

        for module in listOfModules:
            tmpList = self.getFilesFromOutputModule(step = step, outputModule = module)
            if not tmpList:
                continue
            listOfFiles.extend(tmpList)


        return listOfFiles


    def getAllFiles(self):
        """
        _getAllFiles_

        Grabs all files in all output modules in all steps
        """
        listOfFiles = []

        for step in self.data.steps:
            tmp = self.getAllFilesFromStep(step = step)
            if tmp:
                listOfFiles.extend(tmp)

        return listOfFiles

    def getAllInputFiles(self):
        """
        _getAllInputFiles_
        
        Gets all the input files
        """

        listOfFiles = []
        for step in self.data.steps:
            tmp = self.getInputFilesFromStep(stepName = step)
            if tmp:
                listOfFiles.extend(tmp)

        return listOfFiles

    def getInputFilesFromStep(self, stepName, inputSource = None):
        """
        _getInputFilesFromStep_

        Retrieve a list of input files from the given step.
        """
        step = self.retrieveStep(stepName)

        inputSources = []
        if inputSource == None:
            inputSources = step.input.listSections_()
        else:
            inputSources = [inputSource]

        inputFiles = []
        for inputSource in inputSources:
            source = getattr(step.input, inputSource)
            for fileNum in range(source.files.fileCount):
                fwjrFile = getattr(source.files, "file%d" % fileNum)

                lfn = getattr(fwjrFile, "lfn", None)
                pfn = getattr(fwjrFile, "pfn", None)
                size = getattr(fwjrFile, "size", 0)
                events = getattr(fwjrFile, "events", 0)
                branches = getattr(fwjrFile, "branches", [])
                catalog = getattr(fwjrFile, "catalog", None)
                guid = getattr(fwjrFile, "guid", None)
                inputSourceClass = getattr(fwjrFile, "input_source_class", None)
                moduleLabel = getattr(fwjrFile, "module_label", None)
                inputType = getattr(fwjrFile, "input_type", None)

                inputFile = File(lfn = lfn, size = size, events = events)
                inputFile["pfn"] = pfn
                inputFile["branches"] = branches
                inputFile["catalog"] = catalog
                inputFile["guid"] = guid
                inputFile["input_source_class"] = inputSourceClass
                inputFile["module_label"] = moduleLabel
                inputFile["input_type"] = inputType

                runSection = getattr(fwjrFile, "runs")
                runNumbers = runSection.listSections_()

                for runNumber in runNumbers:
                    lumiTuple = getattr(runSection, str(runNumber))
                    inputFile.addRun(Run(int(runNumber), *lumiTuple))

                inputFiles.append(inputFile)

        return inputFiles

    def getFilesFromOutputModule(self, step, outputModule):
        """
        _getFilesFromOutputModule_
        
        Grab all the files in a particular output module
        """

        listOfFiles = []

        outputMod = self.getOutputModule(step = step, outputModule = outputModule)

        if not outputMod:
            return None

        for n in range(outputMod.files.fileCount):
            file = self.getOutputFile(fileName = 'file%i' %(n), outputModule = outputModule, step = step)
            if not file:
                msg = "Could not find file%i in module" %(n)
                logging.error(msg)
                return None
            
            #Now, append to the list of files
            listOfFiles.append(file)

        return listOfFiles

    def stepSuccessful(self, stepName):
        """
        _stepSuccessful_

        Determine wether or not a step was successful.
        """
        stepReport = self.retrieveStep(step = stepName)

        if int(getattr(stepReport, "status", 1)) == 0:
            return True

        return False


    def taskSuccessful(self):
        """
        _taskSuccessful_

        Return True if all steps successful, False otherwise
        """
        value = True

        for stepName in self.data.steps:
            stepReport = self.retrieveStep(step = stepName)
            if int(getattr(stepReport, "status", 1)) == 1:
                value = False

        return True
        

    def getAllFileRefsFromStep(self, step):
        """
        _getAllFileRefsFromStep_

        Retrieve a list of all files produced in a step.  The files will be in
        the form of references to the ConfigSection objects in the acutal
        report.
        """
        stepReport = self.retrieveStep(step = step)
        if not stepReport:
            return []

        outputModules = getattr(stepReport, "outputModules", [])
        fileRefs = []
        for outputModule in outputModules:
            outputModuleRef = self.getOutputModule(step = step, outputModule = outputModule)

            for i in range(outputModuleRef.files.fileCount):
                fileRefs.append(getattr(outputModuleRef.files, "file%i" % i))

        return fileRefs

    def addInfoToOutputFilesForStep(self, stepName, step):
        """
        _addInfoToOutputFilesForStep_

        Add the information missing from output files to the files
        This requires the WMStep to be passed in
        """

        stepReport = self.retrieveStep(step = stepName)
        fileInfo   = FileInfo()

        if not stepReport:
            return None

        listOfModules = getattr(stepReport, 'outputModules', None)

        for module in listOfModules:
            outputMod = getattr(stepReport.output, module, None)
            for n in range(outputMod.files.fileCount):
                file = getattr(outputMod.files, 'file%i' %(n), None)
                if not file:
                    msg = "Could not find file%i in module" %(n)
                    logging.error(msg)
                    return None
                fileInfo(fileReport = file, step = step, outputModule = module)


        return
                
if __name__ == "__main__":
    myReport = Report("cmsRun1")
    myReport.parse("/home/sfoulkes/WMCORE/test/python/WMCore_t/FwkJobReport_t/CMSSWFailReport.xml")

    print myReport.data
    print myReport.json()
