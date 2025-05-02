# TODO This file should use local imports everywhere as it is imported and used in so many places
import codecs
import json
import logging
import math
import os
import re
from collections import OrderedDict
from copy import deepcopy
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from mega import Mega



import regex as re

logger = logging.getLogger(__name__)
alphanum_regex = re.compile(r'\W+')
alphanumeric_filter = lambda t: alphanum_regex.sub('', t)


def get_results(content, field_name):
    keys_to_return = ["text", "confidence", "location", "version", "value"]
    results = []
    for candidate in content.get(field_name, []):
        candidate["version"] = candidate["gen_id"]
        candidate["value"] = get_text_only(candidate["text"])
        results.append({key: candidate[key] for key in candidate if key in keys_to_return})
    return results


def cleanup_text(text):
    if not isinstance(text, str):
        return ""
    text = text.replace('\xad', '-')
    text = text.replace('\xa0', ' ')
    text = text.replace('\ufeff', ' ')
    text = text.replace("ﬁ", "fi")
    text = text.replace("œ", "oe")
    text = text.replace("—", "-")
    text = text.replace("‚", ",")
    text = text.replace("е", "e")
    text = text.replace("с", "c")
    text = text.replace("а", "a")
    text = text.replace("р", "p")
    text = text.replace("Ę", "E")
    return text


def is_time(keyword):
    return True if re.match(r"\d{1,2}[:\-;/]\d{1,2}", keyword) else False


def position_to_triplet(position: int, text: str) -> List[int]:
    text = text.replace("\x0c", "\f")
    page = text[: position + 1].count('\f')
    line = text[max(0, text[:position].rfind(('\f'))) : position].count('\n')
    char = position - max(0, text[:position].rfind('\n') + 1, text[:position].rfind('\f') + 1)
    return [page, line, char]


def triplet_to_position(page, line, char, text):
    if page == 0 and line == 0 and char == 0:
        return -1
    if page == -1 and line == -1 and char == -1:
        return -1
    if page < -1 or line < -1 or char < -1:
        return -1
    if len(text) == 0:
        return -1
    pages = text.split('\f')
    if len(pages) == 0:
        return -1
    pagesbefore = sum([len(p) + 1 for i, p in enumerate(pages) if i < page])  # add 1 for \f
    pagetext = pages[page]
    lines = pagetext.split('\n')
    linesbefore = sum([len(l) + 1 for i, l in enumerate(lines) if i < line])  # add 1 for \n
    textualcharacter = pagesbefore + linesbefore + char
    return textualcharacter


def strip_multispace(text: str) -> str:
    text = re.sub(" +", " ", text)
    return re.sub("^ +", "", text, flags=re.M)


def remove_spaces(text: str) -> str:
    return re.sub(r"\s+", "", text, flags=re.M)


def get_numbers_only(text: str) -> str:
    return re.sub('\\D+', '', text)


