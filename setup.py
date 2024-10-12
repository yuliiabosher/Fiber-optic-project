import logging
import json
from utilities.get_data import downloader
import os
import sys

logging.basicConfig(level=logging.INFO)

data_folder = "data"
sources = "config/data_sources.json"

if __name__ == "__main__":

    if not os.path.exists(sources):
        logging.error("Data Sources File Does Not Exist")
        sys.exit(0)

    try:
        sources = json.load(open(sources))
    except Exception as e:
        logging.error("An Error Occured %s" % e)

    if not os.path.exists(data_folder):
        os.mkdir(data_folder)
    breakpoint()
    for filename, link in sources.items():
        filename = os.path.join(data_folder, filename)
        logging.info("Downloading %s" % link)
        _, errors = downloader(filename, link)
        if not errors:
            logging.info("Saved as %s" % filename)
