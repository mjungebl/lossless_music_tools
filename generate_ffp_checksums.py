"""This module will generate checksums for all FLAC files in a specified directory.
It treats each subfolder of the passed directory as a separate 'album' and will therefore generate a checksum in that directory for any flac files contained there or in subdirectories
REM sample cmd script
REM the PYTHONIOENCODING=utf8 is to allow for unicode in filenames
set PYTHONIOENCODING=utf8
SET WORKPATH='%~dp0'
C:/Users/mexic/AppData/Local/Programs/Python/Python312/python.exe l:/Flac/generate_ffp_checksums.py "%WORKPATH%" > log.txt
pause
"""
import os
import subprocess
import sys
import logging
import concurrent.futures
from filefolder_org import fix_directory_name, get_child_directories,remove_empty_file,load_config
from datetime import datetime
from losslessfiles import ffp
from pathlib import Path

def check_folder_for_checksums(DirectoryName):
    """This function will check if a ffp file exists in the specified directory"""
    ffpexists = False
    for fname in os.listdir(DirectoryName):
        if fname.lower().endswith(".ffp"):
            ffpexists = True
            break
    return ffpexists

def generate_checksums_for_folder(DirectoryName: str,PathToMetaflac: str):
    chkffp = check_folder_for_checksums(DirectoryName)
    if chkffp:
        #don't create ffp if one already exists
        print(f"ffp exists in:  {DirectoryName}/")
        return ([],None)
    else:
        DirectoryName = Path(DirectoryName).as_posix()
        ParentDirectoryName = Path(DirectoryName).parent.as_posix() +'/'
        ffpName = DirectoryName.replace(ParentDirectoryName,'') + '.ffp'
        print(f'{DirectoryName=} {ffpName=}')
        ffpFile = ffp(DirectoryName,ffpName,metaflacpath = PathToMetaflac)
        if not ffpFile.errors:
            ffpFile.generate_checksums()
        if not ffpFile.errors:
            ffpFile.SaveFfp()
        for Err in ffpFile.errors:
            logging.error(Err)
    #return ffpFile

def Main(DirectoryName):
    date = datetime.now().strftime('%Y%m%d%H%M%S') #date for the log name
    logger = logging.getLogger(__name__)
    logfilename = f'{DirectoryName}/Generate_Checksums{date}.log'
    logging.basicConfig(filename=logfilename, level=logging.ERROR ,format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S') #create log file
        
    config_file = os.path.join(os.path.dirname(__file__),"config.toml")
    config = load_config(config_file)
    PathToFlac = config['supportfiles']['flac']
    PathToMetaflac = config['supportfiles']['metaflac']
    list_subfolders_with_paths = get_child_directories(DirectoryName)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(generate_checksums_for_folder, dirnm,PathToMetaflac): dirnm for dirnm in list_subfolders_with_paths}
    logging.shutdown()
    remove_empty_file(logfilename)

if __name__ == "__main__":
    #To do: add compatibility with non-Windows systems
    

    #rootdirectory = r'X:\Downloads\_Extract\Phish'
    rootdirectory = str(sys.argv[1])
    while rootdirectory[-1:] in ["'"]:
        rootdirectory = rootdirectory[:len(rootdirectory)-1]
    while rootdirectory[0] in ["'"]:
        rootdirectory = rootdirectory[1:]
    rootdirectory = fix_directory_name(rootdirectory)
    #print(f'{rootdirectory=}')
    Main(rootdirectory)
