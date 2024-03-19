"""
This module contains tests for the ExportFilePipeline class in the pipelines module.

It includes tests for different scenarios such as processing an item and handling duplicate items.
"""

# Standard Python Libraries
from unittest.mock import MagicMock

# Third-Party Libraries
import pytest
from scrapy.exceptions import DropItem

from .pipelines import ExportFilePipeline


@pytest.fixture
def pipeline():
    """
    Create an ExportFilePipeline instance with a mocked print function.

    This fixture creates a MagicMock instance and uses it as the print parameter for the
    ExportFilePipeline instance. The ExportFilePipeline instance is then returned for use in the tests.
    """
    return ExportFilePipeline(print=MagicMock())


@pytest.fixture
def item():
    """
    Create a sample item for testing.

    This fixture creates a dictionary that represents a sample item with specific headers and other details.
    The item is then returned for use in the tests.
    """
    return {
        "status": 200,
        "url": "https://www.cisa.gov",
        "domain_name": "www.cisa.gov",
        "body": "<body>Hello world</body>",
        "response_size": 24,
        "headers": [
            {"name": "Server", "value": "Apache"},
            {"name": "X-Content-Type-Options", "value": "nosniff, nosniff"},
            {
                "name": "Link",
                "value": '<https://www.cisa.gov/>; rel="shortlink", <https://www.cisa.gov/>; rel="canonical", <https://www.cisa.gov/home>; rel="revision"',
            },
            {"name": "X-Ua-Compatible", "value": "IE=edge"},
            {"name": "Content-Language", "value": "en"},
            {"name": "X-Frame-Options", "value": "SAMEORIGIN"},
            {"name": "X-Generator", "value": "Drupal 8 (https://www.drupal.org)"},
            {"name": "Content-Type", "value": "text/html; charset=UTF-8"},
            {"name": "Vary", "value": "Accept-Encoding"},
            {"name": "Content-Encoding", "value": "gzip"},
            {"name": "Cache-Control", "value": "private, no-cache, must-revalidate"},
            {"name": "Expires", "value": "Sun, 18 Oct 2020 00:08:03 GMT"},
            {"name": "Date", "value": "Sun, 18 Oct 2020 00:08:03 GMT"},
            {"name": "Content-Length", "value": "15726"},
            {"name": "Connection", "value": "keep-alive"},
            {
                "name": "Strict-Transport-Security",
                "value": "max-age=31536000 ; includeSubDomains",
            },
        ],
    }


def test_print_item(pipeline, item):
    """
    Test the process_item method of the ExportFilePipeline class with a sample item.

    This function calls the process_item method of the ExportFilePipeline instance (provided by the pipeline fixture)
    with the sample item (provided by the item fixture) and checks if the print function was called.
    """
    pipeline.process_item(item)
    pipeline.print.assert_called_once()


def test_discard_duplicate_items(pipeline, item):
    """
    Test the process_item method of the ExportFilePipeline class with duplicate items.

    This function calls the process_item method of the ExportFilePipeline instance (provided by the pipeline fixture)
    with the sample item (provided by the item fixture) twice and checks if a DropItem exception is raised the second time.
    It also checks if the print function was called only once.
    """
    pipeline.process_item(item)
    pipeline.print.assert_called_once()
    pipeline.print.reset_mock()
    with pytest.raises(DropItem):
        pipeline.process_item(item)
    pipeline.process_item(dict(item, url="new url"))
    pipeline.print.assert_called_once()
