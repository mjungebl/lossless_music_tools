"""This module is used to move album directories into artist subfolders that match the directory names in the music library for easier copying.
This is intended to be the final step after verification is complete"""
import os.path
import sys
from filefolder_org import fix_directory_name, get_child_directories, remove_path_from_dir_name,  get_concert_subfolders, load_artist_exceptions,\
      load_config, ARTISTEXCEPTIONFILE
import shutil
import toml

def main(directoryname, exceptions = {}):
    directoryname = fix_directory_name(directoryname)
    listsubfolders = get_child_directories(directoryname)
    for subdir in listsubfolders:
        #if subdir.lower().startswith('gd'):
        print(f'{subdir =}')
    foldermap = get_concert_subfolders(directoryname, listsubfolders)
    print(f'{foldermap = }')
    concertfolders = list(set(foldermap.values()))
    for concertfolder in concertfolders:
        if concertfolder:
            if not os.path.exists(concertfolder):
                os.makedirs(concertfolder)
    for source, destination in foldermap.items():
        if destination != None:
            if os.path.exists(destination) and os.path.exists(source):
                if not os.path.exists(os.path.join(os.path.abspath(destination),remove_path_from_dir_name(directoryname,source))):
                    origpath = os.path.abspath(source)
                    newpath = os.path.join(os.path.abspath(destination),remove_path_from_dir_name(directoryname,source))
                    shutil.move(origpath, newpath)

if __name__ == "__main__":
    #config_file = os.path.join(os.path.dirname(__file__),"config.toml")
    #config = load_config(config_file)
    #rootdirectory = str(sys.argv[1])
    rootdirectory = 'X:/Downloads/_FTP/_Concerts_Unofficial/_renamed2'
    #print("ARTISTEXCEPTIONFILE:", ARTISTEXCEPTIONFILE)
    #artistexceptions = load_artist_exceptions(ARTISTEXCEPTIONFILE)
    main(rootdirectory)