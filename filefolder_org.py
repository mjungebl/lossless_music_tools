"""This module is not intended for execution. It contains functions shared between other modules that are used in file management"""
import os
import sys
import tomllib
from pathlib import Path
import csv
import logging
import sys
import shutil
from typing import List, Union
def load_config(config_name):
    with open(config_name, "rb") as f:
        #config = toml.load(f)
        config = tomllib.load(f)
        return config
config_file = os.path.join(os.path.dirname(__file__),"config.toml")
config = load_config(config_file)

"""
Path to artist exceptions. This file will map artist names to the artist folder name when there is a variation. 
Example: Bruce Springsteen & The E Street Band,Bruce Springsteen
"""
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
    #DirectoryName = DirectoryName.replace('\\','/')
    while DirectoryName[-1:] in ['/']:
        DirectoryName = DirectoryName[:len(DirectoryName)-1]    
    return Path(DirectoryName).as_posix()

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
            #print('Exception keys:',excpt.keys(),'|'+reldir[0:reldir.find(' - ')]+'|')
            if reldir[0:reldir.find(' - ')] in excpt.keys():
                reldir = excpt[reldir[0:reldir.find(' - ')]]
            else:
                reldir = reldir[0:reldir.find(' - ')]
        else:
            reldir = None
        directorymap[folder] = reldir
    return directorymap

def get_concert_subfolders(dirnm,folderlst, excpt = {}):
    """for live recordings move the folders in the respective year subfolders"""
    #To Do: make this more robust for multipl artists
    directorymap = {}
    for folder in folderlst:
        reldir = remove_path_from_dir_name(dirnm,folder)
        if reldir.startswith(('gd','ph','jg')) and reldir[2:6].isdigit() and len(reldir) > 6:
            reldir = f"{dirnm}/{reldir[0:6].lower()}"
            #print('Exception keys:',excpt.keys(),'|'+reldir[0:reldir.find(' - ')]+'|')
            #if reldir[0:reldir.find(' - ')] in excpt.keys():
            #    reldir = excpt[reldir[0:reldir.find(' - ')]]
            #else:
            #    reldir = reldir[0:reldir.find(' - ')]
        else:
            reldir = None
        directorymap[folder] = reldir
    return directorymap

def load_artist_exceptions(filenm):
    """Load the artist exceptions file. Used when an artist should be mapped to a different subfolder"""
    exceptions = {}
    with open(filenm) as f:
        reader = csv.reader(f, skipinitialspace=True)
        for row in reader:
            #Ensure there are at least two fields
            if len(row) >= 2:
                key, val = row[0], row[1]
                exceptions[key] = val
                #print(f"Key: {key}, Value: {val}")
            else:
                print(f"Skipping invalid row: {row}")        
        reader = csv.reader(f, skipinitialspace=True)
    return exceptions
 

def replace_in_file_names(directory, find_str, replace_str):
    """
    Renames files in a directory by replacing a string in the filename.

    Args:
        directory: The directory containing the files to rename.
        find_str: The string to find in the filenames.
        replace_str: The string to replace the find_str with.
    """

    for root, dirs, filenames in os.walk(directory):
        #print(filename)
        for filename in filenames:
            if find_str in filename:
                new_filename = filename.replace(find_str, replace_str)
                old_path = os.path.join(root, filename)
                new_path = os.path.join(root, new_filename)
                os.rename(old_path, new_path)
                print(f"Renamed: {filename} -> {new_filename}")

def replace_in_folder_names(directory:str, find_str:str, replace_str:str):
    """
    Renames folders in a directory by replacing a string in the folder.

    Args:
        directory: The directory containing the folders to rename.
        find_str: The string to find in the filenames.
        replace_str: The string to replace the find_str with.
    """
    print(f"Replacing '{find_str}' with '{replace_str}' in folder names under: {directory}")
    for root, dirs, filenames in os.walk(directory):
        for dir in dirs:
            if find_str in dir:
                try:
                    new_dir = dir.replace(find_str, replace_str)
                    new_dir = new_dir.strip()
                    old_path = os.path.join(root, dir)
                    new_path = os.path.join(root, new_dir)
                    os.rename(old_path, new_path)
                    print(f"Renamed: {dir} -> {new_dir}")
                except Exception as e:
                    print(f'Error renaming {dir}: {e}')          
            print(f'{root=} {dir=}')

def reset_logger():
    """Stop logging to any old file and start logging to new_log_file."""
    # 1) Shut down the current logging system
    logging.shutdown()

    # 2) Remove all handlers associated with the root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)



