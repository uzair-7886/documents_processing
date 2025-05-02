from mega import Mega
import os
from collections import defaultdict
import pandas as pd
from datetime import datetime
import docx2txt
import json
from classification.classify_document import classify_document
import logging

class MegaSync:
    def __init__(self, email, password, base_folders=None):
        if base_folders is None:
            self.base_folders = ["MEGA", "JOB_LOG"]
        else:
            self.base_folders = base_folders
            
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('mega_sync.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.mega_api = self.connect_to_mega(email, password)
        self.local_base_paths = {folder: os.path.join(os.getcwd(), folder) for folder in self.base_folders}
        self.report_file = "sync_report.xlsx"
        self.json_log_file = "data.json"
        
        # Create local folders if they don't exist
        for path in self.local_base_paths.values():
            if not os.path.exists(path):
                os.makedirs(path)
                self.logger.info(f"Created local folder: {path}")

    def connect_to_mega(self, email, password):
        mega = Mega()
        try:
            self.logger.info("Connecting to MEGA...")
            api = mega.login(email, password)
            self.logger.info("Successfully connected to MEGA")
            return api
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return None

    def should_process_file(self, file_path):
        """Check if the file should be processed based on extension and path."""
        # Check file extension
        allowed_extensions = ('.docx', '.xlsx')
        if not file_path.lower().endswith(allowed_extensions):
            self.logger.debug(f"Skipping {file_path}: not an allowed file type")
            return False
            
        # Check if file is in ignored folder
        if "ENAS DATA 2024" in file_path:
            self.logger.debug(f"Skipping {file_path}: in ignored folder")
            return False
            
        return True

    def get_folder_structure(self):
        """Build the folder structure from Mega."""
        self.logger.info("Getting MEGA folder structure...")
        files = self.mega_api.get_files()
        folder_structure = defaultdict(list)
        for item in files.values():
            parent = item.get('p', None)
            folder_structure[parent].append(item)
        return folder_structure

    def find_root_folder(self, folder_name):
        """Find the root node ID of a specific folder on Mega."""
        self.logger.info(f"Looking for root folder: {folder_name}")
        files = self.mega_api.get_files()
        for node, info in files.items():
            if info['t'] == 1 and info['a'].get('n') == folder_name:
                self.logger.info(f"Found root folder: {folder_name}")
                return node
        self.logger.info(f"Root folder not found: {folder_name}")
        return None

    def get_files_with_paths(self, folder_id, folder_structure, current_path=""):
        """Recursively get all files in a folder on Mega with relative paths."""
        files = {}
        for item in folder_structure.get(folder_id, []):
            if item['t'] == 0:  # File
                file_path = os.path.join(current_path, item['a']['n'])
                if self.should_process_file(file_path):
                    self.logger.debug(f"Found file: {file_path}")
                    files[file_path] = item
            elif item['t'] == 1:  # Folder
                subfolder_path = os.path.join(current_path, item['a']['n'])
                files.update(self.get_files_with_paths(item['h'], folder_structure, subfolder_path))
        return files

    def get_local_files(self, local_folder):
        """Get all files in a local folder with relative paths."""
        self.logger.info(f"Scanning local folder: {local_folder}")
        local_files = {}
        try:
            for root, _, files in os.walk(local_folder):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, local_folder)
                    if self.should_process_file(rel_path):
                        self.logger.debug(f"Found local file: {rel_path}")
                        local_files[rel_path] = full_path
            return local_files
        except Exception as e:
            self.logger.error(f"Error reading local files in {local_folder}: {e}")
            return {}

    def append_to_report(self, file_name, action, timestamp):
        """Append details to the Excel report."""
        try:
            df = pd.DataFrame(
                [{"File Name": file_name, "Action": action, "Timestamp": timestamp}]
            )
            if os.path.exists(self.report_file):
                existing = pd.read_excel(self.report_file)
                df = pd.concat([existing, df], ignore_index=True)
            df.to_excel(self.report_file, index=False)
            self.logger.debug(f"Updated report for {file_name}")
        except Exception as e:
            self.logger.error(f"Error updating report for {file_name}: {e}")

    def extract_document_text(self, file_path):
        """Extract text from document files."""
        try:
            _, ext = os.path.splitext(file_path)
            if ext.lower() == '.docx':
                return docx2txt.process(file_path)
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting text from {file_path}: {e}")
            return ""

    def update_json_log(self, file_info):
        """Update JSON log file with new file information."""
        try:
            if os.path.exists(self.json_log_file):
                with open(self.json_log_file, 'r') as f:
                    data = json.load(f)
            else:
                data = []
            
            data.append(file_info)
            
            with open(self.json_log_file, 'w') as f:
                json.dump(data, f, indent=4)
            
            self.logger.debug(f"Updated JSON log for {file_info['file_name']}")
        except Exception as e:
            self.logger.error(f"Error updating JSON log: {e}")

    def find_or_create_mega_folders(self, folder_path, folder_structure, root_id):
        """Create missing folders on Mega and return the folder ID."""
        folders = folder_path.split(os.sep)
        parent_id = root_id
        
        for folder in folders:
            folder_id = None
            for item in folder_structure.get(parent_id, []):
                if item['t'] == 1 and item['a']['n'] == folder:
                    folder_id = item['h']
                    break
            
            if not folder_id:
                self.logger.info(f"Creating folder on Mega: {folder}")
                folder_id = self.mega_api.create_folder(folder, parent_id)['h']
                folder_structure[parent_id].append({'h': folder_id, 'a': {'n': folder}, 't': 1})
            parent_id = folder_id
        
        return parent_id

    def process_synced_file(self, file_name, file_path, action):
        """Process a synced file: generate link, extract text, update logs."""
        try:
            # Generate public link
            public_link = self.mega_api.export(file_name)
            
            # Extract document text if possible
            document_text = self.extract_document_text(file_path)
            document_type = classify_document(document_text)
            
            # Update logs
            file_info = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file_name": file_name,
                "mega_link": public_link,
                "document_text": document_text,
                "document_type": document_type,
                "action": action
            }
            
            self.update_json_log(file_info)
            self.append_to_report(file_name, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
        except Exception as e:
            self.logger.error(f"Error processing {file_name}: {e}")

    def sync_files(self):
        """Sync files between Mega and local folders."""
        synced_files = []
        
        for base_folder in self.base_folders:
            self.logger.info(f"\nStarting sync for folder: {base_folder}")
            
            # Find or create root folder on MEGA
            root_folder_id = self.find_root_folder(base_folder)
            if not root_folder_id:
                self.logger.info(f"Creating folder '{base_folder}' on MEGA...")
                root_folder_id = self.mega_api.create_folder(base_folder)['h']
            
            folder_structure = self.get_folder_structure()
            mega_files = self.get_files_with_paths(root_folder_id, folder_structure)
            local_files = self.get_local_files(self.local_base_paths[base_folder])
            
            # Compare files
            mega_not_local = set(mega_files.keys()) - set(local_files.keys())
            local_not_mega = set(local_files.keys()) - set(mega_files.keys())
            
            # Download files from MEGA
            for file in mega_not_local:
                file_name = os.path.basename(file)
                self.logger.info(f"Downloading: {file_name}")
                local_path = os.path.join(self.local_base_paths[base_folder], file)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                try:
                    file_obj = self.mega_api.find(file_name)
                    public_link = self.mega_api.export(file_name)
                    downloaded_path = self.mega_api.download(file_obj, os.path.dirname(local_path))
                    self.process_synced_file(file_name, downloaded_path, "Download")
                    synced_files.append({"file_name": file_name, "mega_link": public_link})
                except Exception as e:
                    self.logger.error(f"Error downloading {file_name}: {e}")
            
            # Upload files to MEGA
            for file in local_not_mega:
                file_name = os.path.basename(file)
                self.logger.info(f"Uploading: {file_name}")
                mega_folder_path = os.path.dirname(file)
                mega_folder_id = root_folder_id
                if mega_folder_path != ".":
                    mega_folder_id = self.find_or_create_mega_folders(mega_folder_path, folder_structure, root_folder_id)
                
                try:
                    uploaded_file = self.mega_api.upload(local_files[file], mega_folder_id)
                    self.process_synced_file(file_name, local_files[file], "Upload")
                    synced_files.append({"file_name": file_name, "action": "Uploaded"})
                except Exception as e:
                    self.logger.error(f"Error uploading {file_name}: {e}")
        
        return synced_files

    def download_file_from_link(self, mega_link, local_path=None):
        """Download a file from a Mega file sharing link."""
        try:
            if local_path is None:
                local_path = self.local_base_paths[self.base_folders[0]]
            
            os.makedirs(local_path, exist_ok=True)
            
            self.logger.info(f"Downloading file from link to: {local_path}")
            downloaded_file = self.mega_api.download_url(mega_link, local_path)
            
            if downloaded_file:
                file_name = os.path.basename(downloaded_file)
                self.append_to_report(file_name, "Link Download", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                self.logger.info(f"File downloaded successfully: {downloaded_file}")
                return downloaded_file
            else:
                self.logger.error("Failed to download file from the link.")
                return None
        
        except Exception as e:
            self.logger.error(f"Error downloading file from link: {e}")
            return None
        
    def get_all_links(self):
        """Retrieve public links for all files in Mega Drive."""
        links = []
        try:
            self.logger.info("Retrieving public links for all files...")
            files = self.mega_api.get_files()
            
            for file_id, file_data in files.items():
                if file_data['t'] == 0:  # Files only
                    file_name = file_data['a']['n']
                    self.logger.debug(f"Processing file: {file_name}")
                    
                    if not self.should_process_file(file_name):
                        continue
                    
                    try:
                        public_link = self.mega_api.export(file_name)
                        if public_link:
                            links.append({
                                "file_name": file_name,
                                "public_link": public_link
                            })
                            self.logger.debug(f"Generated link for {file_name}")
                        else:
                            raise ValueError("Exported link is None")
                    except Exception as e:
                        self.logger.error(f"Could not generate link for {file_name}: {e}")
                        links.append({
                            "file_name": file_name,
                            "public_link": None
                        })

            return links
        except Exception as e:
            self.logger.error(f"Error retrieving or generating links: {e}")
            return []