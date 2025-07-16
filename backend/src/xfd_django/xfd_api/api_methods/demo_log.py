# demo_log.py
# Third-Party Libraries
from xfd_api.logger import LOGGER


def main():
    logger = LOGGER.getChild(__name__)
    logger.debug("Hello from DEBUG")  # will show only if LOG_LEVEL=DEBUG
    logger.info("Hello from INFO")


if __name__ == "__main__":
    main()
