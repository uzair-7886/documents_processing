import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

import regex as re

from utils import (
    cleanup_text,
    position_to_triplet,
    triplet_to_position,
)


logger = logging.getLogger(__name__)

# logic for horizontal beacons
def parse_text(
    text: str, parser: dict, fields: Optional[dict] = None, field_name: Optional[str] = None):
    if not fields:
        fields = {}
    text = cleanup_text(text)
    variables_matches = defaultdict(list)
    if "rules" in parser:
        for rule in parser["rules"]:
            rule["regex"] = rule["rule"]
            rule.setdefault("weight", 0)
            rule.setdefault("gen_id", None)

            # time profiling per regex
            start = time.time()
            found = add_to_dictionary(text, rule["regex"], gen_id=rule["gen_id"], weight=rule["weight"])
            # End regex timing
            time_elapsed = time.time() - start
            if time_elapsed > 0.5:
                logger.warning(
                    f"\nRegex for field {field_name}, regex_id [{rule['gen_id']}] took {time_elapsed} seconds to run!"
                )
                print(
                    f"\nRegex for field {field_name}, regex_id [{rule['gen_id']}] took {time_elapsed} seconds to run!"
                )
                print(f"regex: {rule['regex']}\n")

            for var, match in found.items():
                variables_matches[var].extend(match)
            if found and rule.get("stop_on_find", False):
                break
        return {
            key: sorted(value, key=lambda e: e["confidence"], reverse=True)
            for key, value in variables_matches.items()
        }


# use this for vertical beacons
def extract_with_vertical_beacon_pattern(
    beacon_pattern: str, document__text: str, max_allignment_offset: int = 2
) -> List[dict]:
    """Vertical extractor that looks at the line under the beacon."""
    beacon_match = re.search(beacon_pattern, document__text)
    if not beacon_match:
        return []

    beacon_length = len(beacon_match.group())
    page_index, line_index, column_index = position_to_triplet(beacon_match.start(), document__text)
    page_text = document__text.replace("\x0c", "\f").split("\f")[page_index]
    page_lines = page_text.split('\n')
    line_under = page_lines[line_index + 1]

    # if the line udner is empty, look on the next one
    line_offset = 1 if line_under.strip() else 2

    under_beacon_position = triplet_to_position(
        page_index, line_index + line_offset, column_index - max_allignment_offset, document__text
    )
    value_start_match = re.search(r'[^ ]', document__text[under_beacon_position:])

    if not value_start_match or value_start_match.start() > beacon_length:
        return []

    value_start = under_beacon_position + value_start_match.start()

    # Finding the first whitespace that is not under the beacon anymore (to the right)
    value_end = None
    for match in re.finditer(r' |$', document__text[value_start:]):
        value_end = value_start + match.start()
        if value_end - under_beacon_position > beacon_length:
            break

    if not value_end:
        return []

    value = document__text[value_start:value_end]

    result = [{'text': value.strip(), 'location': value_start, 'confidence': 100}]
    return result


def create_soft_lookup_pattern(
    names: List[str],
    max_distance: int = 2,
    case_insensitive: bool = True,
    do_unidecode: bool = True,
    separator: str = ' ',
    regex_version=re.V0,
    escape_special_characters: bool = True,
):
    """Generate a regex pattern to find multiple needles in a haystack.
    Params:
        names - needles to find
        max_distance - number of allowed errors in fuzzy match
        do_unidecode - remove accents from characters
        separator - regexpattern to replace whitespaces within a name
        regex_version - the version to use for the compiled pattern.
                        Default V0 is compatible with re library.
    Returns a compiled regex pattern.
    """
    assert max_distance < 3
    names = sorted(names, key=lambda x: len(x), reverse=True)
    # if do_unidecode:
    #     names = map(unidecode.unidecode, names)
    if escape_special_characters:
        names = map(lambda x: re.escape(x, literal_spaces=True), names)
    names = map(lambda x: x.replace(' ', separator), names)

    pattern = '|'.join(names)
    pattern = f'(\\b({pattern})\\b)'

    if case_insensitive:
        pattern = f'(?i){pattern}'

    if max_distance > 0:
        pattern = f'{pattern}{{e<{max_distance + 1}}}'

    pattern = re.compile(pattern, regex_version)
    return pattern


