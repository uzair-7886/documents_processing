import os
import sys
import docx2txt

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from classification.load_classification_rules import RULES  
from extraction.rules.rule_engine import parse_text

from utils import get_unique_candidates, get_results

def classify_document(document_text: str, possible_document_types: list = None) -> str:
    # Use all available document types if none are specified
    if not possible_document_types:
        possible_document_types = list(RULES.keys())
    
    highest_confidence = 0
    final_document_type = ""

    # Iterate over all possible document types
    for document_type in possible_document_types:
        total_confidence = 0

        # Parse the text using the rules for this document type
        matches = parse_text(document_text, RULES[document_type])
        results = get_results(matches, document_type)
        results = get_unique_candidates(results, confidence_boost=5)
        # print(results)
        # print(type(matches))
        # print(matches)
        if results:
            # Sum the confidence weights of all matches
            total_confidence = sum(match.get('confidence', 0) for match in results)

        # print(total_confidence)
        # Update if this document type has a higher confidence score
        if total_confidence > highest_confidence:
            highest_confidence = total_confidence
            final_document_type = document_type

    return final_document_type


# filepaths=['./test1.docx', './test2.docx', './test3.docx', './test4.docx', './test5.docx']

# for doc in filepaths:
#     text=docx2txt.process(doc)
#     print(classify_document(text))
