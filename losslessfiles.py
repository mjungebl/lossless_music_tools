import os
import subprocess
from pathlib import Path
from filefolder_org import remove_empty_file,load_config
from mutagen.flac import FLAC
#import soundfile as sf
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed #need to reconcile this with the above at some point. 
import hashlib
import re

config_file = os.path.join(os.path.dirname(__file__),"config.toml")
config = load_config(config_file)
PathToFlac = config['supportfiles']['flac']
PathToMetaflac = config['supportfiles']['metaflac']

#print(f'{PathToFlac=} {PathToMetaflac=}')




def generate_st5_for_folder(shntool_exe: str, folder: str, st5_filename: str,audiofiles:list):
    """
    In 'folder', run:
      shntool.exe hash -m *.flac > st5_filename
    capturing stdout => st5_filename.
    """
    #cmd = [
    #    shntool_exe,
    #    "hash",
    #    "-m",
    #    "*.flac"
    #]
    st5_path = os.path.join(folder, st5_filename)
    print(f"[ST5 from: {folder} => {st5_filename}]")
    #proc = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    #with open(st5_path, "w", encoding="utf-8") as f:
    #    f.write(proc.stdout)
    st5_results = []
    with ThreadPoolExecutor () as executor:
            #futures = {executor.submit(verifyflacfile, filenm,checksum,self.flacpath,self.metaflacpath,self.name,self.location): \
            #        (filenm,checksum) for (filenm,checksum) in list(self.signatures.items())}        
        futures = [executor.submit(generate_st5_for_file,shntool_exe,file,folder) for file in audiofiles]
        for future in as_completed(futures):
            message = future.result()
            st5_results.append(message)

        st5data = ''.join([x[2] for x in sorted(st5_results)])
        returncode = 0
        for rc in [x[1] for x in sorted(st5_results)]:
            if rc !=0:
                returncode= rc
    with open(st5_path, "w", encoding="utf-8") as f:
        f.write(st5data)    
    return (st5_path, returncode)

def generate_st5_for_file(shntool_exe: str, file:str, folder: str):
    """
    In 'folder', run:
      shntool.exe hash -m *.shn > st5_filename
    capturing stdout => st5_filename.
    """
    #print(f'{folder=}')
    cmd = [
        shntool_exe,
        "hash",
        "-m",
        file
    ]
    #st5_path = os.path.join(folder, st5_filename)
    #print(f"[ST5 from SHN] {folder} => {st5_filename}")
    proc = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    #with open(st5_path, "w", encoding="utf-8") as f:
    #    f.write(proc.stdout)
    return (file,proc.returncode, proc.stdout, proc.stderr,proc)


