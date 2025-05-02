import pytest
import sys
import os
import docx2txt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from extraction.rules.predict_job_number import predict_job_number

@pytest.mark.parametrize("file_path, field_name, expected_job_number", [
    ("./data/certificate1.docx", "job_number", "LAD-42356"),
    ("./data/report1.docx", "job_number", "LAD-42117"),
])
def test_job_number(file_path, field_name, expected_job_number):
    try:
        document_text = docx2txt.process(file_path)
    except Exception as e:
        pytest.fail(f"Failed to process document: {file_path}. Error: {str(e)}")
    
    client_predictions = predict_job_number(document_text, field_name)


    predictions_list = client_predictions[field_name]

    assert predictions_list[0]["text"] == expected_job_number, (
        f"Expected client name '{expected_job_number}' but got '{predictions_list[0]['text']}'"
    )
