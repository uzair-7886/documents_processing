import pytest
import sys
import os
import docx2txt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from extraction.rules.predict_emirates_id import predict_emirates_id

@pytest.mark.parametrize("file_path, field_name, expected_emirates_id", [
    ("./data/em.docx", "emirates_id", "784-1988-0757363-3"),
])
def test_emirates_id(file_path, field_name, expected_emirates_id):
    try:
        document_text = docx2txt.process(file_path)
    except Exception as e:
        pytest.fail(f"Failed to process document: {file_path}. Error: {str(e)}")
    
    client_predictions = predict_emirates_id(document_text, field_name)

    print(f"Predictions for {file_path}: {client_predictions}")

    assert field_name in client_predictions, f"'{field_name}' not found in predictions: {client_predictions}"
    predictions_list = client_predictions[field_name]
    assert len(predictions_list) > 0, f"No predictions found for {field_name} in {file_path}"
    assert predictions_list[0]["text"] == expected_emirates_id, (
        f"Expected company ID '{expected_emirates_id}' but got '{predictions_list[0]['text']}'"
    )