class ffp:
    def __init__ (self, location: str, name: str, signatures: dict ={}, metaflacpath: str = None, flacpath: str = None):
        self.location = location
        self.name = name
        #if metaflacpath is not None:
        self.metaflacpath = metaflacpath if metaflacpath != None else PathToMetaflac
        self.flacpath = flacpath if flacpath != None else PathToFlac
        self.signatures = signatures
        self.errors = []
        self.result = []

    def readffpfile(self):
        """split ffp file into dictionary with full file path as key and signature as value"""
        ffpName = f'{self.location}/{self.name}'
        msg = None
        ffp_sigs = {}
        try: 
            ffp = open(ffpName, encoding="utf-8")
        except Exception as e:
            msg = f'Error reading file {ffpName}: {e}'
            print(msg)
            self.errors.append(msg)
        #Attempt to read the first line of the ffp file to determine if it is not encoded using utf-8. If an error occurs, reopen without the encoding parameter.
        try:
            firstline = ffp.readline()
            ffp.close()
            ffp = open(ffpName, encoding="utf-8")
        except UnicodeDecodeError:
            ffp.close()
            try: 
                ffp = open(ffpName)
            except Exception as e:
                msg = f'Error reading file {ffpName}: {e}'
                self.errors.append(msg)
                print(msg)             
        try:
            for line in ffp:
                    if not line.startswith(';') and ':' in line:
                        ffp_line = line.strip().replace('\\','/')
                        ffp_parts = ffp_line[::-1].split(':',1)
                        ffp_sigs[ffp_parts[1][::-1]] = ffp_parts[0][::-1]
                    else: #old format seen in some files. 
                        if not line.startswith(';') and '*' in line:
                            ffp_line = line.strip().replace('\\','/')
                            ffp_parts = ffp_line[::-1].split('*',1)
                            ffp_sigs[ffp_parts[0][::-1].strip()] = ffp_parts[1][::-1].strip()
            self.signatures = ffp_sigs
        except Exception as e:
            msg = f'Error reading file {ffpName}: {e}'
            #print(msg)
            self.errors.append(msg)
            #logger.error(msg)                    
        
        #return ffpFile

    def generate_checksums(self):
        """loop though all files and child directories to generate the checksums for all .flac files, storing them with the relative path"""
        DirectoryName = self.location +'/'
        ParentDirectoryName = Path(DirectoryName).parent.as_posix()
        b_error = False
        self.signatures = {}
        for path, directories, files in os.walk(DirectoryName):
            for file in files:
                if file.lower().endswith(".flac"):
                    filepath = Path(path.replace('\\','/')+"/"+file).as_posix()
                    try:
                        if len(filepath) > 260:
                            raise Exception(f"Path too long: {filepath =}")
                    except Exception as e:
                        b_error = True
                        Err = f"Error: {e}" #sys.error(e) 
                        self.errors.append(Err)
                    if not b_error:
                        try:
                            #fingerprint = subprocess.check_output('"'+self.metaflacpath+'"'+' --show-md5sum "'+filepath+'"', encoding="utf8")
                            #with open(filepath, 'rb') as f:
                            flac_file = FLAC(filepath) #using mutagen prevents the need to call the metaflac cmd. 
                            fingerprint = ("%02x" % flac_file.info.md5_signature).rjust(32, '0')

                            if fingerprint.strip() == '00000000000000000000000000000000':
                                b_error = True
                                Err = f"Error in file: {filepath}. Fingerprint = {fingerprint.strip()}"
                                self.errors.append(Err)
                                print(Err)
                            else:
                                self.signatures[filepath.replace(DirectoryName,'')] = fingerprint.strip()
                        except Exception as e:
                            Err = f"Error: {e}"
                            self.errors.append(Err)
                            print(Err)
                            b_error = True
        if b_error:
            print("Error Generating checksums for: "+DirectoryName)
            #return ([],None)
        else:
            if len(self.signatures) == 0:
                print("No checksums generated for: "+DirectoryName)
                #return ([],None)
            else:
                print("Checksums generated for: "+DirectoryName)
        
    def SaveFfp(self):
        """This function will create a ffp file in the specified directory using the values passed in"""
        FileName = self.location +'/' +self.name
        if self.signatures:
            try:
                #output_file = open(FileName, 'w', encoding="utf-8")
                with open(FileName, 'w', encoding='utf-8') as output_file:
                #for key,value in self.signatures.items():
                    for key in sorted(self.signatures):
                        value = self.signatures[key]                
                        output_file.write(key+':'+value + '\n')
                    #output_file.close()
                print(f"Created file: {FileName}")
            except Exception as e:
                #errors may occur occasionally when there is a bad character in a flac filename. Do not create the ffp file if an exception occurs
                #if output_file.closed == False:
                #    output_file.close()
                remove_empty_file(FileName)
                print(f"ERROR Creating file: {e}")
        else:
            print(f"No signatures file not created: {FileName}")
    
    def verify(self, silent = False):
        #return None
        """verify an ffp file"""
        self.result = []
        self.errors = []
        print(f'Verifying {self.name} in {self.location}:')
        #a single process is not maxing out the disk when verifying, speed things up a bit...
        #with concurrent.futures.ProcessPoolExecutor() as executor:
        #multithreading appears to be a bit faster
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(verifyflacfile, filenm,checksum,self.flacpath,self.metaflacpath,self.name,self.location): \
                    (filenm,checksum) for (filenm,checksum) in list(self.signatures.items())}
            for future in concurrent.futures.as_completed(futures):
                Err = None
                message = None
                Err,message = future.result()
                if Err == None:
                    #print(message)
                    #logger.info(message)
                    self.result.append(message)
                else:
                    self.errors.append(Err)
                    #logger.error(Err)
                if not silent:
                    print('\t'+ message if Err == None else Err)

