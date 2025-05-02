from flask import Flask, request, jsonify
# from celery_config import make_celery
from field_predictor_mapping import field_to_predictor
from classification.classify_document import classify_document
from mega_sync import MegaSync
import docx2txt
#TODO: test the flask app
#TODO: Create a create_project and delete_project endpoint
#TODO: call all the predictors using celery

# Create Flask app
app = Flask(__name__)

# Celery configuration with Redis as the broker
# app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
# app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# # Initialize Celery
# celery = make_celery(app)

#following route needs to be updated as required
@app.route('/extract', methods=['POST'])
def extract_fields():
    data = request.get_json()
    # return jsonify(data)


    # Validate input data
    if not data or 'document_text' not in data or 'fields' not in data:
        #Check if Mega Link is given for a file, process this file
        email = "uzairk7886@gmail.com"
        password = ""
        syncer=MegaSync(email,password)
        if 'mega_link' in data:
            file=syncer.download_file_from_link(data['mega_link'])
            if file:
                document_text = docx2txt.process(file)
        else:
            return jsonify({"error": "Invalid request. 'document_text or mega_link' is required."}), 400
        # return jsonify({"error": "Invalid request. 'document_text' and 'fields' are required."}), 400
    else:
        document_text = data['document_text']

    if not data or 'fields' not in data:
        return jsonify({"error": "Invalid request. 'fields' are required."}), 400
    else:
        fields = data['fields']
    # fields = data['fields']
    document_type = data.get("document_type", "")
    possible_document_types = data.get("possible_document_types", [])
    # return jsonify({"fields": fields, "document_type": document_type, "possible_document_types": possible_document_types})

    # Step 1: Classify the document
    if not document_type:
        document_type = classify_document(document_text, possible_document_types)

    # Dictionary to hold results
    results = {}
    # return jsonify(results)

    for field in fields:
        predictor = field_to_predictor.get(field, None)
        if predictor:
            results[field] = predictor(document_text,field, document_type).get(field)
        else:
            return jsonify({"error": f"No predictor available for field '{field}'"}), 400
    # predictor=field_to_predictor.get("client_name", None)
    # results.append(predictor( document_text,"client_name", document_type))


    return jsonify(results)


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



