import json


def get_app_config():
    with open('config/app.json') as json_config_file:
        json_config = json.load(json_config_file)
        return json_config
