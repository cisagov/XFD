"""
This module contains the pipeline classes for the web scraper.

The pipelines process the items returned by the spiders.
"""

# Standard Python Libraries
import json

# Third-Party Libraries
from scrapy.exceptions import DropItem


class ExportFilePipeline:
    """Print file contents to the console."""

    def __init__(self, print=print):
        """
        Initialize the ExportFilePipeline class.

        Args:
            print (function, optional): A function to print the output. Defaults to print.
        """
        self.urls_seen = set()
        self.print = print

    def process_item(self, item, spider=None):
        """
        Process each item that goes through the pipeline.

        If the item's URL has been seen before, it raises a DropItem exception. Otherwise, it prints the item and returns it.

        Args:
            item (dict): The item to process.
            spider (Spider, optional): The spider that produced the item. Defaults to None.

        Returns:
            dict: The processed item.
        """
        if item["url"] in self.urls_seen:
            raise DropItem("Duplicate item found with url: %s" % item["url"])
        self.urls_seen.add(item["url"])
        self.print("database_output: " + json.dumps(item))
        return item
