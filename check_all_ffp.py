"""This script is used to verify all flac fingerprint files contained in subfolders of the directory that was passed in as an argument
REM Sample cmd script
REM the PYTHONIOENCODING=utf8 is to allow for unicode in filenames
set PYTHONIOENCODING=utf8
SET WORKPATH='%~dp0'
C:/Users/mexic/AppData/Local/Programs/Python/Python312/python.exe l:/Flac/check_all_ffp.py %WORKPATH% >> log.txt
pause
"""
import os
import subprocess
import logging
import sys
import toml
from filefolder_org import remove_empty_file,load_config
from datetime import datetime

errors = []
logger = logging.getLogger(__name__)
#use unicode instead of ascii, NOTE: Also need to add "set PYTHONIOENCODING=utf-8" if redirecting the output
os.system('chcp 65001') #windows only?

#logging.basicConfig(level=logging.INFO ,format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S') #Don't create log file. Useful for testing

def build_ffp_file_list(DirectoryName):
    """Generate the list of ffp files that are available to be verified"""
    ffplist = []
    for path, directories, files in os.walk(DirectoryName):
        for file in files:
            smallfile = file.lower()
            if smallfile.endswith(".ffp"):
                ffplist.append((f"{path.replace('\\','/')}/{file}", f"{path.replace('\\','/')}"))
    return ffplist

def check_ffp(ffpName, DirecotryName,FlacPath,MetaFlacPath):
    """verify an ffp file"""
    ErrorList = []
    ffp_signatures = parse_ffp(ffpName,DirecotryName)
    for key in ffp_signatures: 
        keymatch = False
        verified = False
        try:
            fingerprint = subprocess.check_output('"'+MetaFlacPath+'"'+' --show-md5sum "'+key+'"', encoding="utf8")
            if fingerprint.strip() == '00000000000000000000000000000000':
                msg = f'Error in file: {ffpName}. Path: {key} cannot check MD5 signature since it was unset in the STREAMINFO'
                ErrorList.append(msg)
                logging.warning(msg)
        except  subprocess.CalledProcessError as e:
            logging.error(e.cmd)
            print("Error:" + e.cmd)
        try:
            checkfile = subprocess.check_output('"'+FlacPath+'"'+' --test --silent "'+key, encoding="utf8")
            if str(ffp_signatures[key]).strip() == fingerprint.strip():
                msg = f"{key}:{ffp_signatures[key]} passed."
                print(msg)
                logging.info(msg)
            else:
                msg = f"{key}:{ffp_signatures[key]} verified, but does not match signature."
                print(msg)
                ErrorList.append(msg)
                logging.error(f'Error in file: {ffpName}. Path: {key} verified, but does not match signature.')
        except subprocess.CalledProcessError as e:
            ErrorList.append(f'Error verifying file: {key}')
            logging.error(f'Error verifying file: {key}')
    return ErrorList

def parse_ffp(ffpName,DirecotryName):
    """split ffp file into dictionary with full file path as key and signature as value"""
    ffp = open(ffpName, encoding="utf-8")
    ffp_sigs = {}
    for line in ffp:
            if not line.startswith(';') and ':' in line:
                ffp_line = line.strip().replace('\\','/')
                ffp_parts = ffp_line[::-1].split(':',1)
                ffp_sigs[DirecotryName+'/'+ffp_parts[1][::-1]] = ffp_parts[0][::-1]
    return ffp_sigs

#Main Code
if __name__ == "__main__":
    date = datetime.now().strftime('%Y%m%d%H%M%S') #date for the log name
    #These first two vaiables (PathToFlac,PathToMetaflac) could potentially be removed if the flac.exe and metaflac.exe are in the path.
    #To do: add compatibility with non-Windows systems
    config_file = os.path.join(os.path.dirname(__file__),"config.toml")
    config = load_config(config_file)
    PathToFlac = config['supportfiles']['flac']
    PathToMetaflac = config['supportfiles']['metaflac']
    rootdirectory = str(sys.argv[1]).replace("'","")
    
    while rootdirectory[-1:] in ['/']:
        rootdirectory = rootdirectory[:len(rootdirectory)-1]
    logfilename = f'{rootdirectory}/Verify{date}.log'
    logging.basicConfig(filename=logfilename, level=logging.WARNING ,format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S') #create log file
    logging.info('Searching for *.ffp files recursively: ' + rootdirectory)

    ffps = build_ffp_file_list(rootdirectory)
    if (len(ffps)) == 0:
        print(f'No fingerprints to verify in subdirectories of {rootdirectory}')

    for (filenm,pathnm) in ffps:
        print(filenm)
        logging.info('Verifying: ' + filenm)
        errors += check_ffp(filenm,pathnm,PathToFlac,PathToMetaflac)
    if len(errors) > 0:
        print('Errors:')
        for error in errors:
            print(error)
    else:
        print('No errors occurred')
    logging.info(f'Completed searching for *.ffp files recursively:  {rootdirectory}')
    #Close the log file and delete if it is empty
    logging.shutdown()
    remove_empty_file(logfilename)
