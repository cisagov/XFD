"""Utility functions for handling CSV and JSON data.

Provides functions to convert between JSON and CSV formats, create checksums,
write CSV data to files, and sanitize formulas in strings.
"""

# Standard Python Libraries
import csv
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from io import StringIO
import json
import logging
from typing import Any, Dict, Iterable, List, Sequence

LOGGER = logging.getLogger(__name__)
_FORMULA_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@")


def sanitize_strings_for_excel(cell: Any) -> Any:
    """
    Neutralize potential formulas in string cells for Excel/Sheets.

    - Only touches str; numbers/dates/None pass through.
    - If the (trimmed) string starts with = + - @, prefix with ' to force text.
    """
    if cell is None or isinstance(cell, (int, float, Decimal, bool, date, datetime)):
        return cell
    s = str(cell)
    return ("'" + s) if s.lstrip().startswith(_FORMULA_PREFIXES) else s


def sanitize_row_for_excel(row: Iterable[Any]) -> list[Any]:
    """Apply sanitize_strings_for_excel to a whole row."""
    return [sanitize_strings_for_excel(v) for v in row]


def write_rows_to_csv(
    fieldnames: Sequence[str],
    rows: Iterable[Iterable[Any]],
    *,
    sanitize: bool = True,
    newline: str = "",
) -> str:
    """Write rows to a CSV string."""
    buf = StringIO(newline=newline)
    writer = csv.writer(buf)
    writer.writerow(list(fieldnames))
    if sanitize:
        for r in rows:
            writer.writerow(sanitize_row_for_excel(r))
    else:
        for r in rows:
            writer.writerow(r)
    return buf.getvalue()


def queryset_to_csv(
    qs: Any,
    fieldnames: Sequence[str],
    *,
    sanitize: bool = True,
    newline: str = "",
) -> str:
    """Export a Django QuerySet to a CSV string."""
    rows = qs.values_list(*fieldnames)
    return write_rows_to_csv(fieldnames, rows, sanitize=sanitize, newline=newline)


def create_checksum(data: str) -> str:
    """Generate a SHA-256 checksum for a given string.

    Args:
        data (str): The input string.

    Returns:
        str: The SHA-256 hash of the input string.
    """
    hashable_data = isinstance(data, str) and data or json.dumps(data)
    hash_object = sha256(hashable_data.encode("utf-8"))
    return hash_object.hexdigest()


def json_to_csv(json_array: List[Dict[str, Any]]) -> str:
    """Convert a list of dictionaries (JSON) into a CSV string.

    Args:
        json_array (List[Dict[str, Any]]): List of dictionaries representing JSON data.

    Returns:
        str: CSV string representing the input JSON data.
    """
    if not json_array:
        return ""

    # Extract headers (keys) from the first object in the array
    headers = list(json_array[0].keys())

    # Prepare rows for the CSV
    rows = []
    for obj in json_array:
        row = [
            ",".join(obj[header])
            if isinstance(obj[header], list)
            else ('"{}"'.format(obj[header]) if obj[header] is not None else '""')
            for header in headers
        ]
        rows.append(",".join(row))

    # Combine headers and rows into CSV format
    csv_data = [",".join(headers)] + rows
    return "\n".join(csv_data)


def convert_to_csv(data: List[Dict[str, Any]]) -> str:
    """Convert a list of dictionaries to a CSV string.

    Serializes nested JSON fields to ensure they remain valid JSON strings.

    Args:
        data (List[Dict[str, Any]]): A list of dictionaries to convert.

    Returns:
        str: CSV string.

    Raises:
        ValueError: If the data is empty or invalid.
    """
    if not data:
        raise ValueError("The data list is empty. Cannot process CSV.")

    # Extract headers from the first dictionary
    headers = data[0].keys()

    # Serialize any nested JSON fields
    def serialize_nested_json(row):
        serialized_row = {}
        for key, value in row.items():
            if isinstance(value, (dict, list)):  # If value is a nested structure
                serialized_row[key] = json.dumps(value)  # Serialize it to a JSON string
            else:
                serialized_row[key] = value
        return serialized_row

    # Prepare CSV buffer
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=headers)
    writer.writeheader()

    # Write serialized rows
    for row in data:
        writer.writerow(serialize_nested_json(row))

    csv_data = csv_buffer.getvalue()
    csv_buffer.seek(0)

    return csv_data


def convert_csv_to_json(csv_data: str) -> List[Dict[str, Any]]:
    """Convert CSV string data into a JSON-like list of dictionaries.

    Parses any JSON content within columns.

    Args:
        csv_data (str): CSV data as a string.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing rows in the CSV.

    Raises:
        ValueError: If the CSV data is empty or invalid.
    """
    csv.field_size_limit(10**6)

    try:
        if not csv_data.strip():
            raise ValueError("The CSV data is empty or contains only whitespace.")

        # Create a StringIO buffer from the CSV string
        csv_buffer = StringIO(csv_data)

        # Read the CSV data
        reader = csv.DictReader(csv_buffer)

        # Ensure the CSV has a header
        if reader.fieldnames is None:
            raise ValueError("CSV data has no headers. Cannot process into JSON.")

        # Convert rows to a list of dictionaries
        json_data = []
        for row in reader:
            # Skip empty rows
            if not any(row.values()):
                continue

            # Parse JSON fields
            for key, value in row.items():
                if (
                    value
                    and value.strip().startswith("{")
                    and value.strip().endswith("}")
                ):
                    try:
                        row[key] = json.loads(
                            value
                        )  # Convert JSON strings to Python objects
                    except json.JSONDecodeError:
                        pass  # If it's not valid JSON, leave it as a string
                if (
                    value
                    and value.strip().startswith("[")
                    and value.strip().endswith("]")
                ):
                    try:
                        row[key] = json.loads(
                            value
                        )  # Convert JSON strings to Python objects
                    except json.JSONDecodeError:
                        pass  # If it's not valid JSON, leave it as a string

            json_data.append(row)

        return json_data

    except Exception as e:
        LOGGER.exception("Error processing CSV to JSON: %s", e)
        raise ValueError


def write_csv_to_file(csv_data: str, file_path: str) -> None:
    """Write CSV data (string) to a file.

    Args:
        csv_data (str): CSV data as a string.
        file_path (str): Path to save the CSV file.

    Returns:
        None
    """
    try:
        with open(file_path, mode="w", encoding="utf-8") as file:
            file.write(csv_data)
        LOGGER.info("CSV data successfully written to file: %s", file_path)
    except Exception as e:
        LOGGER.error("An error occurred while writing to the file: %s", e)
