"""This script is for use in conjunction with Cuetools. 
Cuetools can convert an image/cue to individual flac files in a subdirectory (SplitFolderName).
This script will loop through all directories, remove the original files, replace them with the files in the new subdirectory,
and remove the subdirectory.
Currently this is designed to run manually from the editor after editing the SplitFolderName and rootdirectory variables.
Cuetools output "template"settings for "Encode":
[%directoryname%\]new[%unique%]\%filename%.cue
"""
import os
import shutil

os.system('chcp 1252') #windows only?

#to do change these to parameters
SplitFolderName = "new"
#rootdirectory = f'X:/Downloads/_Extract/Artist - Album Name'
rootdirectory = "X:/Downloads/_Extract/_Batch/Frank Zappa - You Can't Do That On Stage Anymore Vol. 2 (1988) [Remaster]"


#Functions
def CheckForSplitFiles(DirectoryName, SplitName):
    folders = os.listdir(DirectoryName)
    NewFlacExists = False
    NewCueExists = False
    if SplitName in folders:
        newdir = os.path.join(DirectoryName,SplitName)
        newdirlist = os.listdir(newdir)
        for item in newdirlist:
            if item.lower().endswith(".flac"):
                NewFlacExists = True
            if item.lower().endswith(".cue"):
                NewCueExists = True
            if NewCueExists and NewFlacExists: #need to know we have both at a minimum. to do: change this to get a tuple and add list of files and folders to check for duplicates
                return True
    return False

def GetFilesToDelete(DirectoryName):
    FilesToDelete = []
    files = [f for f in os.listdir(DirectoryName) if os.path.isfile(os.path.join(DirectoryName,f))]
    for f in files:
        if f.lower().endswith(('.flac','.cue','.log','.accurip')):
            FilesToDelete.append(f)
    return FilesToDelete

def DeleteFiles(DirectoryName,FileList):
    for f in FileList:
        if os.path.isfile(os.path.join(DirectoryName,f)):
            os.remove(os.path.join(DirectoryName,f))

def MoveAllFiles(SourceDir,TargetDir):
    filelist = os.listdir(SourceDir)
    for f in filelist:
        src = os.path.join(SourceDir, f)
        tgt = os.path.join(TargetDir, f)
        shutil.move(src, tgt)

def main(DirectoryName):
    for root, dirs, files in os.walk(DirectoryName):
        for folder in dirs:
            currpath = os.path.join(root,folder)
            Split = CheckForSplitFiles(currpath,SplitFolderName)
            if Split:
                print("Moving split files into: " + currpath)
                DeleteFileList = GetFilesToDelete(currpath)
                if DeleteFiles:
                    DeleteFiles(currpath,DeleteFileList)
                MoveAllFiles(os.path.join(currpath,SplitFolderName),currpath)
                os.rmdir(os.path.join(currpath,SplitFolderName)) 

rootdirectory = rootdirectory.replace('\\','/')

while rootdirectory[-1:] in ['/']:
    rootdirectory = rootdirectory[:len(rootdirectory)-1]
main(rootdirectory)

#list_subfolders_with_paths = [f.path.replace('\\','/') for f in os.scandir(rootdirectory) if f.is_dir()]

#while list_subfolders_with_paths:
    #currdir = list_subfolders_with_paths.pop()
    #to do: change this to a function, pass in the root directory and remove the useless list_subfolders_with_paths


        