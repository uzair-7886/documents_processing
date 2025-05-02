import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


from extraction.rules.load_extraction_rules import RULES
from extraction.rules.rule_engine import parse_text

def classify_document(document_text: str, possible_document_types: list = None) -> str:
    """
    Classifies the document based on the predefined rules and text content.
    
    Args:
        document_text (str): The text content of the document.
        possible_document_types (list, optional): The possible document types to classify into.
        
    Returns:
        str: The classified document type.
    """
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
        if matches:
            # Sum the confidence weights of all matches
            total_confidence = sum(match.get('weight', 0) for match in matches)

        # Update if this document type has a higher confidence score
        if total_confidence > highest_confidence:
            highest_confidence = total_confidence
            final_document_type = document_type

    return final_document_type


# Example usage
