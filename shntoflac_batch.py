#!/usr/bin/env python3

"""
Usage:
  python shn_to_flac_compare_st5.py <source_parent> <destination_parent>

What it does:
  1) For each folder with .shn in <source_parent>:
     - Generate an ST5 for the .shn using "shntool.exe hash -m *.shn > folderName.shn.st5"
  2) Multi-threaded .shn -> .flac conversion, placing .flac in a renamed folder under <destination_parent>.
     - If ".shnf" is in the folder name, replace it with ".flac16"
       else append ".flac16"
  3) Copies any .txt files from source folder to the target folder
  4) Generate ST5 from the new .flac in the target folder using
     "shntool.exe hash -m *.flac > folderName.flac.st5"
  5) Compare the two ST5 files line-by-line (the .shn ST5 from source,
     the .flac ST5 in target) and append the results to "verification.log"
     in the root of <destination_parent>.

Requirements:
  - Python 3.11+ or 'pip install tomli' for older Pythons
  - A config.toml with e.g.:
      [supportfiles]
      shorten = "L:/Flac/shorten.exe"
      flac    = "L:/Flac/flac.exe"
      shntool = "L:/Flac/shntool.exe"
  - shorten.exe, flac.exe, shntool.exe must be valid executables.
"""

import sys
import os
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor

# For Python 3.11+, 'import tomllib' is built in.
# For older Pythons: 'pip install tomli' => 'import tomli as tomllib'
import tomllib


###############################################################################
# Folder Name Transformation
###############################################################################

def transform_subfolder_name(source_parent: str, folder: str) -> str:
    """
    For the 'folder' path under 'source_parent', modifies its last segment:
      - If ".shnf" is in the last segment, replace it with ".flac16"
      - Else append ".flac16"
    Returns the resulting relative path.
    """
    relative_subpath = os.path.relpath(folder, source_parent)
    segments = relative_subpath.split(os.sep)
    last_segment = segments[-1]

    if ".shnf" in last_segment:
        last_segment = last_segment.replace(".shnf", ".flac16")
    else:
        last_segment += ".flac16"

    segments[-1] = last_segment
    return os.sep.join(segments)


###############################################################################
# Config
###############################################################################

def parse_config(config_path: str):
    """Reads config.toml => paths for shorten.exe, flac.exe, shntool.exe."""
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"config.toml not found at {config_path}")

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    shorten_exe = config["supportfiles"]["shorten"]
    flac_exe    = config["supportfiles"]["flac"]
    shntool_exe = config["supportfiles"]["shntool"]
    return shorten_exe, flac_exe, shntool_exe


###############################################################################
# SHN -> WAV -> FLAC
###############################################################################

def decode_shn_to_wav(shorten_exe: str, shn_path: str, wav_path: str):
    """Decode .shn => .wav (shorten.exe -x)."""
    cmd = [shorten_exe, "-x", shn_path, wav_path]
    subprocess.run(cmd, check=True)

def encode_wav_to_flac(flac_exe: str, wav_path: str, flac_path: str):
    """Encode .wav => .flac (flac.exe wav_path -o flac_path)."""
    cmd = [flac_exe, wav_path, "-o", flac_path]
    subprocess.run(cmd, check=True)

def convert_one_shn_file(shorten_exe, flac_exe, source_parent, dest_parent,
                         src_folder, shn_filename):
    """
    Convert one .shn => .flac in the renamed folder under <dest_parent>.
    Return True on success, False otherwise.
    """
    shn_path = os.path.join(src_folder, shn_filename)

    # Build the renamed target folder
    rel_transformed = transform_subfolder_name(source_parent, src_folder)
    out_dir = os.path.join(dest_parent, rel_transformed)
    os.makedirs(out_dir, exist_ok=True)

    base_name = os.path.splitext(shn_filename)[0]
    flac_path = os.path.join(out_dir, base_name + ".flac")

    # if flac already exists => skip
    if os.path.exists(flac_path):
        print(f"[SKIP] FLAC exists => {flac_path}")
        return True

    wav_path = os.path.join(out_dir, base_name + ".wav")

    print(f"\n[THREAD] Converting:\n  SHN : {shn_path}\n  WAV : {wav_path}\n  FLAC: {flac_path}")

    # decode
    try:
        decode_shn_to_wav(shorten_exe, shn_path, wav_path)
        # encode
        encode_wav_to_flac(flac_exe, wav_path, flac_path)
    except subprocess.CalledProcessError as e:
        print(f"Error converting {shn_path}: {e}")
        if os.path.exists(flac_path):
            os.remove(flac_path)
        return False
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)

    return True


###############################################################################
# GATHER .shn
###############################################################################

def gather_shn_files_by_folder(source_parent):
    """
    Return {folder: [list_of_shn_filenames]} for subdirs with .shn
    """
    shn_dict = {}
    for dirpath, dirnames, filenames in os.walk(source_parent):
        shn_files = [f for f in filenames if f.lower().endswith(".shn")]
        if shn_files:
            shn_dict[dirpath] = shn_files
    return shn_dict


