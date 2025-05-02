from flask import Flask, request, jsonify
# from celery_config import make_celery
from field_predictor_mapping import field_to_predictor
from classification.classify_document import classify_document
from mega_sync import MegaSync
import docx2txt
from utils import download_mega_file
import os
import json
from datetime import datetime
from flask_cors import CORS
from process_local import ProcessLocal
#TODO: test the flask app
#TODO: Create a create_project and delete_project endpoint
#TODO: call all the predictors using celery

# Create Flask app
app = Flask(__name__)
CORS(app)

# File to store json data
json_data="data.json"

# Celery configuration with Redis as the broker
# app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
# app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# # Initialize Celery
# celery = make_celery(app)

#following route needs to be updated as required
@app.route('/extract', methods=['POST'])
def extract_fields():
    try:
        # Parse input data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Initialize document_text so it's always in scope
        document_text = None
        
        # Handle document_text directly in the request
        if 'document_text' in data:
            document_text = data['document_text']
        
        # Handle Mega link file download if provided (and if document_text not supplied)
        elif 'mega_link' in data:
            mega_link = data['mega_link']
            try:
                # If you have code to retrieve the file from MEGA or from your JSON, put it here
                if os.path.exists(json_data):
                    with open(json_data, 'r') as f:
                        json_entries = json.load(f)
                    
                    for entry in json_entries:
                        if entry.get('mega_link') == mega_link:
                            document_text = entry.get('document_text')
                            break
            except Exception as e:
                return jsonify({"error": f"Failed to process file: {str(e)}"}), 400
        
        # If, after both checks, we still have no document text, return an error
        if not document_text:
            return jsonify({"error": "No document text provided or unable to retrieve from mega_link"}), 400
        
        # Prepare fields and document type
        fields = data.get('fields', [])
        document_type = data.get("document_type", "")
        possible_document_types = data.get("possible_document_types", [])
        
        # Classify document if not specified
        if not document_type:
            document_type = classify_document(document_text, possible_document_types)
        
        # Initialize results dictionary
        results = {}
        
        # Process each requested field
        for field in fields:
            predictor = field_to_predictor.get(field)
            if predictor:
                # Get prediction result
                prediction = predictor(document_text, field, document_type)
                
                # Extract text, defaulting to first result's text if available
                field_result = prediction.get(field, [{}])[0]
                results[field] = field_result.get('text', 'NO DATA FOUND')
            else:
                # No predictor available
                results[field] = "NO PREDICTOR FOUND!!"
        
        return jsonify(results)
    
    except Exception as e:
        # Catch-all error handling
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/getlinks', methods=['GET'])
def get_all_links():
    try:
        email = "mega@qualitydxb.com"
        password = "^2lc%wT,Soo~"
        syncer = MegaSync(email, password)
            # Get all links from MEGA
        links = syncer.sync_files() 
        return jsonify(links)
    
    except Exception as e:
        # Catch-all error handling
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
    
@app.route('/processlocal', methods=['POST'])
def process_local_route():
    """
    New endpoint to process local folders only.
    Expects JSON body with a list of folder paths, e.g.:
    {
        "folder_paths": ["./local_folder1", "./local_folder2"]
    }
    """
    try:
        data = request.get_json()
        folder_paths = data.get('folder_paths', [])

        # Instantiate the local processor and run
        local_processor = ProcessLocal(folder_paths=folder_paths)
        processed_result = local_processor.process_local_files()

        return jsonify({
            "status": "success",
            "processed_files_count": len(processed_result),
        })
    except Exception as e:
        return jsonify({"error": f"Error processing local folders: {str(e)}"}), 500


# This is a rough structure of the flask endpoint which is using celery. Disabled for now
# @app.route('/extract', methods=['POST'])
# def extract_fields():
#     data = request.get_json()

#     # Validate input data
#     if not data or 'document_text' not in data or 'fields' not in data:
#         return jsonify({"error": "Invalid request. 'document_text' and 'fields' are required."}), 400

#     document_text = data['document_text']
#     fields = data['fields']
#     document_type = data.get("document_type", "")
#     possible_document_types = data.get("possible_document_types", [])

#     # Step 1: Classify the document
#     if not document_type:
#         document_type_task = classify_document.delay(document_text, possible_document_types)
#         document_type = document_type_task.get(timeout=5)  # Blocking until classification completes


#     # Dictionary to hold tasks and field mappings
#     tasks = {}

#     # Map fields to the corresponding Celery task
#     for field in fields:
#         predictor = field_to_predictor.get(field, None)
#         if predictor:
#             tasks[field] = predictor.delay(field, document_text)
#         else:
#             return jsonify({"error": f"No predictor available for field '{field}'"}), 400

#     # Gather results
#     results = {}
#     for field, task in tasks.items():
#         results[field] = task.get(timeout=10)  # Blocks until the task is complete (with a timeout)

#     return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)



