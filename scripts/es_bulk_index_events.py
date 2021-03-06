import json
import logging
import os
from os.path import isfile, join

import requests

import App
from utils import config_utils

config = config_utils.get_app_config()

json_directory_path = config["app"]["json_directory"]
logger = logging.getLogger("App")
es_host = config["elasticsearch"]["host"]
es_port = config["elasticsearch"]["port"]


def run():
    try:
        logger.info("Running script to bulk index events to Elasticsearch cluster host={} port={}".format(
            es_host, es_port))

        json_files = [f for f in os.listdir(json_directory_path) if
                      isfile(join(json_directory_path, f))]

        if json_files:
            logger.info("Number of json file(s) to process: {}".format(len(json_files)))
            for i in range(len(json_files)):
                logger.info("Processing #{} json file ...".format(i + 1))
                json_file = json_files[i]
                json_file_path = json_directory_path + '\\' + json_file

                logger.debug("Opening file {}".format(json_file))
                data_file = open(json_file_path)
                data = data_file.read()

                logger.info("Sending bulk request to ES")
                url = "http://{}:{}/_bulk".format(es_host, es_port)
                headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
                response = requests.post(url, data=data, headers=headers)
                logger.debug("Response status code = {}".format(response.status_code))
                response_content = json.loads(response.text)
                logger.debug(response.text)
                if (response.status_code != 200) or response_content["errors"]:
                    logger.error(
                        '{} Unable to index some events in json file {}'.format(response.status_code, json_file))
                    for j in range(len(response_content["items"])):
                        item = response_content["items"][j]
                        if "error" in item["index"].keys():
                            logger.error(item["index"]["error"])
                else:
                    os.remove(json_file_path)

                logger.info("Completed sending bulk request to ES")
                data_file.close()

    except Exception:
        logger.exception("Failed to run bulk index script")


if __name__ == '__main__':
    App.setup_directories()
    App.setup_logging()
    run()