###############################################################################
# ST5 for SHN, ST5 for FLAC, then compare
###############################################################################

def generate_st5_for_shn(shntool_exe: str, folder: str, st5_filename: str):
    """
    In 'folder', run:
      shntool.exe hash -m *.shn > st5_filename
    capturing stdout => st5_filename.
    """
    cmd = [
        shntool_exe,
        "hash",
        "-m",
        "*.shn"
    ]
    st5_path = os.path.join(folder, st5_filename)
    print(f"[ST5 from SHN] {folder} => {st5_filename}")
    proc = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    with open(st5_path, "w", encoding="utf-8") as f:
        f.write(proc.stdout)
    return (st5_path, proc.returncode)

def generate_st5_for_flac(shntool_exe: str, folder: str, st5_filename: str):
    """
    In 'folder', run:
      shntool.exe hash -m *.flac > st5_filename
    capturing stdout => st5_filename.
    """
    cmd = [
        shntool_exe,
        "hash",
        "-m",
        "*.flac"
    ]
    st5_path = os.path.join(folder, st5_filename)
    print(f"[ST5 from FLAC] {folder} => {st5_filename}")
    proc = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    with open(st5_path, "w", encoding="utf-8") as f:
        f.write(proc.stdout)
    return (st5_path, proc.returncode)

def compare_st5_files(st5_shn_path: str, st5_flac_path: str) -> list[str]:
    """
    Compares wave-based MD5 lines from shn vs flac ST5 files, returning a list of
    result strings. For lines with matching MD5, logs a single-line "MATCH" entry.
    For differences or errors, logs a multi-line entry with details.

    Example ST5 line format from shntool:
      b8e748d6698bfe2847ebddee6d77633d  [shntool]  gd66-01t01.shn
    """

    import os
    
    results = []

    # Check files
    if not os.path.isfile(st5_shn_path):
        results.append(f"[ERROR] Missing SHN ST5 file: {st5_shn_path}")
        return results
    if not os.path.isfile(st5_flac_path):
        results.append(f"[ERROR] Missing FLAC ST5 file: {st5_flac_path}")
        return results

    # Read lines
    with open(st5_shn_path, "r", encoding="utf-8") as f:
        shn_lines = [line.strip() for line in f if line.strip()]
    with open(st5_flac_path, "r", encoding="utf-8") as f:
        flac_lines = [line.strip() for line in f if line.strip()]

    max_len = max(len(shn_lines), len(flac_lines))

    def parse_st5_line(line: str):
        """
        Splits ST5 line into (md5, filename).
        Example:
          "b8e748d6698bfe2847ebddee6d77633d  [shntool]  gd66-01t01.shn"
        => md5="b8e748d6698bfe2847ebddee6d77633d", filename="gd66-01t01.shn"
        """
        tokens = line.split(None, 2)
        if len(tokens) == 0:
            return ("", "")
        if len(tokens) == 1:
            return (tokens[0], "")
        if len(tokens) == 2:
            return (tokens[0], tokens[1])
        # tokens[2] presumably the filename
        md5 = tokens[0]
        filename = tokens[2]
        return (md5, filename)

    for i in range(max_len):
        shn_line = shn_lines[i] if i < len(shn_lines) else "[no line]"
        flac_line = flac_lines[i] if i < len(flac_lines) else "[no line]"

        shn_md5, shn_fname = parse_st5_line(shn_line)
        flac_md5, flac_fname = parse_st5_line(flac_line)

        # If either MD5 is missing, that's a difference
        if not shn_md5 or not flac_md5:
            results.append(
                f"Line {i+1} differs:\n"
                f"  SHN line : {shn_line}\n"
                f"  FLAC line: {flac_line}\n"
            )
            continue

        if shn_md5 == flac_md5:
            # Single-line match log
            results.append(
                f"Line {i+1} MATCH: MD5={shn_md5} | SHN={shn_fname} | FLAC={flac_fname}"
            )
        else:
            # Multi-line difference
            results.append(
                f"Line {i+1} differs:\n"
                f"  SHN => {shn_md5}  {shn_fname}\n"
                f"  FLAC => {flac_md5} {flac_fname}\n"
            )

    return results



###############################################################################
# MAIN
###############################################################################

