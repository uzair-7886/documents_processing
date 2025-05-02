import pytest
import sys
import os
import docx2txt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from extraction.rules.predict_next_date_of_inspection import predict_next_date_of_inspection
from classification.classify_document import classify_document

@pytest.mark.parametrize("file_path, field_name, expected_next_date_of_inspection", [
    ("./data/certificate1.docx", "next_date_of_inspection", "30.09.2025"),
    ("./data/report1.docx", "next_date_of_inspection", "25.03.2025"),
])
def test_next_date_of_inspection(file_path, field_name, expected_next_date_of_inspection):
    try:
        document_text = docx2txt.process(file_path)
    except Exception as e:
        pytest.fail(f"Failed to process document: {file_path}. Error: {str(e)}")
    document_type=classify_document(document_text)
    client_predictions = predict_next_date_of_inspection(document_text, field_name, document_type)


    # Extract predictions for the client name
    predictions_list = client_predictions[field_name]

    # Validate the first prediction
    assert predictions_list[0]["text"] == expected_next_date_of_inspection, (
        f"Expected client name '{expected_next_date_of_inspection}' but got '{predictions_list[0]['text']}'"
    )
