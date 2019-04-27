import json
import logging
import logging.config
import os

import schedule
import time

import config_utils
import scripts.gdelt as gdelt
import datetime

import yaml

logger = logging.getLogger('App')


def main():
    setup_directories()
    setup_logging()

    logger.info("Completed the setup of directories & logging")

    logger.info("Setting up schedule jobs ...")
    schedule.every().hour.at(":00").do(run_gdelt_script)
    schedule.every().hour.at(":15").do(run_gdelt_script)
    schedule.every().hour.at(":30").do(run_gdelt_script)
    schedule.every().hour.at(":45").do(run_gdelt_script)

    logger.info("Completed the setup of schedule jobs")

    while 1:
        schedule.run_pending()
        time.sleep(1)


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

    else:
        logging.basicConfig(level=default_level)


def setup_directories():
    config = config_utils.get_app_config()
    if not os.path.exists(config["gdelt"]["csv_directory"]):
        os.makedirs(config["gdelt"]["csv_directory"])

    if not os.path.exists(config["logging"]["log_directory"]):
        os.makedirs(config["logging"]["log_directory"])

    if not os.path.exists(config["gdelt"]["in_process_csv_directory"]):
        os.makedirs(config["gdelt"]["in_process_csv_directory"])

    if not os.path.exists(config["gdelt"]["processed_csv_directory"]):
        os.makedirs(config["gdelt"]["processed_csv_directory"])


def run_gdelt_script():
    logger.info("Running GDELT script at {}".format(datetime.datetime.now()))
    gdelt.run()
    logger.info("Completed running GDELT script at {}".format(datetime.datetime.now()))


if __name__ == '__main__':
    main()
