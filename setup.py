import logging
import json
from utilities.get_data import downloader, unzip
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

    for filename, link in sources.items():
        filename = os.path.join(data_folder, filename)
        logging.info("Downloading %s" % link)
        if not os.path.exists(filename):
            _, errors = downloader(filename, link)
            if not errors:
                logging.info("Saved as %s" % filename)

            if filename.endswith("zip"):
                logging.info("Unzipping %s" % filename)
                _, errors = unzip(filename, data_folder)
                if not errors:
                    logging.info("Unzipped %s" % filename)
                elif errors:
                    logging.error(
                        "An Error Occured While Unzipping %s : %s" % (filename, errors)
                    )

        else:
            logging.info("File %s Exists, Not Downloading Again" % filename)
