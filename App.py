import json
import logging
import logging.config
import os

import schedule
import time
# import scripts.gdelt as gdelt
import datetime

import yaml

logger = logging.getLogger('App')


def main():
    with open('./config/config.json') as json_config_file:
        config = json.load(json_config_file)

    setup_directories(config)
    setup_logging()


def setup_logging(default_path="./config/logging_config.yml",
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


def setup_directories(config):
    if not os.path.exists(config["gdelt"]["csv_directory"]):
        os.makedirs(config["gdelt"]["csv_directory"])

    if not os.path.exists(config["logging"]["log_directory"]):
        os.makedirs(config["logging"]["log_directory"])

    if not os.path.exists(config["gdelt"]["in_process_csv_directory"]):
        os.makedirs(config["gdelt"]["in_process_csv_directory"])

    if not os.path.exists(config["gdelt"]["processed_csv_directory"]):
        os.makedirs(config["gdelt"]["processed_csv_directory"])


def job():
    current_dt = datetime.datetime.now()
    print(str(current_dt))
    # gdelt.run()


if __name__ == '__main__':
    main()
    # schedule.every().hour.at(":03").do(job)
    # schedule.every().hour.at(":18").do(job)
    # schedule.every().hour.at(":33").do(job)
    # schedule.every().hour.at(":48").do(job)
    #
    # while 1:
    #     schedule.run_pending()
    #     time.sleep(1)
