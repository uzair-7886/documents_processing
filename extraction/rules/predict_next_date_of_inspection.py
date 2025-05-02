import sys
import os
from datetime import datetime, timedelta
import regex as re
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Union, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from extraction.rules.load_extraction_rules import RULES
from extraction.rules.rule_engine import parse_text
from utils import get_unique_candidates, get_results
from extraction.rules.predict_course_start_date import predict_course_start_date
from extraction.rules.predict_course_validity_duration import predict_course_validity_duration

import docx2txt

def replace_new_line_with_dot(text: str) -> str:
    return re.sub(r"\n+", ".", text, flags=re.M)

def format_date(result: list) -> list:
    for candidate in result:
        candidate["text"] = replace_new_line_with_dot(candidate["text"])
    return result

def parse_validity_duration(duration_text: str) -> Tuple[int, str]:
    """
    Parse validity duration text to extract number and unit
    Returns tuple of (number, unit)
    """
    # Convert text numbers to digits
    number_mapping = {
        'ONE': '1', 'TWO': '2', 'THREE': '3', 'FOUR': '4', 'FIVE': '5',
        'SIX': '6', 'SEVEN': '7', 'EIGHT': '8', 'NINE': '9', 'TEN': '10',
        'ELEVEN': '11', 'TWELVE': '12',
    }
    
    # Clean and standardize the input
    duration_text = duration_text.upper().strip()
    
    # Replace text numbers with digits
    for text_num, digit in number_mapping.items():
        duration_text = duration_text.replace(text_num, digit)
    
    # Extract number and unit using regex
    # The code will handle various duration formats like:
        # "ONE YEAR"
        # "1 YEAR"
        # "TWO MONTHS"
        # "2 MONTHS"
        # "SIX (6) MONTHS"
    pattern = r'(\d+)\s*(?:\([^)]*\))?\s*(YEAR|MONTH|WEEK|DAY)S?'
    match = re.search(pattern, duration_text)
    
    if not match:
        raise ValueError(f"Could not parse duration: {duration_text}")
    
    number = int(match.group(1))
    unit = match.group(2).lower()
    
    return number, unit

def calculate_next_date(start_date_str: str, validity_duration_str: str) -> str:
    """
    Calculate the next inspection date based on start date and validity duration
    Returns date in format DD.MM.YYYY
    """
    # Parse start date
    try:
        start_date = datetime.strptime(start_date_str, '%B %d, %Y')
    except ValueError:
        raise ValueError(f"Invalid start date format: {start_date_str}")
    
    # Parse duration
    number, unit = parse_validity_duration(validity_duration_str)
    
    # Calculate end date
    if unit == 'year':
        end_date = start_date + relativedelta(years=number)
    elif unit == 'month':
        end_date = start_date + relativedelta(months=number)
    elif unit == 'week':
        end_date = start_date + timedelta(weeks=number)
    elif unit == 'day':
        end_date = start_date + timedelta(days=number)
    else:
        raise ValueError(f"Invalid duration unit: {unit}")
    
    # Format result
    return end_date.strftime('%d.%m.%Y')

def predict_next_date_of_inspection(document_text: str, field_name: str, document_type: str = None) -> Union[Dict, Tuple]:
    """
    Predict next date of inspection based on document type and content
    Returns formatted date for certificates, or extraction results for other documents
    """
    if document_type == "certificate":
        start_date = predict_course_start_date(document_text, "course_start_date")
        validity_duration = predict_course_validity_duration(document_text, "course_validity_duration")
        
        # Extract the text values from the results
        start_date_text = start_date.get('course_start_date', [])[0].get('text', '')
        validity_duration_text = validity_duration.get('course_validity_duration', [])[0].get('text', '')
        
        try:
            next_date = calculate_next_date(start_date_text, validity_duration_text)
            return {
                'next_date_of_inspection': [{
                    'text': next_date,
                    'confidence': 90,
                    'location': 0,
                    'version': '01'
                }]
            }
        except (ValueError, IndexError) as e:
            # Return original data if date calculation fails
            return (start_date, validity_duration)
            
    else:
        content = parse_text(document_text, RULES[field_name])
        results = get_results(content, field_name)
        results = get_unique_candidates(results, confidence_boost=5)
        results = format_date(results)
        return {field_name: results}


# filepath='./test.docx'
# text = docx2txt.process(filepath)
# print(text)


# print(predict_next_date_of_inspection(text, 'date_of_inspection'))