def add_to_dictionary(text, regex, gen_id=None, weight=0):
    parameter = re.MULTILINE
    parameter |= re.BESTMATCH

    try:
        pattern = re.compile(regex, parameter)
    except Exception as e:
        logger.error(f"\nERROR: {e}, GEN_ID: {gen_id}, REGEX: {regex}\n")
        pattern = None

    found = {}
    try:
        if pattern:
            for m in pattern.finditer(text, overlapped=False, concurrent=True, timeout=20):
                dictionary = m.groupdict()
                for i in dictionary:
                    if dictionary[i] is None or len(dictionary[i].strip()) == 0:
                        continue
                    found_list = found.setdefault(i, [])

                    found_list.append(
                        {
                            "text": dictionary[i],
                            "confidence": weight,
                            "location": m.start(i),
                            "context": m.group(0),
                            "gen_id": gen_id,
                            "version": f"regex-{gen_id}",
                        }
                    )
    except TimeoutError:
        logger.info("timeout in add_to_dictionary")
        pass

    return found


def extract_text_under_matches(
    matches: List,
    document__text: str,
    num_lines: int = 2,
    left_offset: int = 6,
    right_offset: Optional[int] = 10,
    stop_on_non_empty_line: bool = True,
    start_line: int = 1,
):
    """Return the text under each of the given regex matches
    num_lines is the number of lines to consider under the beacon.
    left_offset is the number of characters to consider left of the beacon
    right_offset is the number of characters to consider right of the beacon.
    if right_offset is missing, all characters until the end of the line are considered
    if start_line = 0, it will also return the text after the beacon
    """
    results = []
    for match in matches:
        beacon_length = len(match['text'])
        beacon_start = match['location']
        page_index, line_index, char_index = position_to_triplet(beacon_start, document__text)
        page_text = document__text.replace("\x0c", "\f").split("\f")[page_index]
        page_lines = page_text.split('\n')
        lines_to_consider = [line_index + offset + start_line for offset in range(num_lines)]
        lines_to_consider = [l for l in lines_to_consider if l < len(page_lines)]
        if not lines_to_consider:
            return []

        text_under_beacon = ''
        for line_index in lines_to_consider:
            line = page_lines[line_index]
            left_char_limit = max(0, char_index - left_offset)
            right_char_limit = (
                char_index + beacon_length + right_offset if right_offset is not None else len(line)
            )
            line_text_under_beacon = line[left_char_limit:right_char_limit]
            text_under_beacon += line_text_under_beacon + '\n'
            if stop_on_non_empty_line and line_text_under_beacon.strip():
                break

        if start_line == 0:
            text_under_beacon = text_under_beacon[left_offset + beacon_length :]

        left = beacon_start
        right = triplet_to_position(
            page_index, lines_to_consider[-1], len(page_lines[lines_to_consider[-1]]), document__text
        )
        context = document__text[left : right + 1]
        result = {
            'text': text_under_beacon,
            'location': beacon_start,
            'context': context,
            'confidence': 100,
        }
        results.append(result)
    return results


def extract_text_under_beacons(
    document__text: str,
    beacon_pattern: str,
    num_lines: int = 2,
    left_offset: int = 6,
    right_offset: Optional[int] = 10,
    stop_on_non_empty_line: bool = False,
    start_line: int = 1,
) -> List[dict]:
    """Return the text under each occurrence of a beacon pattern."""
    beacon_matches = re.finditer(beacon_pattern, document__text)
    beacon_matches = [{'text': m.group(), 'location': m.start()} for m in beacon_matches]
    results = extract_text_under_matches(
        beacon_matches,
        document__text,
        num_lines,
        left_offset,
        right_offset,
        stop_on_non_empty_line,
        start_line,
    )
    return results
