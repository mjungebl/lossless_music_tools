import os
import shutil
import subprocess
import logging
import toml
from pathlib import Path
from filefolder_org import fix_directory_name, get_child_directories, remove_empty_file, load_config
import multiprocessing

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Function to ensure the output directory exists
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def extract_metadata(input_file, metadata_file, cover_image_file, metaflac_path):
    """
    Attempt to export tags and cover artwork separately. Return a dict indicating
    which ones were successfully extracted:
      {
        "tags": True/False,
        "cover": True/False
      }
    """
    results = {"tags": False, "cover": False}

    # 1) Export text tags to metadata file
    #    - Do NOT raise an error if there's no tags; just note success/failure
    logging.info(f"Extracting TAGS from: {input_file}")
    proc_tags = subprocess.run(
        [metaflac_path, "--export-tags-to", metadata_file, input_file],
        capture_output=True,
        text=True
    )
    if proc_tags.returncode == 0 and os.path.exists(metadata_file):
        results["tags"] = True
        logging.info(f"Tags exported to: {metadata_file}")
    else:
        logging.info(f"No tags found or error extracting tags. Return code={proc_tags.returncode}")

    # 2) Export cover art to a separate file
    #    - Similarly, don’t raise an error if there's no cover
    logging.info(f"Extracting COVER from: {input_file}")
    proc_cover = subprocess.run(
        [metaflac_path, "--export-picture-to", cover_image_file, input_file],
        capture_output=True,
        text=True
    )
    if proc_cover.returncode == 0 and os.path.exists(cover_image_file):
        results["cover"] = True
        logging.info(f"Cover image extracted to: {cover_image_file}")
    else:
        logging.info(f"No cover image found or error extracting cover. Return code={proc_cover.returncode}")

    return results

def import_metadata(output_file, metadata_file, cover_image_file, metaflac_path, meta_info):
    """
    Import metadata into the newly encoded FLAC. meta_info is a dict that tells us
    whether tags or artwork were successfully extracted.
    """
    try:
        # If we found tags in the source file, import them
        if meta_info["tags"]:
            logging.info(f"Importing tags into: {output_file}")
            subprocess.run(
                [metaflac_path, "--import-tags-from", metadata_file, output_file],
                check=True
            )
        else:
            logging.info(f"No tags to import for: {output_file}")

        # If we found a cover image in the source file, import it
        if meta_info["cover"]:
            logging.info(f"Importing cover artwork into: {output_file}")
            subprocess.run(
                [metaflac_path, "--import-picture-from", cover_image_file, output_file],
                check=True
            )
        else:
            logging.info(f"No cover artwork to import for: {output_file}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to import metadata to {output_file}: {e}")
        raise

def process_single_flac(input_file, output_dir, flac_old_path, flac_new_path, metaflac_path, input_dir):
    """
    Decode -> re-encode -> (conditionally) import tags & cover. If no tags or cover,
    just re-encode with no import error.
    """
    try:
        relative_path = os.path.relpath(os.path.dirname(input_file), start=input_dir)
        output_folder = os.path.join(output_dir, relative_path)
        ensure_dir(output_folder)

        file = os.path.basename(input_file)
        if file.lower().endswith(".flac"):
            temp_wav = os.path.join(output_folder, file[:-5] + ".wav")
            output_flac = os.path.join(output_folder, file)
            metadata_file = os.path.join(output_folder, file[:-5] + ".txt")
            cover_image_file = os.path.join(output_folder, file[:-5] + "_cover.jpg")

            # 1) Extract tags/artwork (no hard failure if none exist)
            meta_info = extract_metadata(input_file, metadata_file, cover_image_file, metaflac_path)

            # 2) Decode to WAV
            logging.info(f"Decoding: {input_file} to {temp_wav}")
            subprocess.run([flac_old_path, "-d", "--force", "--output-name", temp_wav, input_file], check=True)

            # 3) Re-encode to FLAC
            logging.info(f"Encoding: {temp_wav} to {output_flac}")
            subprocess.run([flac_new_path, "-f", "-o", output_flac, temp_wav], check=True)

            # 4) Import tags/artwork if they were extracted
            import_metadata(output_flac, metadata_file, cover_image_file, metaflac_path, meta_info)

            # 5) Remove temp files
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
            if os.path.exists(cover_image_file):
                os.remove(cover_image_file)
        else:
            # Copy non-FLAC files directly
            output_file = os.path.join(output_folder, file)
            logging.info(f"Copying file: {input_file} to {output_file}")
            shutil.copy2(input_file, output_file)

    except subprocess.CalledProcessError as e:
        logging.error(f"Error processing file {input_file}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error processing {input_file}: {e}")

def process_flac_files(input_dir, output_dir, flac_old_path, flac_new_path, metaflac_path):
    """
    Walk through the input_dir, find all files (FLAC or otherwise),
    and process them in parallel with multiprocessing.
    """
    log_file = Path(input_dir).resolve() / "flac_processing.log"
    logging.basicConfig(filename=log_file, filemode="a")

    # Gather all files to process
    files_to_process = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            input_file = os.path.join(root, file)
            files_to_process.append(input_file)
            # Also ensure the output folder exists
            relative_path = os.path.relpath(os.path.dirname(input_file), start=input_dir)
            output_folder = os.path.join(output_dir, relative_path)
            ensure_dir(output_folder)

    # Sort the list for consistent processing order (optional)
    files_to_process.sort()

    # Use all available CPUs
    num_cores = os.cpu_count()

    with multiprocessing.Pool(processes=num_cores) as pool:
        pool.starmap(
            process_single_flac,
            [(input_file, output_dir, flac_old_path, flac_new_path, metaflac_path, input_dir)
             for input_file in files_to_process]
        )

if __name__ == "__main__":
    try:
        # Load configuration
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        config = load_config(config_path)

        input_dir = r"X:\_Temp\A"
        output_dir = r"X:\_Temp\B"
        flac_old_path = config['supportfiles']['oldflac']
        flac_new_path = config['supportfiles']['flac']
        metaflac_path = config['supportfiles']['metaflac']

        logging.info(f"Processing FLAC files from {input_dir} to {output_dir}")
        process_flac_files(input_dir, output_dir, flac_old_path, flac_new_path, metaflac_path)
        logging.info("Processing complete.")
    except Exception as e:
        logging.error(f"Failed to read or process configuration file: {e}")