def main():
    if len(sys.argv) < 3:
        print("Usage: python shn_to_flac_compare_st5.py <source_parent> <destination_parent>")
        sys.exit(1)

    source_parent = sys.argv[1]
    dest_parent   = sys.argv[2]

    if not os.path.isdir(source_parent):
        print(f"Source directory not found: {source_parent}")
        sys.exit(1)

    # config
    config_path = os.path.join(os.path.dirname(__file__), "config.toml")
    try:
        shorten_exe, flac_exe, shntool_exe = parse_config(config_path)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    print("Using shorten.exe:", shorten_exe)
    print("Using flac.exe:",    flac_exe)
    print("Using shntool.exe:", shntool_exe)

    # Gather .shn
    shn_dict = gather_shn_files_by_folder(source_parent)
    if not shn_dict:
        print("No .shn files found, exiting.")
        return

    # 1) Generate ST5 from .shn in each source folder
    st5_shn_map = {}  # folder => path to .shn st5
    for folder, shn_files in shn_dict.items():
        folder_name = os.path.basename(folder)
        st5_filename = folder_name + ".shn.st5"
        st5_path, rc = generate_st5_for_shn(shntool_exe, folder, st5_filename)
        st5_shn_map[folder] = st5_path
        if rc != 0:
            print(f"[ST5 WARN] Return code {rc} for .shn st5 in {folder}")

    # 2) Multi-threaded conversion
    futures = []
    success_count = 0
    fail_count    = 0
    max_workers   = 4

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for folder, shn_files in shn_dict.items():
            for shn_fn in shn_files:
                fut = executor.submit(
                    convert_one_shn_file,
                    shorten_exe,
                    flac_exe,
                    source_parent,
                    dest_parent,
                    folder,
                    shn_fn
                )
                futures.append((folder, shn_fn, fut))

        for (folder, shn_fn, fut) in futures:
            try:
                ok = fut.result()
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as ex:
                print(f"[THREAD ERROR] {folder}/{shn_fn}: {ex}")
                fail_count += 1

    print(f"\n[RESULTS] SHN->FLAC done. success={success_count}, fail={fail_count}")

    # 3) Copy .txt, generate ST5 for .flac in target, compare with .shn ST5
    verification_log = os.path.join(dest_parent, "verification.log")
    with open(verification_log, "a", encoding="utf-8") as lf:
        lf.write("\n====== FLAC vs SHN ST5 Comparison ======\n")

    for folder in shn_dict.keys():
        # The renamed target folder
        rel_transformed = transform_subfolder_name(source_parent, folder)
        tgt_folder = os.path.join(dest_parent, rel_transformed)
        if not os.path.isdir(tgt_folder):
            continue

        # Copy any .txt
        txt_files = [f for f in os.listdir(folder) if f.lower().endswith(".txt")]
        for txtf in txt_files:
            src_txt = os.path.join(folder, txtf)
            dst_txt = os.path.join(tgt_folder, txtf)
            print(f"[COPY TXT] {src_txt} => {dst_txt}")
            shutil.copy2(src_txt, dst_txt)

        # 3a) Generate ST5 for .flac in target
        folder_name = os.path.basename(tgt_folder)
        st5_flac_filename = folder_name + ".flac.st5"
        st5_flac_path, rc2 = generate_st5_for_flac(shntool_exe, tgt_folder, st5_flac_filename)
        if rc2 != 0:
            print(f"[ST5 WARN] Return code {rc2} for .flac st5 in {tgt_folder}")

        # 3b) Compare with the .shn st5 if it exists
        st5_shn_path = st5_shn_map.get(folder)  # path to the .shn st5 in source
        with open(verification_log, "a", encoding="utf-8") as lf:
            lf.write(f"\n--- Comparing .shn ST5 vs .flac ST5 for folder: {folder}\n")
            if not st5_shn_path or not os.path.isfile(st5_shn_path):
                lf.write("[SKIP] No .shn ST5 found.\n")
            elif not os.path.isfile(st5_flac_path):
                lf.write("[SKIP] .flac ST5 not found.\n")
            else:
                diffs = compare_st5_files(st5_shn_path, st5_flac_path)
                if diffs:
                    for d in diffs:
                        lf.write(d + "\n")
                else:
                    lf.write("[OK] No differences. (unlikely for compressed data)\n")

    print(f"\nAll done. Full verification => {verification_log}")


################################################################################
# if you truly want to verify the underlying audio data, you'd typically do a wave-based
# approach (e.g. 'shntool hash -l *.shn' or 'flac -d' => raw wave cmp), which is not done here.
################################################################################

if __name__ == "__main__":
    if len(sys.argv) < 3:
        #print("Usage: python convert_shn_to_flac_with_shorten_multithreaded.py <source_parent> <destination_parent>")
        source = r"X:\Music\Concerts\Concerts_GD\Grateful_Dead\gd1974" #parent directroy to search for shns
        target = r"M:\ConvertSHN\Grateful_Dead\gd1974" #new parent directory
        sys.argv = ["shntoflac_batch.py",source,target]
    main()
    #print(compare_st5_files(r"M:\ConvertSHN\Grateful_Dead\gd1966\gd1966-01-xx.18846.sbd.hanno-uli.sbeok.flac16\gd1966-01-xx.18846.sbd.hanno-uli.sbeok.flac16.flac.st5","X:\Music\Concerts\Concerts_GD\Grateful_Dead\gd1966\gd1966-01-xx.18846.sbd.hanno-uli.sbeok.shnf\gd1966-01-xx.18846.sbd.hanno-uli.sbeok.shnf.shn.st5"))
