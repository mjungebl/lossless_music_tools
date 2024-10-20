"""This script is used to verify all flac fingerprint files contained in subfolders of the directory that was passed in as an argument
REM Sample cmd script
REM the PYTHONIOENCODING=utf8 is to allow for unicode in filenames
set PYTHONIOENCODING=utf8
SET WORKPATH='%~dp0'
C:/Users/mexic/AppData/Local/Programs/Python/Python312/python.exe l:/Flac/check_all_ffp.py "%WORKPATH%" >> log.txt
pause
"""
import os
import subprocess
import logging
import sys
import toml
import concurrent.futures
from filefolder_org import remove_empty_file,load_config,fix_directory_name
from datetime import datetime


errors = []
#use unicode instead of ascii, NOTE: Also need to add "set PYTHONIOENCODING=utf-8" if redirecting the output
os.system('chcp 65001 > NUL 2>&1') #windows only?

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
    ffp_signatures, Err = parse_ffp(ffpName,DirecotryName)
    if Err != None:
        ErrorList.append(Err)
        return ErrorList
    #a single cpu is not maxing out the disk when verifying, speed things up a bit...
    #with concurrent.futures.ProcessPoolExecutor() as executor:
    #multithreading appears to be a bit faster
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(check_flac_file, filenm,checksum,FlacPath,MetaFlacPath,ffpName): (filenm,checksum) for (filenm,checksum) in list(ffp_signatures.items())}
        for future in concurrent.futures.as_completed(futures):
            Err,message = future.result()
            if Err == None:
                print(message)
                logger.info(message)
            else:
                ErrorList.append(Err)
                logger.error(Err)
 
    return ErrorList

def check_flac_file(filenm,checksum,fp,mfp,ffpnm):
    """check an individual flac file"""
    Error = None
    try:
        fingerprint = subprocess.check_output('"'+mfp+'"'+' --show-md5sum "'+filenm+'"', encoding="utf8")
        if fingerprint.strip() == '00000000000000000000000000000000':
            Error = msg = f'Error in file: {filenm}. Path: {filenm} cannot check MD5 signature since it was unset in the STREAMINFO'
    except  subprocess.CalledProcessError as e:
        #logger.error(e.cmd)
        Error = msg = f"Error: {e.cmd}"
    try:
        checkfile = subprocess.check_output('"'+fp+'"'+' --test --silent "'+filenm, encoding="utf8")
        if str(checksum).strip() == fingerprint.strip():
            msg = f"{filenm}:{checksum} passed."
        else:
            Error = msg = f"Error in file: {ffpnm}. Path: {filenm}:{checksum} verified, but does not match signature."
    except subprocess.CalledProcessError as e:
        Error = msg = f'Error verifying file: {filenm}: {e}'
        
    return Error, msg

def parse_ffp(ffpName,DirecotryName):
    """split ffp file into dictionary with full file path as key and signature as value"""
    msg = None
    ffp_sigs = {}
    try: 
        ffp = open(ffpName, encoding="utf-8")
    except Exception as e:
        msg = f'Error in file {ffpName}: {e}'
        print(msg)
        logger.error(msg)          
    #Attempt to read the first line of the ffp file to determine if it is not encoded using utf-8. If an error occurs, reopen without the encoding parameter.
    try:
        firstline = ffp.readline()
    except UnicodeDecodeError:
        ffp.close()
        try: 
            ffp = open(ffpName)
        except Exception as e:
            msg = f'Error in file {ffpName}: {e}'
            print(msg)
            logger.error(msg)               
    try:
        for line in ffp:
                if not line.startswith(';') and ':' in line:
                    ffp_line = line.strip().replace('\\','/')
                    ffp_parts = ffp_line[::-1].split(':',1)
                    ffp_sigs[DirecotryName+'/'+ffp_parts[1][::-1]] = ffp_parts[0][::-1]
    except Exception as e:
        msg = f'Error in file {ffpName}: {e}'
        print(msg)
        logger.error(msg)                    
    
    return ffp_sigs, msg


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
    rootdirectory = fix_directory_name(rootdirectory)
    logger = logging.getLogger(__name__)
    logfilename = f'{rootdirectory}/Verify{date}.log'
    logging.basicConfig(filename=logfilename, level=logging.ERROR ,format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S') #create log file
    logger.info(f'Searching for *.ffp files recursively and verifying signatures in {rootdirectory}')
    ffps = build_ffp_file_list(rootdirectory)
    if (len(ffps)) == 0:
        print(f'No fingerprints to verify in subdirectories of {rootdirectory}')

    for (filenm,pathnm) in ffps:
        print(filenm)
        logger.info('Verifying: ' + filenm)
        errors += check_ffp(filenm,pathnm,PathToFlac,PathToMetaflac)
    if len(errors) > 0:
        log_err_sum = False
        if logger.getEffectiveLevel() < 40: #if we need to scroll through the log, summarize the errors at the end
            logger.error('Error Summary:')
            log_err_sum = True
        print('Errors:')
        for error in errors:
            print(f'Error: {error}')
            if log_err_sum:
                logger.error(error)
    else:
        print('No errors occurred')
    logger.info(f'Completed searching and verifying *.ffp files recursively in {rootdirectory}')
    #Close the log file and delete if it is empty
    logging.shutdown()
    remove_empty_file(logfilename)
