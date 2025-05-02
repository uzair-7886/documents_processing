import os
import json
import logging
import docx2txt
from datetime import datetime
from classification.classify_document import classify_document

# Replace with actual classification import or function definition

class ProcessLocal:
    """
    This class processes files from local folders only, extracts relevant info,
    classifies, and saves the data to processed_local.json.
    """
    def __init__(self, folder_paths=None):
        """
        :param folder_paths: list of folder paths to scan for local files
        """
        if folder_paths is None:
            folder_paths = []
        self.folder_paths = folder_paths
        
        # Logging setup can be separate or shared
        self.logger = logging.getLogger(__name__)
        self.processed_json_file = "processed_local.json"
        
        # Create local folders if they don't exist
        for folder in self.folder_paths:
            if not os.path.exists(folder):
                os.makedirs(folder)
                self.logger.info(f"Created local folder: {folder}")

    def should_process_file(self, file_path):
        """
        Check if the file should be processed based on extension and path.
        """
        allowed_extensions = ('.docx', '.xlsx')
        if not file_path.lower().endswith(allowed_extensions):
            self.logger.debug(f"Skipping {file_path}: not an allowed file type")
            return False

        # Example ignoring subfolder "ENAS DATA 2024"
        if "ENAS DATA 2024" in file_path:
            self.logger.debug(f"Skipping {file_path}: in ignored folder")
            return False

        return True

    def extract_document_text(self, file_path):
        """
        Extract text from a DOCX file.
        Return empty string for non-DOCX (like .xlsx).
        """
        try:
            _, ext = os.path.splitext(file_path)
            if ext.lower() == '.docx':
                return docx2txt.process(file_path)
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting text from {file_path}: {e}")
            return ""

    def update_processed_json(self, file_info):
        """
        Write out the minimal details for local processing into processed_local.json.
        """
        try:
            if os.path.exists(self.processed_json_file):
                with open(self.processed_json_file, 'r') as f:
                    data = json.load(f)
            else:
                data = []
            
            data.append(file_info)
            
            with open(self.processed_json_file, 'w') as f:
                json.dump(data, f, indent=4)
            
            self.logger.debug(f"Updated processed_local.json for {file_info['file_name']}")
        except Exception as e:
            self.logger.error(f"Error updating processed_local.json: {e}")

    def process_local_files(self):
        """
        Scan the specified local folders, extract text and classification,
        then save minimal details to processed_local.json.
        """
        processed_list = []
        
        for folder in self.folder_paths:
            self.logger.info(f"Processing local folder: {folder}")
            for root, _, files in os.walk(folder):
                for file in files:
                    full_path = os.path.join(root, file)
                    if not self.should_process_file(full_path):
                        continue
                    
                    # Extract text
                    document_text = self.extract_document_text(full_path)
                    document_type = classify_document(document_text)
                    
                    # Prepare minimal info
                    file_info = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "file_name": full_path,
                        "document_text": document_text,
                        "document_type": document_type
                    }
                    
                    # Update JSON
                    self.update_processed_json(file_info)
                    processed_list.append(file_info)
        
        return processed_list