def get_text_only(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", text)


def remove_numbers(text: str) -> str:
    return re.sub(r"\d", "", text)


def get_text_w_underscores(text: str) -> str:
    return re.sub(r"\W", "", text)


def get_alphabets_only(text: str) -> str:
    return re.sub(r"[^A-Za-z]", "", text)


# returns a similarity score (the higher the better, in range from 0.0 to 1.0)
def similar(string_a, string_b):
    return SequenceMatcher(None, string_a, string_b).ratio()


def get_text(candidate):
    return str(candidate.get("value", candidate.get("text", "")))


def get_confidence(candidate):
    return int(float(candidate.get("confidence", 0)))


def get_location(candidate):
    if "location" in candidate:
        location = candidate["location"]
    elif "upper_left" in candidate:
        location = int(
            float(
                f"{abs(candidate['upper_left'][0])}{abs(candidate['upper_left'][1])}{abs(candidate['upper_left'][2])}"
            )
        )
    else:
        location = -1
    return location


# check to see if the two candidates are at the same location or not
def check_same_location(candidate_1, candidate_2):
    start_c1 = get_location(candidate_1)
    start_c2 = get_location(candidate_2)
    end_c1 = start_c1 + len(get_text(candidate_1))
    end_c2 = start_c2 + len(get_text(candidate_2))
    span_c1 = set(range(start_c1, end_c1))
    span_c2 = set(range(start_c2, end_c2))
    common = span_c1.intersection(span_c2)
    return len(common) >= (((len(span_c1) + len(span_c2)) / 2) / 2)


def remove_duplicate_results(
    candidate_list,
    location_based_check=False,
    similarity_threshold=0.7,
    only_value_based_check=False,
    pages_whitelist=None,
):
    result_list = candidate_list
    candidates_to_remove = []
    for i, result in enumerate(result_list):
        if "visual_coord" in result:
            continue
        # only proceeding with the candidates which has a some text
        if len(get_text(result)) > 0:  # i < len(result_list) and
            for next_result in result_list[i + 1 :]:
                if "visual_coord" in result:
                    continue
                # skip comparison in case of location_based_check=True and the candidates are not at the same location
                if location_based_check and not check_same_location(result, next_result):
                    continue
                if similar(get_text(result), get_text(next_result)) >= similarity_threshold:
                    to_remove = (
                        next_result if get_confidence(result) >= get_confidence(next_result) else result
                    )
                    if to_remove not in candidates_to_remove:
                        candidates_to_remove.append(to_remove)

    if pages_whitelist is not None:
        for candidate in result_list:
            if "visual_coord" in candidate and candidate["visual_coord"][0] not in pages_whitelist:
                if candidate not in candidates_to_remove:
                    candidates_to_remove.append(candidate)
            elif all(
                location_field not in candidate
                for location_field in ["location", "visual_coord", "upper_left"]
            ) or ("upper_left" in candidate and candidate["upper_left"][0] not in pages_whitelist):
                if candidate not in candidates_to_remove:
                    candidates_to_remove.append(candidate)

    # removing the found duplicates
    for c_to_remove in candidates_to_remove:
        if c_to_remove in result_list:
            result_list.remove(c_to_remove)
    refined_result_list = []
    for i, result in enumerate(result_list):
        if only_value_based_check:
            # removing the candidates with the EXACT text/value AT ANY LOCATION
            if get_text(result) not in [
                get_text(tmp_result) for tmp_result in refined_result_list if "visual_coord" not in tmp_result
            ]:
                refined_result_list.append(result)
        else:
            # removing the candidates with the EXACT text/value AT THE SAME LOCATION
            if get_text(result) not in [
                get_text(tmp_result)
                for tmp_result in refined_result_list
                if (
                    ("visual_coord" not in tmp_result)
                    and ("visual_coord" not in result)
                    and (check_same_location(result, tmp_result))
                )
            ]:
                refined_result_list.append(result)
    return refined_result_list


def merged_if_no_overlap_otherwise_first(lines):
    result = ""
    length = max([0] + [len(line) for line in lines])

    for i in range(length):
        for line in lines:
            if len(line) > i and line[i] != " ":
                # we already wrote something in that position
                if len(result) == i + 1:
                    return lines[0]
                result += line[i]
        if len(result) == i:
            result += " "

    return result


def convert_date_to_requested_format(date_in_dd_mm_yyyy: str, date_format: str) -> str:
    date_in_dd_mm_yyyy = date_in_dd_mm_yyyy.split("-")
    if date_format == "DD/MM/YYYY":
        reformatted_date = date_in_dd_mm_yyyy[0] + "/" + date_in_dd_mm_yyyy[1] + "/" + date_in_dd_mm_yyyy[2]
    elif date_format == "DD/MM/YY":
        reformatted_date = (
            date_in_dd_mm_yyyy[0] + "/" + date_in_dd_mm_yyyy[1] + "/" + date_in_dd_mm_yyyy[2][-2:]
        )
    elif date_format == "DD.MM.YY":
        reformatted_date = (
            date_in_dd_mm_yyyy[0] + "." + date_in_dd_mm_yyyy[1] + "." + date_in_dd_mm_yyyy[2][-2:]
        )
    elif date_format == "DD-MM-YY":
        reformatted_date = (
            date_in_dd_mm_yyyy[0] + "-" + date_in_dd_mm_yyyy[1] + "-" + date_in_dd_mm_yyyy[2][-2:]
        )
    elif date_format == "YYYYMMDD":
        reformatted_date = date_in_dd_mm_yyyy[2] + date_in_dd_mm_yyyy[1] + date_in_dd_mm_yyyy[0]
    elif date_format == "YYMMDD":
        reformatted_date = date_in_dd_mm_yyyy[2][-2:] + date_in_dd_mm_yyyy[1] + date_in_dd_mm_yyyy[0]
    elif date_format == "YYYY-MM-DD":
        reformatted_date = date_in_dd_mm_yyyy[2] + "-" + date_in_dd_mm_yyyy[1] + "-" + date_in_dd_mm_yyyy[0]
    else:  # going back to the original: DD-MM-YYYY
        reformatted_date = date_in_dd_mm_yyyy[0] + "-" + date_in_dd_mm_yyyy[1] + "-" + date_in_dd_mm_yyyy[2]
    return reformatted_date



def get_page_range_for_nth_section(document, i):
    return get_page_range_for_section(document["prediction"]["sections"], document.text_per_page, i)


def get_page_range_for_section(sections: list, text_per_page: str, i: int):
    section_page_range_start = sections[i]["page"]
    if i == len(sections) - 1:
        section_page_range_end = len(text_per_page)
    else:
        section_page_range_end = sections[i + 1]["page"]
    return section_page_range_start, section_page_range_end


def get_page_header(page_text, nr_lines=5, ignore_empty_lines=False):
    document_lines = page_text.strip().split("\n")
    if ignore_empty_lines:
        document_lines = [x for x in document_lines if len(x) > 0]
    if len(document_lines) > nr_lines:
        header = "\n".join(document_lines[:nr_lines])
    else:
        header = page_text
    return header


def get_document_header(document__text, nr_lines=5, ignore_empty_lines=False):
    pages = document__text.strip().split("\f")
    pages_header = "\f".join(
        [get_page_header(p, nr_lines=nr_lines, ignore_empty_lines=ignore_empty_lines) for p in pages]
    )
    return pages_header


def get_page_footer(page_text, nr_lines=5, ignore_empty_lines=False):
    document_lines = page_text.strip().split("\n")
    if ignore_empty_lines:
        document_lines = [x for x in document_lines if len(x) > 0]
    if len(document_lines) > nr_lines:
        footer = "\n".join(document_lines[-nr_lines:])
    else:
        footer = page_text
    return footer


def get_document_footer(document__text, nr_lines=5, ignore_empty_lines=False):
    pages = document__text.strip().split("\f")
    pages_footer = "\f".join(
        [get_page_footer(p, nr_lines=nr_lines, ignore_empty_lines=ignore_empty_lines) for p in pages]
    )
    return pages_footer


# remove exact duplicate candidates
# and increase confidence in case a candidate comes up multiple times in the original list
def get_unique_candidates(all_candidates, confidence_boost=5):
    # dont make confidences 100 as then we cant use the rule engine on top of it
    unique_candidates = []
    for candidate in all_candidates:
        already_found = [c.get("value", c["text"]) for c in unique_candidates]
        if candidate.get("value", candidate["text"]) in already_found:
            prev_index = already_found.index(candidate.get("value", candidate["text"]))
            prev_confidence = unique_candidates[prev_index]["confidence"]
            new_confidence = max(prev_confidence, candidate["confidence"]) + confidence_boost
            unique_candidates[prev_index]["confidence"] = new_confidence
            unique_candidates[prev_index]["version"] = candidate.get("version", "prediction")
        else:
            unique_candidates.append(candidate)
    # sort by confidence
    unique_candidates = sorted(unique_candidates, key=lambda k: k["confidence"], reverse=True)

    for candidate in unique_candidates:
        candidate["confidence"] = max(0, min(99, candidate["confidence"]))
    return unique_candidates


# check to see if the context of a candidate contains a blacklisted pattern
def blacklisted_word_in_context(blacklisted_patterns, candidate_location, document__text):
    page, line, _ = position_to_triplet(candidate_location, document__text)
    context_line = document__text.split("\f")[page].split("\n")[line].lower()
    blacklisted_in_context = False
    for blacklisted in blacklisted_patterns:
        if re.search(blacklisted, context_line, re.I):
            blacklisted_in_context = True
            break
    return blacklisted_in_context


def get_page_doc_type_mapping(sections):
    """Get a mapping from page number to a doc type for every page of the document up until the last section. The key
    -1 is used to store information about possible pages after the first page of the last section."""
    sections = sorted(sections, key=lambda x: x['page'])
    page_doc_type_mapping = OrderedDict({section['page']: section['document_type'] for section in sections})
    for section_number, (page, doc_type) in enumerate(page_doc_type_mapping.copy().items()):
        if section_number + 1 == len(page_doc_type_mapping):
            page_doc_type_mapping[-1] = doc_type
            break
        elif page + 1 in page_doc_type_mapping:
            continue
        page_doc_type_mapping[page] = doc_type
    return page_doc_type_mapping


def find_largest_words(document_reverse_list, number_of_largest_words_to_return=1):
    """This function takes a list of reverses and returns the largest word visually contained therein"""
    if not document_reverse_list:
        return []
    return_words = []
    word_and_heights = []
    for page in document_reverse_list:
        page_height = page["height"]
        page_width = page["width"]
        for line in page["lines"]:
            for _, v in line.items():
                lowerleft = v["vertices"][0]
                upperleft = v["vertices"][3]
                height = upperleft["y"] - lowerleft["y"]
                relative_height = round(height / page_height, 3)

                lowerright = v["vertices"][1]
                width = lowerright["x"] - lowerleft["x"]
                relative_width = round(width / page_width, 3)

                word_and_heights.append((v["word"], relative_height, relative_width))
    if not word_and_heights:
        return []
    word_and_heights = np.array(word_and_heights, dtype=np.dtype("O"))
    median_height = np.median(word_and_heights[:, 1])

    weight = np.array((10, 4))  # Weight for height and width
    word_and_heights = np.c_[
        word_and_heights, word_and_heights[:, 1] * weight[0] + word_and_heights[:, 2] * weight[1]
    ]
    sorted_indices = np.argsort(word_and_heights[:, 3])

    largest_words = word_and_heights[sorted_indices]

    idx = 1  # Start at -1 instead of 0
    prev_largest_word = [None, 0]
    while len(return_words) < number_of_largest_words_to_return and idx < len(largest_words):
        word = largest_words[-idx]

        if (
            word[1] > median_height * 1.25
        ):  # Only return words that are 25% larger than the median; avoids FPs
            logger.debug(f"Size of word {word[0]}: {word[1]} vs median {median_height}")
            # If the current word is 4 times smaller than the previous largest word, skip it, cannot be considered large word
            if prev_largest_word[1] > word[1] * 4:
                idx += 1  # Ensure we skip to next word
                continue
            return_words.append(word[0])
            prev_largest_word = word  # Store the last largest word
        idx += 1

    return return_words


def get_percentage_of_page(page_text: str, percentage: float, use_begin_of_page: bool = True):
    if not page_text:
        return page_text
    page_text = page_text.split("\n")
    page_length = len(page_text)
    if use_begin_of_page:
        return "\n".join(page_text[: math.ceil(page_length * percentage)])
    return "\n".join(page_text[math.floor(page_length * (1 - percentage)) :])


def load_json(json_path) -> dict:
    with open(json_path) as json_file:
        json_data = json.load(json_file)
    return json_data


def save_json(data, save_path, verbose=False):
    with open(save_path, 'w', encoding='utf8') as f:
        json.dump(data, f, sort_keys=False, indent=4, ensure_ascii=False)
    if verbose:
        print(f"json saved at {save_path}")


def save_text(text, save_path, verbose=False):
    with codecs.open(save_path, "w+", "utf-8-sig") as text_file:
        text_file.write(text)
    if verbose:
        print(f"text saved at {save_path}")


def add_last_page_to_sections(sections, total_pages):
    sections = sorted(sections, key=lambda k: k["page"])
    for i, section in enumerate(sections):
        if i < len(sections) - 1:
            section["last_page"] = sections[i + 1]["page"] - 1
        else:
            section["last_page"] = total_pages - 1
    return sections


def modulo_check(number, module=97):
    last_two_digits = int(number[-2:])
    if last_two_digits == module:
        last_two_digits = 0
    return int(number[:-2]) % module == last_two_digits


def check_valid_attachments_present(document__files):
    """checks the document__files to see if there are any valid attachments present in the uploaded file"""
    valid_attachments_present = False
    for attachment in document__files:
        if attachment["page"] == 0 and os.path.splitext(attachment["filename"])[1].lower() in [
            ".msg",
            ".eml",
        ]:
            continue
        if attachment["page"] > 0 and attachment["page_count"] > 0:
            valid_attachments_present = True
            break
    return valid_attachments_present


def get_results(content, field_name):
    keys_to_return = ["text", "confidence", "location", "version", "value"]
    results = []
    for candidate in content.get(field_name, []):
        candidate["version"] = candidate["gen_id"]
        results.append({key: candidate[key] for key in candidate if key in keys_to_return})
    return results


def mask_text(text, start, stop):
    if start > len(text) or stop > len(text) or start >= stop:
        return text
    return text[:start] + " " * (stop - start) + text[stop:]


def mask_matching_lines(negative_for_line, text):
    for match in re.finditer('^.*(' + negative_for_line + ').*$', text, re.MULTILINE):
        text = mask_text(text, match.start(), match.end())
    return text


def mask_matching_pages(negative_for_page, text):
    for match in re.finditer('(?:^|\f)([^\f]*' + negative_for_page + '[^\f]*)(?:\f|$)', text):
        text = mask_text(text, match.start(1), match.end(1))
    return text


def remove_consecutive_empty_lines(page_text: str, no_of_consecutive: int = 10) -> str:
    """Remove all consecutive empty lines from page_text if their number exceeds the no.of consecutive"""
    page_lines = page_text.split("\n")
    empty_lines = [i for i in range(len(page_lines)) if not page_lines[i]]
    consecutive = 0
    remove_lines = []

    for i in range(len(empty_lines) - 1):
        if consecutive >= no_of_consecutive:
            remove_lines.append(empty_lines[i])
        if empty_lines[i + 1] == empty_lines[i] + 1:
            consecutive += 1
        # restart the counter
        else:
            consecutive = 0

    for i in sorted(remove_lines, reverse=True):
        del page_lines[i]

    page_text = "\n".join(page_lines)
    return page_text

def get_top_half_of_page_text(text: str) -> str:
    page_length = len(text.split("\n"))
    top_of_page_text = "\n".join(text.split("\n")[: int(page_length * 3 / 5) + 1])
    return top_of_page_text


def format_string_for_conversion(input_string: str) -> str:
    """
    Format the string for easy conversion to float/int
    """
    return input_string.replace(",", ".").strip("%").strip(" ")


def convert_percentage_string_to_float(string_to_convert: str) -> Union[float, None]:
    """
    Fast function converting a percentage string to a float. Used only when computing amounts with percentages from text
    """
    string_to_convert = format_string_for_conversion(string_to_convert)
    try:
        return float(string_to_convert)
    except (ValueError, TypeError):
        return None


def convert_to_int(data_to_convert: Union[str, int, float, None]) -> Union[int, None]:
    """
    Function for converting a varaible (can be string, int or a float) to an int
    """
    # If its a string with percentage sign then remove it
    if isinstance(data_to_convert, str):
        data_to_convert = format_string_for_conversion(data_to_convert)
    try:
        return int(data_to_convert)
    except (ValueError, TypeError):
        return None

def download_mega_file(mega_link, download_dir=None):
    """
    Download a file from a public Mega link without login.
    
    Args:
        mega_link (str): The Mega file sharing link
        download_dir (str, optional): Directory to save the file
    
    Returns:
        str: Full path to the downloaded file
        None: If download fails
    """
    try:
        # Initialize Mega without login
        mega = Mega()
        
        # Set default download directory
        if download_dir is None:
            download_dir = os.path.join(os.getcwd(), 'downloads')
        
        # Create download directory if it doesn't exist
        os.makedirs(download_dir, exist_ok=True)
        
        # Download the file directly from the public link
        downloaded_file = mega.download_url(mega_link, download_dir)
        
        if downloaded_file:
            print(f"File downloaded successfully: {downloaded_file}")
            return downloaded_file
        else:
            print("Failed to download file")
            return None
    
    except Exception as e:
        print(f"Download error: {e}")
        return None
