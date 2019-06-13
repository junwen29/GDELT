import datetime
import logging
import logging.config
import os
import time

import schedule
import yaml

from utils import config_utils
from scripts import gdelt, gdacs

logger = logging.getLogger('App')


def main():
    setup_directories()
    setup_logging()

    logger.info("Completed the setup of directories & logging")

    logger.info("Setting up schedule jobs ...")

    schedule.every().hour.at(":00").do(run_gdelt_script)
    schedule.every().hour.at(":00").do(run_gdacs_script)

    schedule.every().hour.at(":15").do(run_gdelt_script)
    schedule.every().hour.at(":15").do(run_gdacs_script)

    schedule.every().hour.at(":30").do(run_gdelt_script)
    schedule.every().hour.at(":30").do(run_gdacs_script)

    schedule.every().hour.at(":45").do(run_gdelt_script)
    schedule.every().hour.at(":45").do(run_gdacs_script)

    logger.info("Completed the setup of schedule jobs")

    while 1:
        logger.debug("Waiting to run pending schedules ...")
        schedule.run_pending()
        time.sleep(1)
        logger.debug("Next run is at {}".format(schedule.next_run()))


def setup_logging(default_path="../config/logging.yml",
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

    else:
        logging.basicConfig(level=default_level)


def setup_directories():
    config = config_utils.get_app_config()
    if not os.path.exists(config["app"]["data_directory"]):
        os.makedirs(config["app"]["data_directory"])

    if not os.path.exists(config["logging"]["log_directory"]):
        os.makedirs(config["logging"]["log_directory"])

    if not os.path.exists(config["gdelt"]["in_process_csv_directory"]):
        os.makedirs(config["gdelt"]["in_process_csv_directory"])

    if not os.path.exists(config["gdelt"]["processed_csv_directory"]):
        os.makedirs(config["gdelt"]["processed_csv_directory"])

    if not os.path.exists(config["app"]["json_directory"]):
        os.makedirs(config["app"]["json_directory"])

    if not os.path.exists(config["app"]["ib_directory"]):
        os.makedirs(config["app"]["ib_directory"])

    if not os.path.exists(config["app"]["xml_directory"]):
        os.makedirs(config["app"]["xml_directory"])


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