def flatten_immediate_subdirectories():
    dir_path = str(sys.argv[1])
    """
    For each *immediate* subdirectory of `dir_path`, if that subdirectory
    contains one or more subfolders, move *all* of its contents (files and
    subfolders) up into `dir_path`. Only remove the subdirectory if it is
    verified empty after the move.

    :param dir_path: Path to the parent directory in which to flatten subdirectories
    :raises ValueError: If dir_path does not exist
    """

    # 1. Ensure the directory path exists
    if not os.path.isdir(dir_path):
        raise ValueError(f"Directory does not exist: {dir_path}")

    # 2. Scan immediate children of dir_path
    for entry in os.scandir(dir_path):
        
        if entry.is_dir():
            subdir_path = entry.path

            # Check if subdir contains at least one directory
            has_subfolders = False
            for item in os.scandir(subdir_path):
                if item.is_dir():
                    has_subfolders = True
                    break

            # If the subdirectory has subfolders, move all contents
            if has_subfolders:
                # Move items that still exist at the time of moving
                for item_name in os.listdir(subdir_path):
                    old_item = os.path.join(subdir_path, item_name)
                    new_item = os.path.join(dir_path, item_name)
                    if os.path.exists(new_item):
                        print(f"ERROR: Skipping {old_item}, {new_item} Exists!")
                        break
                    else:
                        print(f"Moving {old_item} -> {new_item}")
                        shutil.move(old_item, new_item)
                    #else:
                    #    print(f"Skipping move: {old_item} no longer exists.")

                # After attempting to move everything, check if subdir is empty
                if not os.listdir(subdir_path):
                    print(f"Removing empty directory: {subdir_path}")
                    os.rmdir(subdir_path)
                else:
                    print(f"Subdirectory not empty, skipping removal: {subdir_path}")
       
    if not os.listdir(dir_path):
         print(f"Removing empty directory: {dir_path}")
        #os.rmdir(subdir_path)
    else:
        print(f"Subdirectory not empty, skipping removal: {subdir_path}")

def get_files_by_extension(folder, ext):
    """
    Returns a list of filenames in the specified folder that have the given extension.
    
    Parameters:
        folder (str): The directory in which to search for files.
        ext (str): The file extension to filter by (e.g., "flac" or ".flac").
    
    Returns:
        list: A list of filenames (not full paths) that end with the specified extension.
    """
    # Ensure the extension starts with a dot
    if not ext.startswith('.'):
        ext = '.' + ext

    # Get all entries in the folder and filter by file type and extension
    filenames = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f)) and f.lower().endswith(ext.lower())
    ]
    
    return filenames


def copy_files_by_extension_recursive(source_folder, target_folder, extension):
    """
    Recursively copies all files with the specified extension from source_folder
    to target_folder while preserving the directory structure.

    Parameters:
        source_folder (str): The root directory to search for files.
        target_folder (str): The destination root directory where files will be copied.
        extension (str): The file extension to filter by (e.g., "txt" or ".txt").
    
    Example:
        copy_files_by_extension_recursive("data", "backup", "txt")
    """
    # Ensure the extension starts with a dot
    if not extension.startswith('.'):
        extension = '.' + extension

    for dirpath, dirnames, filenames in os.walk(source_folder):
        for filename in filenames:
            if filename.lower().endswith(extension.lower()):
                # Full source file path
                src_file = os.path.join(dirpath, filename)
                # Determine the relative directory path from the source folder
                rel_dir = os.path.relpath(dirpath, source_folder)
                # Determine the destination directory
                dst_dir = os.path.join(target_folder, rel_dir)
                os.makedirs(dst_dir, exist_ok=True)
                # Destination file path
                dst_file = os.path.join(dst_dir, filename)
                print(f"[COPY {extension.upper()}] {src_file} => {dst_file}")
                shutil.copy2(src_file, dst_file)


def get_file_extensions(folder):
    """
    Recursively retrieves a sorted list of unique file extensions found in the given folder.
    
    Parameters:
        folder (str): The root directory to search.
    
    Returns:
        list: A sorted list of unique file extensions (in lowercase, including the dot).
              Files without an extension are represented as an empty string.
    """
    extensions = set()
    for root, dirs, files in os.walk(folder):
        for filename in files:
            # os.path.splitext returns a tuple (root, ext) where ext includes the dot
            ext = os.path.splitext(filename)[1].lower()
            extensions.add(ext)
    return sorted(extensions)

def read_nonempty_lines(file_path):
    """
    Reads a text file and returns a list of all non-empty lines.
    
    A line is considered non-empty if it contains any non-whitespace characters.
    
    Args:
        file_path (str): The path to the text file.
    
    Returns:
        list: A list of non-empty lines (with trailing newline characters removed).
    """
    nonempty_lines = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():  # Checks if line has non-whitespace characters.
                nonempty_lines.append(line.rstrip("\n"))
    return nonempty_lines


