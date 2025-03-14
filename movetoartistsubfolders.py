"""This module is used to move album directories into artist subfolders that match the directory names in the music library for easier copying.
This is intended to be the final step after verification is complete"""
import os.path
import sys
from filefolder_org import fix_directory_name, get_child_directories, remove_path_from_dir_name,  get_artist_subfolders, load_artist_exceptions,\
      load_config, ARTISTEXCEPTIONFILE
import shutil

def main(directoryname):
    #config_file = os.path.join(os.path.dirname(__file__),"config.toml")
    #config = load_config(config_file)    
    exceptions = load_artist_exceptions(ARTISTEXCEPTIONFILE)
    directoryname = fix_directory_name(directoryname)
    listsubfolders = get_child_directories(directoryname)
    foldermap = get_artist_subfolders(directoryname, listsubfolders, exceptions)
    artistfolders = list(set(foldermap.values()))
    for artistfolder in artistfolders:
        if artistfolder:
            if not os.path.exists(artistfolder):
                os.makedirs(artistfolder)
    for source, destination in foldermap.items():
        if destination != None:
            if os.path.exists(destination) and os.path.exists(source):
                if not os.path.exists(os.path.join(os.path.abspath(destination),remove_path_from_dir_name(directoryname,source))):
                    origpath = os.path.abspath(source)
                    newpath = os.path.join(os.path.abspath(destination),remove_path_from_dir_name(directoryname,source))
                    shutil.move(origpath, newpath)

if __name__ == "__main__":
    #sys.argv = [' ',r'X:\Downloads\_Extract\_Batch\' ]
    rootdirectory = str(sys.argv[1])
    #rootdirectory = r'X:\Downloads\_Extract\_Batch' 
    #print("ARTISTEXCEPTIONFILE:", ARTISTEXCEPTIONFILE)
    main(rootdirectory)