def verifyflacfile(filenm,checksum,fp,mfp,ffpnm,loc):
    """check an individual flac file"""
    filepath = loc + '/' + filenm
    Error = None
    try:
        #fingerprint = subprocess.check_output('"'+mfp+'"'+' --show-md5sum "'+loc+'/'+filenm+'"', encoding="utf8")
        flac_file = FLAC(filepath) #using mutagen prevents the need to call the metaflac cmd. 
        fingerprint = ("%02x" % flac_file.info.md5_signature).rjust(32, '0')        
        if fingerprint.strip() == '00000000000000000000000000000000':
            Error = msg = f'Error in file: {filenm}. Path: {filenm} cannot check MD5 signature since it was unset in the STREAMINFO'
    #except  subprocess.CalledProcessError as e:
    except Exception as e:
        #logger.error(e.cmd)
        Error = msg = f"Error: {e}"
    try:
        #rawfingerprint = calcflacfingerprint(filepath)
        #if rawfingerprint != fingerprint:
        #    msg = f"{filenm}:{rawfingerprint} does not match {checksum}."
        checkfile = subprocess.check_output('"'+fp+'"'+' --test --silent "'+loc+'/'+filenm, encoding="utf8")
        if str(checksum).strip() == fingerprint.strip():
            msg = f"{filenm}:{checksum} passed."
        else:
            Error = msg = f"Error in file: {ffpnm}. Path: {filenm}:{checksum} verified, but does not match signature."
    except Exception as e:
        Error = msg = f'Error verifying file: {filenm}:\n\t {e}'
    #print('\t'+msg if Error == None else Error)
    return Error, msg

def calcflacfingerprint(flac_file):
    """
    Computes the MD5 fingerprint of the raw audio data in the FLAC file.

    Args:
        flac_file (str): Path to the FLAC file.

    Returns:
        str: The computed MD5 fingerprint (as a hexadecimal string).
    NOTE: This does not detect errors when decoding. 
    """
    with sf.SoundFile(flac_file, 'r') as f:
        try:
            raw_audio_data = f.read(dtype='int16')
            raw_audio_bytes = raw_audio_data.tobytes()
            print("Sample rate:", f.samplerate)
            print("Channels:", f.channels)
            print("Frames:", f.frames)
            print("Duration (s):", f.frames / f.samplerate)
            #print("Extra info:" f.)
            print("Fingerprint:", hashlib.md5(raw_audio_bytes).hexdigest())
            #if 'extra_info' in sf.info(flac_file).:
            extra_info = sf.info(flac_file).extra_info
            #if extra_info:
            print("Error information:", extra_info)                
        except Exception as e:
            print(f"Error decoding FLAC file: {e}")
    return hashlib.md5(raw_audio_bytes).hexdigest()

class albumfolder:
    """class to hold a directory containing flac files, equivalent to an album or a concert. in some cases the flac files may be located in sub directories divided by discs"""
    def __init__ (self, location: str):
        self.location = location


class artistfolder:
    def __init__ (self, location: str):
        self.location = location

