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
from filefolder_org import fix_directory_name, get_child_directories,remove_empty_file,load_config

def check_folder_for_checksums(DirectoryName):
    """This function will check if a ffp file exists in the specified directory"""
    ffpexists = False
    for fname in os.listdir(DirectoryName):
        if fname.lower().endswith(".ffp"):
            ffpexists = True
            break
    return ffpexists

def generate_checksums_for_folder(DirectoryName):
    """This function will generate checksums for all flac files in the specified directory and subdirectories"""
    Fingerprints = []
    b_error = False
    for path, directories, files in os.walk(DirectoryName):
        for file in files:
            if file.lower().endswith(".flac"):
                filepath = path.replace('\\','/')+"/"+file
                try:
                    fingerprint = subprocess.check_output('"'+PathToMetaflac+'"'+' --show-md5sum "'+filepath+'"', encoding="utf8")
                    if fingerprint.strip() == '00000000000000000000000000000000':
                        b_error = True
                    else:
                        Fingerprints.append(filepath.replace(DirectoryName.replace('\\','/')+'/','')+':'+fingerprint.strip())
                except  subprocess.CalledProcessError as e:
                    print("Error:" + e.cmd)
                    b_error = True
    if b_error:
        print("Error Generating checksums for: "+DirectoryName)
        return []
    else:
        print("Checksums generated for: "+DirectoryName)
        return Fingerprints

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
    while list_subfolders_with_paths:
        dirnm = list_subfolders_with_paths.pop()
        chkffp = check_folder_for_checksums(dirnm)
        if chkffp:
            #don't create ffp if one already exists
            print(f"ffp exists in:  {dirnm}/")
            continue
        ffps = generate_checksums_for_folder(dirnm)
        if ffps:
            filename = dirnm+"/"+dirnm.replace(DirectoryName,'')+'.ffp'
            WriteFfp(ffps,filename)


if __name__ == "__main__":
    #These first two vaiables (PathToFlac,PathToMetaflac) could potentially be removed if the flac.exe and metaflac.exe are in the path.
    #To do: add compatibility with non-Windows systems
    config_file = os.path.join(os.path.dirname(__file__),"config.toml")
    config = load_config(config_file)
    PathToFlac = config['supportfiles']['flac']
    PathToMetaflac = config['supportfiles']['metaflac']
    rootdirectory = str(sys.argv[1]).replace("'","")
    rootdirectory = fix_directory_name(rootdirectory)
    Main(rootdirectory)