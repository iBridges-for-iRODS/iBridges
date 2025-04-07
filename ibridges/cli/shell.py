import cmd

from ibridges.exception import NotACollectionError
from ibridges.cli.util import cli_authenticate, list_collection
from ibridges.path import IrodsPath
import subprocess

class IBridgesShell(cmd.Cmd):
    prompt = "ibridges> "

    def __init__(self):
        self.session = cli_authenticate(None)
        super().__init__()

    def do_shell(self, arg):
        subprocess.run(arg.split(" "))

    def do_list(self, arg):
        try:
            list_collection(self.session, remote_path=IrodsPath(self.session, arg))
        except NotACollectionError:
            print(f"{arg} is not a collection.")

    def complete_list(self, text, line, begidx, endidx):
        session = self.session

        cmd, *args = line.split()
        if len(args) == 0:
            path_list = []
            for ipath in IrodsPath(session).walk(depth=1):
                path_list.append(ipath.name)
            return path_list

        if len(args) > 1:
            return []

        base_path = IrodsPath(session, args[0])
        if base_path.collection_exists():
            if line.endswith("/"):
                prefix = text
            else:
                prefix = f"{text}/"
            return [f"{prefix}{ipath.name}" for ipath in base_path.walk(depth=1)]
        elif base_path.dataobject_exists():
            return []

        last_part = base_path.parts[-1]
        base_path = IrodsPath(session, *base_path.parts[:-1])
        completions = []
        for ipath in base_path.walk(depth=1):
            if ipath.name.startswith(last_part):
                completions.append(text + ipath.name[len(last_part):])
        return completions

    def do_EOF(self, arg):
        self.close()
        return True

    def close(self):
        self.session.close()

def main():
    IBridgesShell().cmdloop()
