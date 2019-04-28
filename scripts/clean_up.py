import shutil

from utils import config_utils


def main():
    config = config_utils.get_app_config()
    data_directory_path = config["app"]["data_directory"]
    logs_directory_path = config["logging"]["log_directory"]
    shutil.rmtree(data_directory_path)
    shutil.rmtree(logs_directory_path)


if __name__ == '__main__':
    main()
