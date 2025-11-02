"""Split a list into chunks based on a byte size limit.

Each chunk will have a total byte size that does not exceed the specified
maximum. Chunks are stored as dictionaries containing the chunked items
and their bounds.
"""

# Standard Python Libraries
import json
from typing import Any, Dict, List


def chunk_list_by_bytes(input_list: List[Any], max_bytes: int) -> List[Dict[str, Any]]:
    """Split a list into chunks where each chunk's byte size is within max_bytes.

    Each chunk is represented as a dictionary containing the chunked items and
    their bounds.

    Args:
        input_list (List[Any]): The list to be chunked.
        max_bytes (int): Maximum bytes allowed per chunk.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary contains
        a chunk and its bounds.
    """
    chunks: List[Dict[str, Any]] = []
    current_chunk: List[Any] = []
    current_size: int = 0
    start_index: int = 0

    for idx, item in enumerate(input_list):
        # Serialize item to calculate its actual size
        try:
            item_size = len(json.dumps(item).encode("utf-8"))
        except TypeError:
            item_size = len(json.dumps(str(item)).encode("utf-8"))

        if current_size + item_size > max_bytes:
            # Add the current chunk with its bounds to the result
            chunks.append(
                {
                    "chunk": current_chunk,
                    "bounds": {
                        "start": start_index,
                        "end": start_index + len(current_chunk) - 1,
                    },
                }
            )
            # Update the start index based on the length of the processed chunk
            start_index += len(current_chunk)
            # Start a new chunk
            current_chunk = []
            current_size = 0

        current_chunk.append(item)
        current_size += item_size

    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(
            {
                "chunk": current_chunk,
                "bounds": {
                    "start": start_index,
                    "end": start_index + len(current_chunk) - 1,
                },
            }
        )

    return chunks
