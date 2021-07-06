from elabjournal import elabjournal
import urllib.request

RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

class elabConnector():
    def __init__(self, token):
        try:
            self.elab = elabjournal.api(key=token)
            self.experiment = self.elab.experiments().first()
        except TypeError:
            raise PermissionError('Invalid token for ELN.')
        self.userId = self.elab.user().id()
        self.baseUrl = "https://"+token.split(";")[0]
        print("INFO: Default Experiment: "+self.experiment.name())
        self.metadataUrl = "https://"+token.split(";")[0]+ \
                "/members/experiments/browser/" + \
                "#view=experiment&nodeID="+str(self.experiment.id())
        self.__name__ = 'ELN'
        print("INFO: Data will be linked to: "+ self.metadataUrl)

    def showGroups(self):
        print(self.elab.groups().all(["name", "description"]))
        return True
    
    def __getGroupIds(self):
        return self.elab.groups().all().index

    def __chooseGroup(self):
        success = False
        while not success:
            inVar = input("Choose Elab groupId: ")
            try:
                groupId = int(inVar)
                if groupId in self.__getGroupIds():
                    print(BLUE+"Group chosen: "+self.elab.group().name()+DEFAULT)
                    success = True
                    return groupId
                else:
                    print(YEL+"\nNot a valid groupId"+DEFAULT)
            except ValueError:
                print(RED+'Not a number'+DEFAULT)

    def __switchGroup(self, groupId):
        if groupId in self.elab.groups().all().index:
            self.elab.set_group(groupId)
            return True
        else:
            raise ValueError("ERROR ELAB: groupId not found.")

    def showExperiments(self, groupId = None):
        currentGroup = self.elab.group().id()
        if groupId == None:
            groupId = self.elab.group().id()
        self.__switchGroup(groupId)
        experiments = self.elab.experiments()
        expFrames = self.elab.experiments().all()
        print("Your experiments:")
        print(expFrames.loc[expFrames["userID"] == self.userId, ["name", "projectID"]])
        print("Other experiments:")
        print(expFrames.loc[expFrames["userID"] != self.userId, ["name", "projectID"]])
        self.__switchGroup(currentGroup)

        return True

    def __getExperimentIds(self, groupId = None):
        currentGroup = self.elab.group().id()
        if groupId == None:
            groupId = self.elab.group().id()
        self.__switchGroup(groupId)
        experiments = self.elab.experiments()
        expFrames = self.elab.experiments().all()
        self.__switchGroup(currentGroup)
        return expFrames.index

    def __chooseExperiment(self, groupId = None):
        currentGroup = self.elab.group().id()
        if groupId == None:
            groupId = self.elab.group().id()
        else:
            self.__switchGroup(groupId)
        self.showExperiments()
        success = False
        while not success:
            try:
                expId = int(input("Choose an experimentId:"))
                assert(expId in self.elab.experiments().all().index)
                success = True
                self.__switchGroup(currentGroup)
                return expId
            except Exception as error:
                print(RED+"Not a valid Experiment ID."+DEFAULT)
            
    def __switchExperiment(self, expId):
        experiments = self.elab.experiments()
        expFrames = self.elab.experiments().all()
        if expId in expFrames.index:
        if expId in expFrames.index:
            self.experiment = self.elab.experiments().get(expId)
            return True
        else:
            raise ValueError("ERROR ELAB: expId not found.")

    def updateMetadataUrlInteractive(self, **params):
        currentGroup = self.elab.group().id()
        currentUrl = self.metadataUrl
        if 'group' in params and params['group'] == True:
            groupId = self.__chooseGroup()
        else:
            groupId = currentGroup

        expId = self.__chooseExperiment(groupId)
        self.__switchGroup(groupId)
        self.__switchExperiment(expId)
        self.metadataUrl = self.baseUrl+ \
            "/members/experiments/browser/#view=experiment&nodeID="+ \
            str(expId)
        return(self.elab.group().name(), self.experiment.name())

    def updateMetadataUrl(self, **params):
        try:
            groupId = params['group']
            expId = params['experiment']
            self.__switchGroup(groupId)
            self.__switchExperiment(expId)
            self.metadataUrl = self.baseUrl+ \
                "/members/experiments/browser/#view=experiment&nodeID="+ \
                str(expId)
            return self.metadataUrl
        except:
            raise

    def addMetadata(self, info, title='Title'):
        self.experiment.add(info, title)
        return True
