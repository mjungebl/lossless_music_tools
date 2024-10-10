This is a set of scripts that are intended to assist with managing a lossless music library.
The initial version contains scripts to generate flac fingerprint files when not present and to traverse a directory structure to verify the integrety of the signatures.

Typical usage would be to call the scripts from the command line. 
Currently these scripts support windows only.

Sample script:
set PYTHONIOENCODING=utf9
SET WORKPATH='%~dp0'
"E:\My Documents\GitHub\lossless_music_tools\.venv\Scripts\python.exe" "E:\My Documents\GitHub\lossless_music_tools\generate_ffp_checksums.py" "%WORKPATH%" > log.txt
"E:\My Documents\GitHub\lossless_music_tools\.venv\Scripts\python.exe" "E:\My Documents\GitHub\lossless_music_tools\check_all_ffp.py" %WORKPATH% >> log.txt
pause

These were initially put together due to shortcomings I encountered when using "Traders Little Helper", which include the following:
Poor support for unicode filenames, lack of a recursive verification of *.ffp files, and no external log file when a large number of files are verified.


