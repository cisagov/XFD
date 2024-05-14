"""
This module defines the middlewares for the web scraper.

Middlewares are used to process incoming responses and outgoing requests and items. This module defines two types of middlewares: Spider Middleware and Downloader Middleware. The Spider Middleware processes responses before they reach the spider and processes items and requests after they have been processed by the spider. The Downloader Middleware processes requests before they are sent to the downloader and processes responses before they reach the Spider Middleware or the spider.
See documentation here:
https://docs.scrapy.org/en/latest/topics/spider-middleware.html
"""

# Third-Party Libraries
from scrapy import signals


class WebscraperSpiderMiddleware:
    """
    This class defines the Spider Middleware for the web scraper.

    The Spider Middleware processes responses before they reach the spider and processes items and requests after they have been processed by the spider.
    """

    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create spiders using Scrapy.

        Connect the spider_opened method to the spider_opened signal.
        """
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        """
        Process each response that goes through the spider middleware and into the spider.

        Return None or raise an exception.
        """
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        """
        Process the results returned from the Spider, after it has processed the response.

        Return an iterable of Request, or item objects.
        """
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        yield from result

    def process_spider_exception(self, response, exception, spider):
        """
        Handle exceptions raised by a spider or process_spider_input() method.

        This method should return either None or an iterable of Request or item objects.
        """
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        """
        Process the start requests of the spider.

        This method works similarly to the process_spider_output() method, except that it doesn’t have a response associated. It must return only requests (not items).
        """
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        yield from start_requests

    def spider_opened(self, spider):
        """Log the name of the spider when opened."""
        spider.logger.info("Spider opened: %s" % spider.name)


class WebscraperDownloaderMiddleware:
    """
    This class defines the Downloader Middleware for the web scraper.

    The Downloader Middleware processes requests before they are sent to the downloader and processes responses before they reach the Spider Middleware or the spider.
    """

    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create spiders using Scrapy.

        Connect the spider_opened method to the spider_opened signal.
        """
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        """
        Process each request that goes through the downloader middleware.

        Must either return None, a Response object, a Request object, or raise IgnoreRequest.
        """
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        """
        Process the response returned from the downloader.

        Must either return a Response object, a Request object, or raise IgnoreRequest.
        """
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        """
        Handle exceptions raised by a download handler or a process_request() method.

        Must either return None, a Response object, a Request object.
        """
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        """Log the name of the spider when it is opened."""
        spider.logger.info("Spider opened: %s" % spider.name)
