import pytest
import sys
import os
import docx2txt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from extraction.rules.predict_certificate_number import predict_certificate_number

@pytest.mark.parametrize("file_path, field_name, expected_certificate_number", [
    ("./data/certificate1.docx", "certificate_number", "T20241086737"),
    ("./data/report1.docx", "certificate_number", "L202409396310"),
])
def test_certificate_number(file_path, field_name, expected_certificate_number):
    try:
        document_text = docx2txt.process(file_path)
    except Exception as e:
        pytest.fail(f"Failed to process document: {file_path}. Error: {str(e)}")
    
    certificate_predictions = predict_certificate_number(document_text, field_name)

    print(f"Predictions for {file_path}: {certificate_predictions}")

    assert field_name in certificate_predictions, f"'{field_name}' not found in predictions: {certificate_predictions}"
    predictions_list = certificate_predictions[field_name]
    assert len(predictions_list) > 0, f"No predictions found for {field_name} in {file_path}"
    assert predictions_list[0]["text"] == expected_certificate_number, (
        f"Expected certificate number '{expected_certificate_number}' but got '{predictions_list[0]['text']}'"
    )
