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
    """
    For each candidate:
      1) Normalize newlines → dots
      2) If we have explicit "day", "month", "year" keys, turn them into ISO.
      3) Otherwise, if "text" already looks like DD.MM.YYYY, convert that to ISO.
    """
    for candidate in result:
        # step 1: replace newlines with dots (existing behavior)
        candidate["text"] = re.sub(r"\n+", ".", candidate["text"], flags=re.M)

        # step 2: explicit day/month/year fields
        if {"day", "month", "year"}.issubset(candidate):
            candidate["text"] = to_iso_date(
                candidate["day"],
                candidate["month"],
                candidate["year"]
            )
            continue

        # step 3: catch any "DD.MM.YYYY" or "D.M.YYYY" in candidate["text"]
        m = re.match(r"^\s*(\d{1,2})[.\-](\d{1,2})[.\-](\d{4})\s*$", candidate["text"])
        if m:
            d, mo, y = m.groups()
            candidate["text"] = to_iso_date(d, mo, y)

    return result

def to_iso_date(day: Union[str, int], month: Union[str, int], year: Union[str, int]) -> str:
    """
    Convert separate day, month, year into an ISO-formatted date (YYYY-MM-DD).
    """
    day = int(day)
    month = int(month)
    year = int(year)
    return f"{year:04d}-{month:02d}-{day:02d}"

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
    Calculate the next inspection date based on start date and validity duration.
    Always return ISO format (YYYY-MM-DD) instead of DD.MM.YYYY.
    """
    # Parse start date (e.g. "September 30, 2024")
    try:
        start_date = datetime.strptime(start_date_str, '%B %d, %Y')
    except ValueError:
        raise ValueError(f"Invalid start date format: {start_date_str}")

    # Parse duration (unchanged)
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

    # Return ISO instead of "DD.MM.YYYY"
    return end_date.strftime('%Y-%m-%d')

def predict_next_date_of_inspection(document_text: str, field_name: str, document_type: str = None) -> dict:
    if document_type == "certificate":
        start = predict_course_start_date(document_text, "course_start_date")
        dur   = predict_course_validity_duration(document_text, "course_validity_duration")
        try:
            s_text = (start.get('course_start_date') or [])[0]['text']
            d_text = (dur  .get('course_validity_duration') or [])[0]['text']
            nd     = calculate_next_date(s_text, d_text)
            return { field_name: [{ 'text': nd, 'confidence': 90, 'location': 0, 'version': '01' }] }
        except (IndexError, ValueError):
            # nothing to calculate, just return “no data”
            return { field_name: [] }

    # non-certificate path unchanged
    content = parse_text(document_text, RULES[field_name])
    results = get_results(content, field_name)
    results = get_unique_candidates(results, confidence_boost=5)
    results = format_date(results)
    return {field_name: results}
# filepath='./test.docx'
# text = docx2txt.process(filepath)
# print(text)


# print(predict_next_date_of_inspection(text, 'date_of_inspection'))