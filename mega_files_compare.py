from mega import Mega
import os
from collections import defaultdict

class MegaSync:
    """
    Class to compare files between a local folder (qualitydxb here) and a folder on Mega.
    """
    def __init__(self, email, password, base_folder="qualitydxb"):
        self.mega_api = self.connect_to_mega(email, password)
        self.base_folder = base_folder
        self.local_base_path = os.path.join(os.getcwd(), base_folder)

    def connect_to_mega(self, email, password):
        mega = Mega()
        try:
            return mega.login(email, password)
        except Exception as e:
            print(f"Login failed: {e}")
            return None

    def get_folder_structure(self):
        """Build the folder structure from Mega."""
        files = self.mega_api.get_files()
        folder_structure = defaultdict(list)
        for item in files.values():
            parent = item.get('p', None)
            folder_structure[parent].append(item)
        return folder_structure

    def find_root_folder(self, folder_name):
        """Find the root node ID of a specific folder on Mega."""
        files = self.mega_api.get_files()
        for node, info in files.items():
            if info['t'] == 1 and info['a'].get('n') == folder_name:
                return node
        return None

    def get_files_with_paths(self, folder_id, folder_structure, current_path=""):
        """Recursively get all files in a folder on Mega with relative paths."""
        files = {}
        for item in folder_structure.get(folder_id, []):
            if item['t'] == 0:  # File
                file_path = os.path.join(current_path, item['a']['n'])
                files[file_path] = item['h']
            elif item['t'] == 1:  # Folder
                subfolder_path = os.path.join(current_path, item['a']['n'])
                files.update(self.get_files_with_paths(item['h'], folder_structure, subfolder_path))
        return files

    def get_local_files(self, local_folder):
        """Get all files in a local folder with relative paths."""
        local_files = {}
        try:
            for root, _, files in os.walk(local_folder):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), local_folder)
                    local_files[rel_path] = None
            return local_files
        except Exception as e:
            print(f"Error reading local files in {local_folder}: {e}")
            return {}

    def compare_files(self):
        """Compare Mega files with local files and report differences."""
        root_folder_id = self.find_root_folder(self.base_folder)
        if not root_folder_id:
            print(f"Folder '{self.base_folder}' not found on Mega.")
            return

        print(f"Found root folder '{self.base_folder}' on Mega.")
        
        # Get Mega folder structure
        folder_structure = self.get_folder_structure()
        mega_files = self.get_files_with_paths(root_folder_id, folder_structure)
        
        # Get local folder structure
        local_files = self.get_local_files(self.local_base_path)

        # Compare files
        mega_not_local = set(mega_files.keys()) - set(local_files.keys())
        local_not_mega = set(local_files.keys()) - set(mega_files.keys())

        print("\nComparison Results:")
        print(f"Files on Mega but not locally:\n{list(mega_not_local)}")
        print(f"Files locally but not on Mega:\n{list(local_not_mega)}")

def main():
    email = "uzairk7886@gmail.com"
    password = "Mega12345"
    syncer = MegaSync(email, password)
    if not syncer.mega_api:
        print("Failed to connect to Mega.")
        return
    print("Starting file comparison...")
    syncer.compare_files()

if __name__ == "__main__":
    main()
