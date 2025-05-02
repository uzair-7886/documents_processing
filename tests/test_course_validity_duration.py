import pytest
import sys
import os
import docx2txt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from extraction.rules.predict_course_validity_duration import predict_course_validity_duration

@pytest.mark.parametrize("file_path, field_name, expected_course_validity_duration", [
    ("./data/certificate1.docx", "course_validity_duration", "ONE (1) YEAR"),
])
def test_course_validity_duration(file_path, field_name, expected_course_validity_duration):
    try:
        document_text = docx2txt.process(file_path)
    except Exception as e:
        pytest.fail(f"Failed to process document: {file_path}. Error: {str(e)}")
    
    client_predictions = predict_course_validity_duration(document_text, field_name)

    print(f"Predictions for {file_path}: {client_predictions}")

    assert field_name in client_predictions, f"'{field_name}' not found in predictions: {client_predictions}"
    predictions_list = client_predictions[field_name]
    assert len(predictions_list) > 0, f"No predictions found for {field_name} in {file_path}"
    assert predictions_list[0]["text"] == expected_course_validity_duration, (
        f"Expected company ID '{expected_course_validity_duration}' but got '{predictions_list[0]['text']}'"
    )