def find_zero_length_flacs(root_dir: str) -> List[Path]:
    r"""
    Traverse the directory tree rooted at `root_dir` and return a list of 
    Path objects pointing to any .flac files of size 0 bytes.

    Parameters:
        root_dir (str): Path to the top‐level folder to scan 
                        (e.g., r"X:\Music\Kitchen\4TB").

    Returns:
        List[Path]: A list of pathlib.Path objects for each zero‐byte .flac found.
    """
    zero_length_files: List[Path] = []
    root = Path(root_dir)

    # Recursively search for “*.flac” anywhere under root
    for flac_path in root.rglob("*.flac"):
        #print(f"Checking: {flac_path}")
        try:
            if flac_path.stat().st_size == 0:
                zero_length_files.append(flac_path)
        except (OSError, IOError):
            # If we can’t stat the file (permissions, broken link, etc.), skip it
            continue

    return zero_length_files



def sort_file_lines(file_path: Path) -> Path:
    """
    Read a text file, sort its lines alphabetically, and write out a new file
    with '_sorted' appended before the extension.

    If the file contains non-UTF-8 bytes, it will ignore them rather than error.
    """
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    sorted_file = file_path.with_name(f"{file_path.stem}_sorted{file_path.suffix}")
    if sorted_file.exists():
        raise FileExistsError(f"Cannot overwrite existing file: {sorted_file}")

    # Read, with a fallback on decode errors
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = file_path.read_text(encoding="utf-8", errors="ignore")

    lines = text.splitlines()
    lines.sort()

    # Write back (ensure trailing newline)
    sorted_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sorted_file


def remove_trailing_chars_from_folder(path: str, n: int) -> str:
    """
    Rename the folder at `path`, removing the last `n` characters
    from its name.

    Parameters:
        path (str): Full path to the existing folder.
        n (int): Number of characters to strip off the end of the folder’s name.

    Returns:
        str: The new full path of the renamed folder.

    Raises:
        FileNotFoundError: If `path` does not exist or isn’t a directory.
        ValueError: If `n` is negative or >= length of the folder name.
        OSError: If the rename operation fails (e.g. permissions).
    """
    if not os.path.isdir(path):
        raise FileNotFoundError(f"No such directory: {path}")

    parent, name = os.path.split(path)
    if n < 0 or n >= len(name):
        raise ValueError(f"Cannot remove {n} chars from '{name}'")

    new_name = name[:-n]
    new_path = os.path.join(parent, new_name)

    os.rename(path, new_path)
    return new_path

def find_folders_ending_with(base_dir: str, suffix: str = "-001"):
    base = Path(base_dir)
    return [
        p for p in base.iterdir()
        if p.is_dir() and p.name.endswith(suffix)
    ]

def is_directory_empty(path: Union[str, Path]) -> bool:
    """
    Check whether the directory at `path` is empty.

    Parameters:
        path (str | Path): Path to the directory to check.

    Returns:
        bool: True if the directory exists and contains no files or subdirectories; False otherwise.

    Raises:
        FileNotFoundError: If `path` does not exist.
        NotADirectoryError: If `path` exists but is not a directory.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No such path: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {p}")

    # Option A: pathlib
    return next(p.iterdir(), None) is None

    # — or —

    # Option B: os.scandir (a bit faster on large dirs)
    # with os.scandir(p) as it:
    #     for _ in it:
    #         return False
    # return True


def list_directories_recursive_pathlib(base_dir: str) -> List[Path]:
    """
    Return a list of all subdirectory Path objects under base_dir (recursively).

    Parameters:
        base_dir (str): Root directory to scan.

    Returns:
        List[Path]: Path objects for each subdirectory beneath base_dir.
    """
    base = Path(base_dir)
    if not base.is_dir():
        raise NotADirectoryError(f"Not a directory: {base}")

    # rglob('*') finds all files & dirs; filter to dirs only
    return [p for p in base.rglob('*') if p.is_dir()]


def delete_directory_if_empty(path: Union[str, Path]) -> bool:
    """
    Delete the directory at `path` only if it is empty.

    Parameters:
        path (str | Path): The directory to delete.

    Returns:
        bool: True if the directory was empty and successfully deleted; False if it existed but was not empty.

    Raises:
        FileNotFoundError: If `path` does not exist.
        NotADirectoryError: If `path` exists but is not a directory.
        OSError: If deletion fails unexpectedly (e.g., permissions).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No such path: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {p}")

    # Use your existing empty-check
    if is_directory_empty(p):
        p.rmdir()  # removes the directory
        return True
    else:
        return False


def main():
    print('Not gonna do it!')

# --------------------------
# Example usage:
# flatten_immediate_subdirectories("X:/MyParentFolder")
# --------------------------


