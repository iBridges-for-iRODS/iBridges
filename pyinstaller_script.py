from genericpath import isfile
from subprocess import Popen, run, PIPE, STDOUT
from shutil import copytree, rmtree

from glob import glob
from os import getcwd, mkdir, path, remove, sep
from platform import system


"""
Pipeline to create pyinstaller executables.
not using the --onefile options because than windows has to upack the exe before it can run. 
This makes it rougly 30 seconds slower than the current variant. 
"""

# Run command in shell, stdout is printed to the screen
def run_cmd(cmd):
    if system()[0].upper() == "W": # windows
        ps = run(cmd, stderr=STDOUT, shell=True, universal_newlines=True)
    else:
        ps = run(cmd, stderr=STDOUT, shell=True, universal_newlines=True, executable="/bin/bash")
    # Print all errors
    if ps.stderr != None:
        print(f"commandline error: {ps.stderr}")
        raise Exception("shell run error")


# Convert the .ui files to .py files
def ui_to_py(ui_folder, python):
    # python -m PyQt5.uic.pyuic -x main.ui -o mainUI.py
    for ui_file in glob(ui_folder + '*.ui'):
        filename, ext = path.splitext(ui_file)
        print(f"Converting {filename} to .py")
        run_cmd(f"""{python} -m PyQt6.uic.pyuic -x {ui_file} -o {filename +".py"}""")

        # Find and replace the pixelmap references... They are hardcoded
        # Also have to go up one directory for the executable, its ugly! 
        with open(filename +".py", 'r') as file:
            lines = file.readlines()
            modified_lines = {}
            for linenum, line in enumerate(lines):
                if """QtGui.QPixmap(\"""" in line: 
                    abs_fchar = line.find("\"")
                    abs_lchar = line.find(".", abs_fchar) + 2

                    new_line = line[0:abs_fchar] + "dirname(realpath(sys.argv[0])) + \"" + line[abs_lchar:]
                    exeline = line[0:abs_fchar] + "join(dirname(realpath(sys.argv[0])), pardir) + \"" + line[abs_lchar:]
                    modified_lines[linenum] = (new_line, exeline)

        if len(modified_lines) > 0:
            lineofset = 0
            spacing = "        " #distance of one tab
            for linenum, text in modified_lines.items():
                lines[(linenum + lineofset)] = spacing + text[0]
                lines.insert(linenum + lineofset, f"{spacing}else:\n")
                lines.insert(linenum + lineofset, spacing + text[1])
                lines.insert(linenum + lineofset, f"{spacing}if getattr(sys, 'frozen', False):\n")
                lineofset = lineofset + 3

            lines.insert(10, "import sys\n")
            lines.insert(10, "from os.path import dirname, join, pardir, realpath\n")
            with open(filename +".py", 'w') as file:
                file.writelines(lines)


# Remove the locally stored .py versions of the files
def remove_pyui_files(ui_folder):
    pyuifiles = glob(ui_folder + '*.py')
    if len(pyuifiles) > 0:
        for file in pyuifiles:
            print(f"Removing {file}")
            remove(file)


# Overwrite one folder with all content
def replace_folder(source, destination):
    if path.exists(destination) and path.isdir(destination):
        rmtree(destination)
    copytree(source, destination)


if __name__ == "__main__":
    icons_folder = f"{getcwd()}{sep}gui{sep}icons"
    ui_folder = f"{getcwd()}{sep}gui{sep}ui_files{sep}"
    rules_folder = f"{getcwd()}{sep}rules"
    venv = f"{getcwd()}{sep}venv"

    # Seperator for sending multiple commands in one commandline call
    if system()[0].upper() == "W": # windows
        cmd_sep = "&&"
        python = "python" # python version 
    else: # Linux
        cmd_sep = ";"
        python = "python3"

    # Step 1 Convert .ui files to .py files
    # Remove py files if they already exist, recompiling is the best way to ensure they are up to date
    remove_pyui_files(ui_folder)
    ui_to_py(ui_folder, python)

    # Step 2: Pyinstallers includes all dependencies in the environment, so we use a venv
    # Step 2a, Ensure the folder for the venv exists 
    if (not path.exists(venv)) or (not path.isdir(venv)):
        mkdir(venv)
    
    # Step 2b, Create the venv if needed
    if system()[0].upper() == "W": # windows
        venv_activate = f"{venv}{sep}Scripts{sep}activate.bat"
    else:
        venv_activate = f"source {venv}/bin/activate"
    if (not path.exists(venv_activate)) or (not path.isfile(venv_activate)):
        run_cmd(f"{python} -m venv {venv}")
        run_cmd(f"{venv_activate} {cmd_sep} python -m pip install --upgrade pip")	      
        run_cmd(f"{venv_activate} {cmd_sep} pip install -r requirements.txt")

    # Step 3, Activate venv and tun pyinstaller
    run_cmd(f"{venv_activate} {cmd_sep} pyinstaller --clean --noconfirm --icon {icons_folder}{sep}irods-iBridgesGui.ico irods-iBridgesGui.py")
    dist_folder = f"{getcwd()}{sep}dist"


    # Step 4, Copy rules, icons folder to dist folder, replace if exists.
    dist_icons = f"{dist_folder}{sep}icons"
    dist_rules = f"{dist_folder}{sep}rules"
    replace_folder(icons_folder, dist_icons)
    replace_folder(rules_folder, dist_rules)
    
   
    confirmation = input("Do you want to cleanup the build environment (Y/N): ")
    if confirmation[0].upper() == 'Y':
        #remove_pyui_files(ui_folder)
        rmtree(getcwd() + sep + "build")
        #remove(getcwd() + "dist")
        remove(getcwd() + sep + "irods-iBridgesGui.spec")