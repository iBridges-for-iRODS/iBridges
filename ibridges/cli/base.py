import argparse

class ShellArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        if status:
            print(f'Error: {message}')
        self.printed_help = True

