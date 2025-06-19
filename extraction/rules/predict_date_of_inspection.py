import sys
import os
from datetime import datetime
import regex as re
from typing import Dict, List

from extraction.rules.load_extraction_rules import RULES
from extraction.rules.rule_engine import parse_text
from utils import get_unique_candidates, get_results
import re
from datetime import datetime
from typing import Dict

def to_iso_date(day: str, month: str, year: str) -> str:
    """
    Convert separate day, month, year into ISO format YYYY-MM-DD.
    """
    d = int(day)
    m = int(month)
    y = int(year)
    return f"{y:04d}-{m:02d}-{d:02d}"

def ddmmyyyy_to_iso(text: str) -> str:
    """
    If text matches DD.MM.YYYY (or D.M.YYYY), convert to ISO YYYY-MM-DD.
    Otherwise, return text unchanged.
    """
    m = re.match(r"^\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s*$", text)
    if m:
        d, mo, y = m.groups()
        return to_iso_date(d, mo, y)
    return text

def predict_date_of_inspection(document_text: str, field_name: str, document_type: str = None) -> Dict:
    try:
        if document_type == "certificate":
            # look for "START ON THIS <Month> <Day>, <Year>"
            start_pattern = r"START\s+ON\s+THIS\s+([A-Z]+)\s+(\d{1,2}),?\s+(\d{4})"
            match = re.search(start_pattern, document_text, re.IGNORECASE)
            
            if match:
                month, day, year = match.groups()
                try:
                    date_obj = datetime.strptime(f"{month} {day} {year}", "%B %d %Y")
                except ValueError:
                    return ""
                iso_date = date_obj.strftime("%Y-%m-%d")
                
                return {
                    'date_of_inspection': [{
                        'text': iso_date,
                        'confidence': 90,
                        'location': match.start(),
                        'version': '01'
                    }]
                }
            
            # fallback: general date patterns
            date_pattern = r"(?:ON|DATED?|ISSUED)\s+(?:THIS\s+)?(\d{1,2}(?:ST|ND|RD|TH)?\s+)?([A-Z]+)\s+(\d{1,2}|\d{4})(?:\s*,\s*(\d{4}))?"
            matches = re.finditer(date_pattern, document_text, re.IGNORECASE)
            
            results = []
            for match in matches:
                try:
                    groups = match.groups()
                    if len(groups) == 4 and groups[3]:
                        day_raw = groups[0].strip().rstrip('STNDRDTHstndrdth') if groups[0] else '1'
                        month, year = groups[1], groups[3]
                    else:
                        day_raw = groups[0].strip().rstrip('STNDRDTHstndrdth') if groups[0] else '1'
                        month = groups[1]
                        year = groups[2] if len(groups[2]) == 4 else groups[3]
                    
                    date_obj = datetime.strptime(f"{month} {day_raw} {year}", "%B %d %Y")
                    iso_date = date_obj.strftime("%Y-%m-%d")
                    
                    results.append({
                        'text': iso_date,
                        'confidence': 85,
                        'location': match.start(),
                        'version': '01'
                    })
                except (ValueError, TypeError):
                    continue
            
            if results:
                return {'date_of_inspection': results}
        
        # non-certificate path
        content = parse_text(document_text, RULES[field_name])
        results = get_results(content, field_name)
        results = get_unique_candidates(results, confidence_boost=5)
        
        # Convert any "DD.MM.YYYY" in the extracted text to ISO
        for candidate in results:
            candidate['text'] = ddmmyyyy_to_iso(candidate['text'])
        
        return {field_name: results}
    
    except Exception:
        return ""
