import pytest
import sys
import os
import docx2txt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from extraction.rules.predict_client_name import predict_client_name

@pytest.mark.parametrize("file_path, field_name, expected_client_name", [
    ("./data/certificate1.docx", "client_name", "GOVIND KUMAR"),
    ("./data/report1.docx", "client_name", "AES MIDDLE EAST"),
])
def test_client_name(file_path, field_name, expected_client_name):
    try:
        document_text = docx2txt.process(file_path)
    except Exception as e:
        pytest.fail(f"Failed to process document: {file_path}. Error: {str(e)}")
    
    client_predictions = predict_client_name(document_text, field_name)


    # Extract predictions for the client name
    predictions_list = client_predictions[field_name]

    # Validate the first prediction
    assert predictions_list[0]["text"] == expected_client_name, (
        f"Expected client name '{expected_client_name}' but got '{predictions_list[0]['text']}'"
    )
