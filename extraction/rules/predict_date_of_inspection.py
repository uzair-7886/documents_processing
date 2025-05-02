import sys
import os
from datetime import datetime
import regex as re
from typing import Dict, List

from extraction.rules.load_extraction_rules import RULES
from extraction.rules.rule_engine import parse_text
from utils import get_unique_candidates, get_results

def predict_date_of_inspection(document_text: str, field_name: str, document_type: str = None) -> Dict:
    """
    Parse date of inspection from document text, with special handling for certificates.
    
    Args:
        document_text (str): The text content of the document
        field_name (str): Name of the field to extract
        document_type (str, optional): Type of document (e.g. "certificate")
        
    Returns:
        Dict: Dictionary containing the extracted date information, or an empty string in case of error.
    """
    try:
        if document_type == "certificate":
            # Look for date patterns in the text
            # First try to find dates with explicit "START ON" or similar phrases
            start_pattern = r"START\s+ON\s+THIS\s+([A-Z]+)\s+(\d{1,2}),?\s+(\d{4})"
            match = re.search(start_pattern, document_text, re.IGNORECASE)
            
            if match:
                try:
                    month, day, year = match.groups()
                    date_obj = datetime.strptime(f"{month} {day} {year}", "%B %d %Y")
                    formatted_date = date_obj.strftime("%d.%m.%Y")
                    
                    return {
                        'date_of_inspection': [{
                            'text': formatted_date,
                            'confidence': 90,
                            'location': match.start(),
                            'version': '01'
                        }]
                    }
                except ValueError:
                    return ""
                    
            # Fallback to general date pattern matching
            date_pattern = r"(?:ON|DATED?|ISSUED)\s+(?:THIS\s+)?(\d{1,2}(?:ST|ND|RD|TH)?\s+)?([A-Z]+)\s+(\d{1,2}|\d{4})(?:\s*,\s*(\d{4}))?"
            matches = re.finditer(date_pattern, document_text, re.IGNORECASE)
            
            results = []
            for match in matches:
                try:
                    groups = match.groups()
                    if len(groups) == 4 and groups[3]:  # Has explicit year
                        day = groups[0].strip().rstrip('STNDRDTHstndrdth') if groups[0] else '1'
                        month, year = groups[1], groups[3]
                    else:
                        day = groups[0].strip().rstrip('STNDRDTHstndrdth') if groups[0] else '1'
                        month = groups[1]
                        year = groups[2] if len(groups[2]) == 4 else groups[3]
                    
                    date_str = f"{month} {day} {year}"
                    date_obj = datetime.strptime(date_str, "%B %d %Y")
                    formatted_date = date_obj.strftime("%d.%m.%Y")
                    
                    results.append({
                        'text': formatted_date,
                        'confidence': 85,
                        'location': match.start(),
                        'version': '01'
                    })
                except (ValueError, TypeError):
                    continue
                    
            if results:
                return {'date_of_inspection': results}
        
        content = parse_text(document_text, RULES[field_name])
        results = get_results(content, field_name)
        results = get_unique_candidates(results, confidence_boost=5)
        return {field_name: results}
    except Exception:
        return ""
