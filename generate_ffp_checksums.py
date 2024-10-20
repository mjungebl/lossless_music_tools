"""This module will generate checksums for all FLAC files in a specified directory.
It treats each subfolder of the passed directory as a separate 'album' and will therefore generate a checksum in that directory for any flac files contained there or in subdirectories
REM sample cmd script
REM the PYTHONIOENCODING=utf8 is to allow for unicode in filenames
set PYTHONIOENCODING=utf8
SET WORKPATH='%~dp0'
C:/Users/mexic/AppData/Local/Programs/Python/Python312/python.exe l:/Flac/generate_ffp_checksums.py "%WORKPATH%" > log.txt
pause
"""
import os.path
import subprocess
import sys
import toml
import logging
import concurrent.futures
from filefolder_org import fix_directory_name, get_child_directories,remove_empty_file,load_config
from datetime import datetime

def check_folder_for_checksums(DirectoryName):
    """This function will check if a ffp file exists in the specified directory"""
    ffpexists = False
    for fname in os.listdir(DirectoryName):
        if fname.lower().endswith(".ffp"):
            ffpexists = True
            break
    return ffpexists

def generate_checksums_for_folder(DirectoryName,ParentDirectoryName):
    """This function will generate checksums for all flac files in the specified directory and subdirectories"""
    chkffp = check_folder_for_checksums(DirectoryName)
    if chkffp:
        #don't create ffp if one already exists
        print(f"ffp exists in:  {DirectoryName}/")
        return ([],None)
    Fingerprints = []
    b_error = False
    for path, directories, files in os.walk(DirectoryName):
        for file in files:
            if file.lower().endswith(".flac"):
                filepath = path.replace('\\','/')+"/"+file
                try:
                    if len(filepath) > 260:
                        raise Exception(f"Path too long: {filepath =}")
                except Exception as e:
                    b_error = True
                    Err = f"Error: {e}" #sys.error(e) 
                    print(Err)
                    logging.error(Err)
                if not b_error:
                    try:               
                        fingerprint = subprocess.check_output('"'+PathToMetaflac+'"'+' --show-md5sum "'+filepath+'"', encoding="utf8")
                        if fingerprint.strip() == '00000000000000000000000000000000':
                            b_error = True
                            Err = f"Error in file: {filepath}. Fingerprint = {fingerprint.strip()}"
                            print(Err)
                            logger.error(Err)
                        else:
                            Fingerprints.append(filepath.replace(DirectoryName.replace('\\','/')+'/','')+':'+fingerprint.strip())
                    except subprocess.CalledProcessError as e:
                        Err = f"Error: {e.cmd}"
                        print(Err)
                        logging.error(Err)
                        b_error = True
    if b_error:
        print("Error Generating checksums for: "+DirectoryName)
        return ([],None)
    else:
        if len(Fingerprints) == 0:
            print("No checksums generated for: "+DirectoryName)
            return ([],None)
        print("Checksums generated for: "+DirectoryName)
        return (Fingerprints,DirectoryName+"/"+DirectoryName.replace(ParentDirectoryName,'')+'.ffp')

def WriteFfp(FingerprintList, FileName):
    """This function will create a ffp file in the specified directory using the values passed in"""
    try:
        output_file = open(FileName, 'w', encoding="utf-8")
        for ffp in FingerprintList:
            output_file.write(ffp + '\n')
        output_file.close()
        print(f"Created file: {FileName}")
    except Exception as e:
        #errors may occur occasionally when there is a bad character in a flac filename. Do not create the ffp file if an exception occurs
        if output_file.closed == False:
            output_file.close()
        remove_empty_file(FileName)
        print(f"ERROR Creating file: {e}")

def Main(DirectoryName):
    list_subfolders_with_paths = get_child_directories(DirectoryName)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(generate_checksums_for_folder, dirnm,DirectoryName): dirnm for dirnm in list_subfolders_with_paths}
        for future in concurrent.futures.as_completed(futures):
            ffps,filename = future.result()
            if ffps:
                WriteFfp(ffps,filename)

if __name__ == "__main__":
    #These first two vaiables (PathToFlac,PathToMetaflac) could potentially be removed if the flac.exe and metaflac.exe are in the path.
    #To do: add compatibility with non-Windows systems
    date = datetime.now().strftime('%Y%m%d%H%M%S') #date for the log name
    config_file = os.path.join(os.path.dirname(__file__),"config.toml")
    config = load_config(config_file)
    PathToFlac = config['supportfiles']['flac']
    PathToMetaflac = config['supportfiles']['metaflac']
    rootdirectory = str(sys.argv[1]).replace("'","")
    rootdirectory = fix_directory_name(rootdirectory)
    logger = logging.getLogger(__name__)
    logfilename = f'{rootdirectory}/Generate_Checksums{date}.log'
    logging.basicConfig(filename=logfilename, level=logging.ERROR ,format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S') #create log file
    Main(rootdirectory)
    logging.shutdown()
    remove_empty_file(logfilename)