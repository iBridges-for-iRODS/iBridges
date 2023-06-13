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
        exp_id = self.experiment.id()
        self.metadataUrl = f'{self.baseUrl}{URL_PATH}{exp_id}'
        self.__name__ = 'ELN'
        self.group = None

    def showGroups(self, get=False):
        groups_frame = self.elab.groups().all(['name', 'description'])
        print(groups_frame)
        if get:
            lines = groups_frame.to_string().split('\n')[2:]
            groups = [(group[0], ' '.join(group[1:]))
                      for group in [line.strip().split() for line in lines]]
            return groups
        return True

    def _choose_group(self):
        success = False
        while not success:
            in_var = input('Choose Elab groupId: ')
            try:
                group_id = int(in_var)
                if group_id in self.elab.groups().all().index:
                    print(f'{BLUE}Group chosen: {self.elab.group().name()}{DEFAULT}')
                    success = True
                    return group_id

                print(f'{YEL}\nNot a valid group_id"{DEFAULT}')
            except ValueError:
                print(r'{RED}Not a number{DEFAULT}')

    def _resolve_group_name(self, group_name):
        all_groups = self.elab.groups().all()
        if len(all_groups.loc[all_groups["name"]==group_name])==1:
            return all_groups.loc[all_groups["name"]==group_name].index[0]
        return group_name

    def _switch_group(self, group_id):
        if isinstance(group_id, str) and group_id.isnumeric():
            group_id = int(group_id)
        elif isinstance(group_id, str):
            group_id = self._resolve_group_name(group_name=group_id)

        if int(group_id) in self.elab.groups().all().index.to_list():
            self.elab.set_group(group_id)
            self.group = self.elab.groups().all().loc[[group_id]]
            return True

        raise ValueError('ERROR ELAB: groupId not found.')

    def showExperiments(self, groupId=None, get=False):
        current_group = self.elab.group().id()
        if groupId is None:
            groupId = self.elab.group().id()
        self._switch_group(groupId)
        exp_frames = self.elab.experiments().all()
        print('Your experiments:')
        my_exp_frame = exp_frames.loc[exp_frames['userID'] == self.userId, ['name', 'projectID']]
        print(my_exp_frame)
        print('Other experiments:')
        other_exp_frame = exp_frames.loc[exp_frames['userID'] != self.userId, ['name', 'projectID']]
        print(other_exp_frame)
        self._switch_group(current_group)

        if get:
            lines = my_exp_frame.to_string().split('\n')[2:]
            my_experiments = [(line[0], ' '.join(line[1:len(line) - 1]), line[len(line) - 1])
                             for line in [l.split() for l in lines]]
            lines = other_exp_frame.to_string().split('\n')[2:]
            other_experiments = [(line[0], ' '.join(line[1:len(line) - 1]), line[len(line) - 1])
                                for line in [l.split() for l in lines]]

            return (my_experiments, other_experiments)
        return True

    def _choose_experiment(self, group_id=None):
        current_group = self.elab.group().id()
        if group_id is None:
            group_id = self.elab.group().id()
        else:
            self._switch_group(group_id)
        self.showExperiments()
        success = False
        while not success:
            try:
                exp_id = int(input('Choose an experimentId: '))
                assert exp_id in self.elab.experiments().all().index
                success = True
                self._switch_group(current_group)
                return exp_id
            except Exception:
                print(f'{RED}Not a valid Experiment ID.{DEFAULT}')

    def __resolve_experiment_name(self, exp_name):
        all_exp = self.elab.experiments().all()
        if len(all_exp.loc[all_exp["name"]==exp_name])==1:
            return all_exp.loc[all_exp["name"]==exp_name].index[0]
        return exp_name

    def _switch_experiment(self, exp_id):

        if isinstance(exp_id, str) and exp_id.isnumeric():
            exp_id = int(exp_id)
        elif isinstance(exp_id, str):
            exp_id = self.__resolve_experiment_name(exp_name=exp_id)

        exp_frames = self.elab.experiments().all()
        if exp_id in exp_frames.index:
            self.experiment = self.elab.experiments().get(exp_id)
            return True

        raise ValueError("ERROR ELAB: expId not found.")

    def updateMetadataUrlInteractive(self, **params):
        current_group = self.elab.group().id()
        if 'group' in params and params['group'] is True:
            group_id = self._choose_group()
        else:
            group_id = current_group

        exp_id = self._choose_experiment(group_id)
        self._switch_group(group_id)
        self._switch_experiment(exp_id)
        self.metadataUrl = f'{self.baseUrl}{URL_PATH}{exp_id}'
        return self.elab.group().name(), self.experiment.name()

    def updateMetadataUrl(self, **params):
        group_id = params['group']
        exp_id = params['experiment']
        self._switch_group(group_id)
        self._switch_experiment(exp_id)
        self.metadataUrl = f'{self.baseUrl}{URL_PATH}{exp_id}'
        return self.metadataUrl

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