class md5:
    def __init__ (self, location: str, name: str, signatures: dict):
        self.location = location
        self.name = name
        #if signatures == {}:
        #    self.readffpfile()
        #else:
        self.signatures = signatures
        self.errors = []
        self.result = []

    def readmd5file(self):
        """split md5 file into dictionary with full file path as key and signature as value"""
        md5Name = f'{self.location}/{self.name}'
        msg = None
        md5_sigs = {}
        try: 
            md5 = open(md5Name, encoding="utf-8")
        except Exception as e:
            msg = f'Error reading file {md5Name}: {e}'
            print(msg)
            self.errors.append(msg)
            #logger.error(msg)
        #Attempt to read the first line of the ffp file to determine if it is not encoded using utf-8. If an error occurs, reopen without the encoding parameter.
        try:
            firstline = md5.readline()
            md5.close()
            md5 = open(md5Name, encoding="utf-8")
        except UnicodeDecodeError:
            md5.close()
            try: 
                md5 = open(md5Name)
            except Exception as e:
                msg = f'Error reading file {md5Name}: {e}'
                self.errors.append(msg)
                print(msg)
                #logger.error(msg)               
        try:
            for line in md5:
                    if not line.startswith(';') and ':' in line:
                        md5_line = line.strip().replace('\\','/')
                        md5_parts = md5_line[::-1].split(':',1)
                        md5_sigs[md5_parts[0][::-1]] = md5_parts[0][::-1]
                    else:
                        if not line.startswith(';') and '*' in line:
                            md5_line = line.strip().replace('\\','/')
                            md5_parts = md5_line[::-1].split('*',1)
                            md5_sigs[md5_parts[0][::-1].strip()] = md5_parts[1][::-1].strip()
                    print(md5_parts)
            self.signatures = md5_sigs
        except Exception as e:
            msg = f'Error reading file {md5Name}: {e}'
            #print(msg)
            self.errors.append(msg)
##################################################################
#FOLDER MANAGEMENT FUNCTIONS
##################################################################

def rename_child_folders_remove_x_segment(parent_folder):
    """
    For each immediate child folder of parent_folder, this function searches for any
    occurrence of a substring that matches the pattern: period, one or more 'x' or 'X', period.
    When such a substring is found, it is removed (i.e. replaced with a single period).
    
    For example:
        "artist.xx.2001-05-01.rest" becomes "artist.2001-05-01.rest"
        "band.X.X.track" becomes "band..track" which may then be further normalized
          if desired.
    
    The function renames the folders accordingly and returns two lists:
        - renamed: a list of tuples (old_folder_name, new_folder_name)
        - unmatched: a list of folder names that did not contain the pattern.
    
    Parameters:
        parent_folder (str): The path to the parent folder whose immediate child folders
                             will be processed.
    
    Returns:
        tuple: (renamed, unmatched)
    """
    renamed = []
    unmatched = []
    
    # Pattern to match a period, one or more x (case-insensitive), then a period.
    pattern = re.compile(r'\.[xX]+\.')

    for entry in os.listdir(parent_folder):
        entry_path = os.path.join(parent_folder, entry)
        if not os.path.isdir(entry_path):
            continue  # Process only directories

        # Check for the pattern.
        if pattern.search(entry):
            # Replace all occurrences of the pattern with a single period.
            new_name = pattern.sub('.', entry)
            # Only rename if the new name is different.
            if new_name != entry:
                new_path = os.path.join(parent_folder, new_name)
                try:
                    os.rename(entry_path, new_path)
                    renamed.append((entry, new_name))
                    print(f"Renamed: {entry} -> {new_name}")
                except Exception as e:
                    print(f"Error renaming {entry} to {new_name}: {e}")
            else:
                unmatched.append(entry)
        else:
            unmatched.append(entry)
    
    return renamed


def rename_child_folders_strip_leading_zeros(parent_folder):
    """
    Splits the given string on periods, and for any segment that consists solely
    of digits, converts it to an integer (thus removing leading zeros) and then back to a string.
    Finally, the segments are re-joined with periods.

    For example:
      "gd1991-03-31.99386.099386.Greensboro,NC.mtx.south.flac16"
    becomes:
      "gd1991-03-31.99386.99386.Greensboro,NC.mtx.south.flac16"
    """
    renamed = []
    for entry in os.listdir(parent_folder):
        entry_path = os.path.join(parent_folder, entry)
        if not os.path.isdir(entry_path):
            continue  # Skip if not a folder    
        segments = entry.split('.')
        print(segments)
        new_segments = []
        for seg in segments:
            if seg.isdigit():
                # Converting to int removes leading zeros, then back to string.
                newseg = str(seg).lstrip('0')
                if newseg not in new_segments:
                    new_segments.append(newseg)
            else:
                if seg not in new_segments:
                    new_segments.append(seg)
        new_name = '.'.join(new_segments)
        if new_name != entry:
                    new_path = os.path.join(parent_folder, new_name)
                    try:
                        os.rename(entry_path, new_path)
                        renamed.append((entry, new_name))
                        print(f"Renamed: {entry} -> {new_name}")
                    except Exception as e:
                        print(f"Error renaming {entry} to {new_name}: {e}")

    return renamed

