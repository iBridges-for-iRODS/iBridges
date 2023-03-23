"""IrodsConnector for eLabJournal

"""
from urllib.parse import urlparse
from elabjournal import elabjournal

URL_PATH = '/members/experiments/browser/#view=experiment&nodeID='
DEFAULT = '\x1b[0m'
RED = '\x1b[1;31m'
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
        self.baseUrl = f'https://{token.split(";")[0]}'
        print(f'INFO: Default Experiment: {self.experiment.name()}')
        exp_id = self.experiment.id()
        self.metadataUrl = f'{self.baseUrl}{URL_PATH}{exp_id}'
        self.__name__ = 'ELN'
        print(f'INFO: Data will be linked to: {self.metadataUrl}')

    def showGroups(self, get=False):
        groupsFrame = self.elab.groups().all(['name', 'description'])
        print(groupsFrame)
        if get:
            lines = groupsFrame.to_string().split('\n')[2:]
            groups = [(group[0], ' '.join(group[1:]))
                      for group in [line.strip().split() for line in lines]]
            return groups
        return True

    def __chooseGroup(self):
        success = False
        while not success:
            inVar = input('Choose Elab groupId:')
            try:
                groupId = int(inVar)
                if groupId in self.elab.groups().all().index:
                    print(f'{BLUE}Group chosen: {self.elab.group().name()}{DEFAULT}')
                    success = True
                    return groupId
                else:
                    print(f'{YEL}\nNot a valid groupId"{DEFAULT}')
            except ValueError:
                print(r'{RED}Not a number{DEFAULT}')

    def __resolveGroupName(self, groupName):
        all = self.elab.groups().all()
        if len(all.loc[all["name"]==groupName])==1:
            return all.loc[all["name"]==groupName].index[0]
        return groupName

    def __switchGroup(self, groupId):
        if isinstance(groupId, str) and groupId.isnumeric():
            groupId = int(groupId)
        elif isinstance(groupId, str):
            groupId = self.__resolveGroupName(groupId)

        if int(groupId) in self.elab.groups().all().index.to_list():
            self.elab.set_group(groupId)
            self.group = self.elab.groups().all().loc[[groupId]]
            return True
        else:
            raise ValueError('ERROR ELAB: groupId not found.')

    def showExperiments(self, groupId=None, get=False):
        currentGroup = self.elab.group().id()
        if groupId is None:
            groupId = self.elab.group().id()
        self.__switchGroup(groupId)
        experiments = self.elab.experiments()
        expFrames = self.elab.experiments().all()
        print('Your experiments:')
        myExpFrame = expFrames.loc[expFrames['userID'] == self.userId, ['name', 'projectID']]
        print(myExpFrame)
        print('Other experiments:')
        otherExpFrame = expFrames.loc[expFrames['userID'] != self.userId, ['name', 'projectID']]
        print(otherExpFrame)
        self.__switchGroup(currentGroup)

        if get:
            lines = myExpFrame.to_string().split('\n')[2:]
            myExperiments = [(line[0], ' '.join(line[1:len(line) - 1]), line[len(line) - 1])
                             for line in [l.split() for l in lines]]
            lines = otherExpFrame.to_string().split('\n')[2:]
            otherExperiments = [(line[0], ' '.join(line[1:len(line) - 1]), line[len(line) - 1])
                                for line in [l.split() for l in lines]]

            return (myExperiments, otherExperiments)
        return True

    def __chooseExperiment(self, groupId=None):
        currentGroup = self.elab.group().id()
        if groupId is None:
            groupId = self.elab.group().id()
        else:
            self.__switchGroup(groupId)
        self.showExperiments()
        success = False
        while not success:
            try:
                expId = int(input('Choose an experimentId:'))
                assert expId in self.elab.experiments().all().index
                success = True
                self.__switchGroup(currentGroup)
                return expId
            except Exception as error:
                print(f'{RED}Not a valid Experiment ID.{DEFAULT}')

    def __switchExperiment(self, expId):
        # TODO determine if this call is needed
        experiments = self.elab.experiments()
        expFrames = self.elab.experiments().all()
        if expId in expFrames.index:
            self.experiment = self.elab.experiments().get(expId)
            return True
        else:
            raise ValueError("ERROR ELAB: expId not found.")

    def updateMetadataUrlInteractive(self, **params):
        currentGroup = self.elab.group().id()
        currentUrl = self.metadataUrl
        if 'group' in params and params['group'] is True:
            groupId = self.__chooseGroup()
        else:
            groupId = currentGroup

        expId = self.__chooseExperiment(groupId)
        self.__switchGroup(groupId)
        self.__switchExperiment(expId)
        self.metadataUrl = f'{self.baseUrl}{URL_PATH}{expId}'
        return self.elab.group().name(), self.experiment.name()

    def updateMetadataUrl(self, **params):
        try:
            groupId = params['group']
            expId = params['experiment']
            self.__switchGroup(groupId)
            self.__switchExperiment(expId)
            self.metadataUrl = f'{self.baseUrl}{URL_PATH}{expId}'
            return self.metadataUrl
        except:
            raise

    def addMetadata(self, url, meta=None, title='Title'):
        infos = []

        url_parts = urlparse(url)
        if all([url_parts.scheme, url_parts.netloc]):
            infos.append(f'<a href="{url}">Experiment data in iRODS</a>')
        else:
            infos.append(url)

        if meta is not None:
            infos.append('<br>')
            infos.append('<table style="width: 500px;" border="1" cellspacing="1" cellpadding="1">')
            infos.append('<tbody>')
            for key, value in meta.items():
                infos.append(f'<tr><td>{key}</td><td>{value}</td></tr>')
            infos.append('</tbody>')
            infos.append('</table>')

        self.experiment.add(''.join(infos), title)
        return True
