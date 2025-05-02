import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from classification.classify_document import classify_document
import docx2txt

@pytest.mark.parametrize("file_path, expected_label", [
    ("./data/certificate1.docx", "certificate"),
    ("./data/certificate2.docx", "certificate"),
    ("./data/report1.docx", "examination_report"),
    ("./data/report2.docx", "examination_report"),
])


def test_classify_document(file_path, expected_label):
    document_text = docx2txt.process(file_path)
    assert classify_document(document_text) == expected_label