def two_char_year_folder_fix(parent_folder):
    """
    Renames all direct child folders in parent_folder that start with an artist abbreviation
    followed by a date in the format 'yy-mm-dd' to a format with a four-digit year.
    
    For a folder matching:
      [ArtistAbbr][yy]-[mm]-[dd][rest]
    it will be renamed to:
      [ArtistAbbr][yyyy]-[mm]-[dd][rest]
    
    The two-digit year is converted using this heuristic:
      if int(yy) < 50, then yyyy = "20" + yy; else yyyy = "19" + yy.
    
    Folders that already match the four-digit pattern (e.g. ArtistAbbryyyy-mm-dd...) are skipped.
    Any folders that do not match either pattern are collected in a list.
    
    Parameters:
        parent_folder (str): The folder in which to process child directories.
    
    Returns:
        tuple: Two lists:
            - renamed: list of tuples (old_name, new_name) for each renamed folder.
            - unmatched: list of folder names that did not match either pattern.
    """
    # Pattern for two-digit year e.g. "gd87-01-28.rest..."
    pattern_2digit = re.compile(r'^(?P<abbr>[A-Za-z]+)(?P<yy>\d{2})-(?P<mm>\d{2})-(?P<dd>\d{2})(?P<rest>.*)$')
    # Pattern for four-digit year e.g. "gd1987-01-28.rest..."
    pattern_4digit = re.compile(r'^(?P<abbr>[A-Za-z]+)(?P<yyyy>\d{4})-(?P<mm>\d{2})-(?P<dd>\d{2})(?P<rest>.*)$')
    
    renamed = []
    unmatched = []
    
    # Process only direct children (non-recursive)
    for entry in os.listdir(parent_folder):
        entry_path = os.path.join(parent_folder, entry)
        if not os.path.isdir(entry_path):
            continue  # skip non-directories
        
        # Check for four-digit year pattern first.
        if pattern_4digit.match(entry):
            # Already in correct format; skip renaming.
            continue
        
        m = pattern_2digit.match(entry)
        if m:
            abbr = m.group("abbr")
            yy = m.group("yy")
            mm = m.group("mm")
            dd = m.group("dd")
            rest = m.group("rest")
            
            # Use a heuristic to convert two-digit year to four digits.
            # Here, if int(yy) < 50 we assume 2000+; otherwise, 1900+.
            year_int = int(yy)
            if year_int < 50:
                yyyy = "20" + yy
            else:
                yyyy = "19" + yy
            
            new_name = f"{abbr}{yyyy}-{mm}-{dd}{rest}"
            new_path = os.path.join(parent_folder, new_name)
            
            try:
                print(f"Renaming: {entry} -> {new_name}")
                os.rename(entry_path, new_path)
                renamed.append((entry, new_name))
            except Exception as e:
                print(f"Error renaming {entry} to {new_name}: {e}")
        else:
            unmatched.append(entry)
    
    return renamed, unmatched

def foldercleanup(parentdirectory):
    """
    call all of the cleanup functions on new folders. 
    """
    parentdirectory = Path(parentdirectory).as_posix()

    #print(f'{ren=}, {unmatch=}')
    ren = rename_child_folders_strip_leading_zeros(parentdirectory)
    for orig,new in ren:
        print(f'Renamed: {orig} to {new}')

    ren, unmatch = two_char_year_folder_fix(parentdirectory)
    for folder in ren:
        print(f'Renamed: {folder}')

    for folder in unmatch:
        print(f'Unable to rename: {folder}')

    rename_child_folders_remove_x_segment(parentdirectory)

#pd = r'X:\Downloads\_FTP\gdead.1967.project'
#pd = r"X:\Downloads\_FTP\gdead.1975.project"
#rename_child_folders_remove_x_segment(pd)
#foldercleanup(pd)