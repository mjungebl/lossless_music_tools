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

# Function to extract metadata and cover image from a FLAC file
def extract_metadata(input_file, metadata_file, cover_image_file, metaflac_path):
    try:
        logging.info(f"Extracting metadata from: {input_file}")
        
        # Export text tags to metadata file
        subprocess.run([metaflac_path, "--export-tags-to", metadata_file, input_file], check=True)
        
        # Extract embedded cover image (if present) to a separate file
        subprocess.run([metaflac_path, "--export-picture-to", cover_image_file, input_file], check=True)
        
        if os.path.exists(cover_image_file):
            logging.info(f"Cover image extracted: {cover_image_file}")
        else:
            logging.info("No cover image found in the source file.")
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to extract metadata from {input_file}: {e}")
        raise

# Function to import metadata and cover image to a FLAC file
def import_metadata(output_file, metadata_file, cover_image_file, metaflac_path):
    try:
        logging.info(f"Importing metadata to: {output_file}")
        
        # Import text tags from metadata file
        subprocess.run([metaflac_path, "--import-tags-from", metadata_file, output_file], check=True)
        
        # Import cover image (if present) from a separate file
        if os.path.exists(cover_image_file):
            subprocess.run([metaflac_path, "--import-picture-from", cover_image_file, output_file], check=True)
            logging.info(f"Cover image imported from: {cover_image_file}")
        else:
            logging.info("No cover image to import.")
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to import metadata to {output_file}: {e}")
        raise

# Function to process a single FLAC file (decoding, encoding, and metadata handling)
def process_single_flac(input_file, output_dir, flac_old_path, flac_new_path, metaflac_path,input_dir):
    print(f'{input_file}=, {output_dir}=, {flac_old_path}=, {flac_new_path}=, {metaflac_path}=,{input_dir}=')
    try:
        relative_path = os.path.relpath(os.path.dirname(input_file), start=input_dir)
        output_folder = os.path.join(output_dir, relative_path)
        #ensure_dir(output_folder)

        file = os.path.basename(input_file)
        if file.lower().endswith(".flac"):
            temp_wav = os.path.join(output_folder, file[:-5] + ".wav")
            output_flac = os.path.join(output_folder, file)
            metadata_file = os.path.join(output_folder, file[:-5] + ".txt")
            cover_image_file = os.path.join(output_folder, file[:-5] + "_cover.jpg")

            # Extract metadata and cover image from source file
            extract_metadata(input_file, metadata_file, cover_image_file, metaflac_path)

            # Decode to WAV without tags
            logging.info(f"Decoding: {input_file} to {temp_wav}")
            subprocess.run([flac_old_path, "-d", "--force", "--output-name", temp_wav, input_file], check=True)

            # Re-encode to FLAC
            logging.info(f"Encoding: {temp_wav} to {output_flac}")
            subprocess.run([flac_new_path, "-f", "-o", output_flac, temp_wav], check=True)

            # Import metadata and cover image to the re-encoded FLAC file
            import_metadata(output_flac, metadata_file, cover_image_file, metaflac_path)

            # Remove temporary files
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
            if os.path.exists(cover_image_file):
                os.remove(cover_image_file)
        else:
            # Copy non-FLAC files
            output_file = os.path.join(output_folder, file)
            logging.info(f"Copying file: {input_file} to {output_file}")
            shutil.copy2(input_file, output_file)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error processing file {input_file}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error processing {input_file}: {e}")

# Process FLAC files in parallel using multiprocessing
def process_flac_files(input_dir, output_dir, flac_old_path, flac_new_path, metaflac_path):
    log_file = Path(input_dir).resolve() / "flac_processing.log"
    logging.basicConfig(filename=log_file, filemode="a")

    # List all FLAC files to process
    files_to_process = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            input_file = os.path.join(root, file)
            files_to_process.append(input_file)
            relative_path = os.path.relpath(os.path.dirname(input_file), start=input_dir)
            output_folder = os.path.join(output_dir, relative_path)
            ensure_dir(output_folder)            
    print(files_to_process.sort())
    # Get the number of available physical cores
    num_cores = os.cpu_count()

    # Use multiprocessing Pool to process FLAC files in parallel
    with multiprocessing.Pool(processes=num_cores) as pool:
        # Pass the arguments as a tuple and use starmap to unpack
        pool.starmap(process_single_flac, [(input_file, output_dir, flac_old_path, flac_new_path, metaflac_path,input_dir) for input_file in files_to_process])

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
