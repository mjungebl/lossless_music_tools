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
from losslessfiles import ffp



#use unicode instead of ascii, NOTE: Also need to add "set PYTHONIOENCODING=utf-8" if redirecting the output
os.system('chcp 65001 > NUL 2>&1') #windows only?

def build_ffp_file_list(DirectoryName):
    """Generate the list of ffp files that are available to be verified"""
    ffplist = []
    for path, directories, files in os.walk(DirectoryName):
        for file in files:
            smallfile = file.lower()
            if smallfile.endswith(".ffp"):
                ffpfile = ffp(path,file,{})
                ffpfile.readffpfile()
                ffplist.append(ffpfile)
    return ffplist

def main(rootdirectory):
    errors = []
    date = datetime.now().strftime('%Y%m%d%H%M%S') #date for the log name
    logger = logging.getLogger(__name__)
    logfilename = f'{rootdirectory}/Verify{date}.log'
    logging.basicConfig(filename=logfilename, level=logging.ERROR ,format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S') #create log file
    logger.info(f'Searching for *.ffp files recursively and verifying signatures in {rootdirectory}')
    config_file = os.path.join(os.path.dirname(__file__),"config.toml")
    config = load_config(config_file)
    PathToFlac = config['supportfiles']['flac']
    PathToMetaflac = config['supportfiles']['metaflac']
    ffps = build_ffp_file_list(rootdirectory)
    if (len(ffps)) == 0:
        print(f'No fingerprints to verify in subdirectories of {rootdirectory}')
    for ffpfile in ffps:
        if not ffpfile.errors:
            logger.info('Verifying: ' + ffpfile.name + ' in ' +ffpfile.location)
            ffpfile.verify() #= verifyffp(ffpfile,PathToFlac,PathToMetaflac)
        for error in ffpfile.errors:
            print(error)
            errors.append(error)
            logger.error(error)
        #for result in ffpfile.result:
        #    print(result)
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

#Main Code
if __name__ == "__main__":
    #To do: add compatibility with non-Windows systems
    #override for testing:
    #rd = r"X:\Music\Concerts\Concerts_GD\_Purchased"
    rd = str(sys.argv[1])
    while rd[-1:] in ["'"]:
        rd = rd[:len(rd)-1]
    while rd[0] in ["'"]:
        rd = rd[1:]
    rd = fix_directory_name(rd)
    main(rd)

 
