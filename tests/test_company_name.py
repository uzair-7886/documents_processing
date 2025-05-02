import pytest
import sys
import os
import docx2txt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from extraction.rules.predict_company_name import predict_company_name

@pytest.mark.parametrize("file_path, field_name, expected_company_name", [
    ("./data/certificate1.docx", "company_name", "QUALITY INTERNATIONAL C.I.S. LLC."),
])
def test_company_name(file_path, field_name, expected_company_name):
    try:
        document_text = docx2txt.process(file_path)
    except Exception as e:
        pytest.fail(f"Failed to process document: {file_path}. Error: {str(e)}")
    
    client_predictions = predict_company_name(document_text, field_name)

    print(f"Predictions for {file_path}: {client_predictions}")

    assert field_name in client_predictions, f"'{field_name}' not found in predictions: {client_predictions}"
    predictions_list = client_predictions[field_name]
    assert len(predictions_list) > 0, f"No predictions found for {field_name} in {file_path}"
    assert predictions_list[0]["text"] == expected_company_name, (
        f"Expected company ID '{expected_company_name}' but got '{predictions_list[0]['text']}'"
    )
