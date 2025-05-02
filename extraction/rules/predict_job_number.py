import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from extraction.rules.load_extraction_rules import RULES
import docx2txt

from extraction.rules.rule_engine import (
    parse_text,
)
from utils import get_unique_candidates, get_results

def predict_job_number(document_text: str, field_name: str, document_type: str = None) -> dict:
    content = parse_text(document_text, RULES[field_name])
    results = get_results(content, field_name)
    results = get_unique_candidates(results, confidence_boost=5)
    return {field_name: results}


# filepath='./ex.docx'
# text = docx2txt.process(filepath)


# print(predict_job_number(text, 'job_number'))