if __name__ == "__main__":
    main()
    # zero_length_files = find_zero_length_flacs(r"X:\Music\Kitchen\4TB")
    # print(zero_length_files)
    # folder = r'X:\Downloads\_Extract\_Batch\Phish'
    # replace_in_folder_names(folder,'.CA.',',.CA.')    
    # replace_in_folder_names(folder,'.',' ')
    # replace_in_folder_names(folder,'FLAC16-WEEKaPAuG','')
    # replace_in_folder_names(folder,' FLAC24-WEEKaPAuG',' [24-48]')
    # replace_in_folder_names(folder,'Phish-','Phish - ')
    # folder = r"X:\Downloads\_Zips\ETR\Grateful Dead - Enjoying The Ride (2025)"
    # replace_in_folder_names(folder,'Enjoying the Ride ','')
    # replace_in_folder_names(folder,' [FLAC16]','')
    # replace_in_folder_names(folder,' [Flac]','')
    # replace_in_folder_names(folder,' [flac]','')
    # replace_in_folder_names(folder,'[FLAC]','')
    # replace_in_folder_names(folder,'[Flac]','')
    # replace_in_folder_names(folder,'[flac]','')
    # replace_in_folder_names(folder,' FLAC','')
    # replace_in_folder_names(folder,' [HDCD]','')
    # replace_in_folder_names(folder,'[HDCD]','')
    #[HDCD]
    folder = r'X:\Downloads\_FTP\_Incoming\FLAC'
    #folder = r'X:\Downloads\_Extract\_Batch\_PlayDead\New_Shows'
    #folder = r'X:\Video\Video_DVD_4TB\Videos\Music\Phish\Bakers Dozen'
    #replace_in_file_names(folder,'UntouchedTrimmedCH.','')
    #replace_in_file_names(folder,'ph2017.07.','Phish - 2017-07-')
    replace_in_folder_names(folder,'.',' ')
    #replace_in_folder_names(folder,'treyanastasio','Trey Anastasio - ')
    #replace_in_folder_names(folder,' nugs flac16441','')
    # folder = r'X:\Downloads\_Extract\_Batch\Phish'
    # replace_in_folder_names(folder,'.',' ')
    replace_in_folder_names(folder,'FLAC16-WEEKaPAuG','')
    replace_in_folder_names(folder,'-must4rd','')
    # replace_in_folder_names(folder,'Phish-','Phish - ')
    # folder = r'X:\Music\Studios\Studios\Talking Heads'
    replace_in_folder_names(folder,' [FLAC]','')
    replace_in_folder_names(folder,'FLAC24-96','[24-96]')
    replace_in_folder_names(folder,'FLAC24-48','[24-48]')
    replace_in_folder_names(folder,'Phil Lesh & Friends 2007','Phil Lesh & Friends - 2007')
    # flac1644
    replace_in_folder_names(folder,' flac1644','')
    replace_in_folder_names(folder,' nugs','')
    # replace_in_folder_names(folder,' [flac]','')
    #Phish-
    # replace_in_folder_names(folder,'Trey Anastasio-','Trey Anastasio - ')
    # replace_in_folder_names(folder,'Trey Anastasio Band-','Trey Anastasio - ')
    # replace_in_folder_names(folder,'Trey Anastasio Band - ','Trey Anastasio - ')
    # folder = r'X:\Downloads\_Extract\_Batch\Leftover Salmon'
    # replace_in_folder_names(folder,' [FLAC16]','')
    # replace_in_folder_names(folder,'Leftover Salmon ','Leftover Salmon - ')
    #replace_in_file_names(r"V:\String Cheese Incident\String Cheese Incident - 2022-07-17 - Red Rocks Amphitheatre, Morrison, CO",' - 2022-07-17 - Red Rocks Ampitheatre, Morrison, CO - The String Cheese Incident - The String Cheese Incident','')
    #sort_file_lines(Path('zero_fingerprint_flacs_12TB.txt'))
    #replace_in_file_names(r"X:\Downloads\_Mega\Grateful Dead\Grateful Dead - Enjoying the Ride (2025)","( ","(")
    
    # renames = find_folders_ending_with(r"X:\Downloads\_Zips\Phish","-002")
    # print(renames)
    # trim_n = len("-20250509T030621Z-1-001")
    # for name in renames:
    #     new_name = remove_trailing_chars_from_folder(name, trim_n)
    #     print(f"Renamed {name} to {new_name}")

# CLEAN UP EMPTY DIRECTORIES UNDER A PARENT FOLDER
    # dirs = list_directories_recursive_pathlib(r"X:\Downloads\_Zips\Phish")
    # for x in dirs:
    #     empty = is_directory_empty(x)
    #     if empty:
    #         print(f"Empty directory: {x}")
    #         delete_directory_if_empty(x)

    # folder = r'X:\Downloads\_Zips\Phish'
    # replace_in_folder_names(folder,'phish','ph')
