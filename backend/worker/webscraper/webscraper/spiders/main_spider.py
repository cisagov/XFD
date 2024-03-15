"""
This module contains the MainSpider class for the webscraper project.

The MainSpider class is a Scrapy spider that crawls and scrapes data from the specified start URLs.
"""

# Standard Python Libraries
from urllib.parse import urlparse

# Third-Party Libraries
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class MainSpider(CrawlSpider):
    """
    MainSpider is a Scrapy spider that crawls and scrapes data from the specified start URLs.

    It uses the LinkExtractor to follow links and the parse_item method to process the scraped data.
    """

    name = "main"

    rules = (Rule(LinkExtractor(), callback="parse_item", follow=True),)

    def __init__(self, *args, **kwargs):
        """
        Initialize the MainSpider class.

        It reads the start URLs from a file and sets the allowed domains based on these URLs.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        with open(self.domains_file) as f:
            self.start_urls = f.read().split("\n")
        self.allowed_domains = [urlparse(url).netloc for url in self.start_urls]

    def parse_start_url(self, response):
        """
        Parse the start URL.

        This method gets called when the spider opens the start URL. It returns the result of the parse_item method.

        Args:
            response (Response): The response object for the start URL.

        Returns:
            dict: The result of the parse_item method.
        """
        return self.parse_item(response)

    def parse_item(self, response):
        """
        Parse the response and extract the data.

        This method gets called for each response that the spider receives. It extracts the data from the response and returns it as a dictionary.

        Args:
            response (Response): The response to parse.

        Returns:
            dict: The extracted data.
        """
        try:
            body_decoded = response.body.decode()
        except UnicodeDecodeError:
            body_decoded = "<binary>"

        headers = []
        for name, values in response.headers.items():
            for value in values:
                headers.append({"name": name.decode(), "value": value.decode()})

        item = dict(
            status=response.status,
            url=response.url,
            domain_name=urlparse(response.url).netloc,
            body=body_decoded,
            response_size=len(response.body),
            headers=headers,
        )
        yield item
