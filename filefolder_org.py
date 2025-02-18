"""This module is not intended for execution. It contains functions shared between other modules that are used in file management"""
import os
import sys
import tomllib
from pathlib import Path
import csv
import logging
import sys
import shutil

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

def replace_in_folder_names(directory, find_str, replace_str):
    for root, dirs, filenames in os.walk(directory):
        for dir in dirs:
            if find_str in dir:
                new_dir = dir.replace(find_str, replace_str)
                old_path = os.path.join(root, dir)
                new_path = os.path.join(root, new_dir)
                os.rename(old_path, new_path)
                print(f"Renamed: {dir} -> {new_dir}")            
            #print(f'{root=} {dir=}')

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

# Example usage:
#if __name__ == "__main__":
    #folder_name = "path/to/your/folder"  # Replace with your target folder
    #exts = get_file_extensions(folder_name)
    #print("Found file extensions:", exts)


def main():
    print('Not gonna do it!')

# --------------------------
# Example usage:
# flatten_immediate_subdirectories("X:/MyParentFolder")
# --------------------------



    


