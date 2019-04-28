import json
import logging

logger = logging.getLogger('Utils')


def get_app_config():
    app_config_path = 'config/app.json'

    try:
        with open(app_config_path) as json_config_file:
            json_config = json.load(json_config_file)
            return json_config
    except Exception:
        logger.exception("Unable to read Application properties from {}".format(app_config_path))
