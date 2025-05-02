from extraction.rules.load_extraction_rules import RULES

from extraction.rules.rule_engine import (
    parse_text,
)
from utils import get_unique_candidates, get_results

def predict_course_name(document_text: str, field_name: str, document_type: str = None) -> dict:
    content = parse_text(document_text, RULES[field_name])
    results = get_results(content, field_name)
    results = get_unique_candidates(results, confidence_boost=5)
    return {field_name: results}