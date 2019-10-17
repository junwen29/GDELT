import datetime
import logging
import logging.config
import os

import yaml

from scripts import gdelt, gdacs
from utils import config_utils

logger = logging.getLogger('App')


def main():
    setup_directories()
    setup_logging()
    run_gdelt_script()
    run_gdacs_script()


def setup_logging(default_path="./config/logging.yml",
                  default_level=logging.INFO,
                  env_key="LOG_CFG"):
    """
        Setup logging configuration

        This reads a .yml file and extracts the relevant logging information
        required by the logging module.

        """

    path = default_path
    value = os.getenv(env_key, None)

    if value:
        path = value

    # Open the logging configuration file
    if os.path.exists(path):
        with open(path, "rb") as f:
            config = yaml.safe_load(f.read())

            # Append the date stamp to the filename for each handler
            # This is so each log file has a unique filename if run
            # on a separate date.
            # This can be changed to suit needs, hourly/minutely etc.
            for i in (config["handlers"].keys()):
                if i != "console":
                    log_filename = config["handlers"][i]["filename"]
                    base, extension = os.path.splitext(log_filename)
                    today = datetime.datetime.today()
                    log_filename = "{}{}{}".format(base,
                                                   today.strftime("_%Y_%m_%d"),
                                                   extension)
                    config["handlers"][i]["filename"] = log_filename

            logging.config.dictConfig(config)
            f.close()

    else:
        logging.basicConfig(level=default_level)


def setup_directories():
    config = config_utils.get_app_config()
    if not os.path.exists(config["app"]["data_directory"]):
        data_directory = config["app"]["data_directory"]
        data_directory.replace('\\', os.sep).replace('/', os.sep)
        os.makedirs(data_directory)

    if not os.path.exists(config["logging"]["log_directory"]):
        log_directory = config["logging"]["log_directory"]
        log_directory.replace('\\', os.sep).replace('/', os.sep)
        os.makedirs(log_directory)

    if not os.path.exists(config["gdelt"]["in_process_csv_directory"]):
        in_process_csv_directory = config["gdelt"]["in_process_csv_directory"]
        in_process_csv_directory.replace('\\', os.sep).replace('/', os.sep)
        os.makedirs(in_process_csv_directory)

    if not os.path.exists(config["gdelt"]["processed_csv_directory"]):
        processed_csv_directory = config["gdelt"]["processed_csv_directory"]
        processed_csv_directory.replace('\\', os.sep).replace('/', os.sep)
        os.makedirs(processed_csv_directory)

    if not os.path.exists(config["app"]["json_directory"]):
        json_directory = config["app"]["json_directory"]
        json_directory.replace('\\', os.sep).replace('/', os.sep)
        os.makedirs(json_directory)

    if not os.path.exists(config["app"]["ib_directory"]):
        ib_directory = config["app"]["ib_directory"]
        ib_directory.replace('\\', os.sep).replace('/', os.sep)
        os.makedirs(ib_directory)

    if not os.path.exists(config["app"]["xml_directory"]):
        xml_directory = config["app"]["xml_directory"]
        xml_directory.replace('\\', os.sep).replace('/', os.sep)
        os.makedirs(xml_directory)


def run_gdelt_script():
    time_now = datetime.datetime.now()
    logger.info("Running GDELT script at {}".format(time_now.strftime('%Y-%m-%d %H:%M:%S')))
    gdelt.run()
    time_later = datetime.datetime.now()
    logger.info("Completed running GDELT script at {}".format(time_later.strftime('%Y-%m-%d %H:%M:%S')))
    time_taken = time_later - time_now
    logger.info("Time taken = {} seconds".format(time_taken.total_seconds()))


def run_gdacs_script():
    time_now = datetime.datetime.now()
    logger.info("Running GDACS script at {}".format(time_now.strftime('%Y-%m-%d %H:%M:%S')))
    gdacs.run()
    time_later = datetime.datetime.now()
    logger.info("Completed running GDACS script at {}".format(time_later.strftime('%Y-%m-%d %H:%M:%S')))
    time_taken = time_later - time_now
    logger.info("Time taken = {} seconds".format(time_taken.total_seconds()))


if __name__ == '__main__':
    main()
