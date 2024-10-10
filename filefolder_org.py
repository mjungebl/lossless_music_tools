"""This module is not intended for execution. It contains functions shared between other modules that are used in flac file management"""
import os.path
import sys
import toml
"""
Path to artist exceptions. This file will map artist names to the artist folder name when there is a variation. 
Example: Bruce Springsteen & The E Street Band,Bruce Springsteen
"""
def load_config(config_name):
    with open(config_name) as f:
        config = toml.load(f)
        return config

config_file = os.path.join(os.path.dirname(__file__),"config.toml")
config = load_config(config_file)
#print(config['supportfiles']['artistexceptions'])

ARTISTEXCEPTIONFILE = config['supportfiles']['artistexceptions']

def remove_empty_file(file_path):
    """clean up files that were created if they're empty"""
    try:
        if os.stat(file_path).st_size == 0:
            os.remove(file_path)
            print(f"Removed empty file: {file_path}")
    except FileNotFoundError:
        pass  # File doesn't exist, so no need to remove

def fix_directory_name(DirectoryName):
    """Clean up the directory name so it is compatible with other code, remove trailing slashes as they'll be concatenated back in"""
    DirectoryName = DirectoryName.replace('\\','/')
    while DirectoryName[-1:] in ['/']:
        DirectoryName = DirectoryName[:len(DirectoryName)-1]
    return DirectoryName

def get_child_directories(dirnm):
    """Get a list of subdirectories for the directory specified. Only want a single level here"""
    dirnm = dirnm.strip()
    directorylist = [f.path.replace('\\','/') for f in os.scandir(dirnm) if f.is_dir()]
    return directorylist

def remove_path_from_dir_name(path,dirnm):
    """Remove the original path from the directory name. used as a step to farse the folder name for an artist"""
    dirnm = dirnm.replace(path,'')
    if dirnm[0] == '/':
        dirnm = dirnm[1:]
    return dirnm

def get_artist_subfolders(dirnm,folderlst, excpt = {}):
    """attempt to get the artist name from the folder name. if found, will be used to create a subfolder and move this folder there for easy copying to the music library"""
    directorymap = {}
    for folder in folderlst:
        reldir = remove_path_from_dir_name(dirnm,folder)
        if reldir.find(' - ') != -1:
            print('Exception keys:',excpt.keys(),'|'+reldir[0:reldir.find(' - ')]+'|')
            if reldir[0:reldir.find(' - ')] in excpt.keys():
                reldir = excpt[reldir[0:reldir.find(' - ')]]
            else:
                reldir = reldir[0:reldir.find(' - ')]
        else:
            reldir = None
        directorymap[folder] = reldir
    return directorymap

def load_artist_exceptions(filenm):
    """Load the artist exceptions file. Used when an artist should be mapped to a different subfolder"""
    exceptions = {}
    with open(filenm) as f:
        for line in f:
            if ',' in line:
                (key, val) = line.strip().split(',')
                exceptions[key] = val
    return exceptions
 
#test = load_artist_exceptions(ARTISTEXCEPTIONFILE)
#print(test)
if __name__ == "__main__":
    rootdirectory = str(sys.argv[1])
