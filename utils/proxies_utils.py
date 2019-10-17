import logging
import urllib.request
import socket
import urllib.error

import App
from utils import config_utils

config = config_utils.get_app_config()
logger = logging.getLogger("Utils")


def is_bad_proxy(pip, handler):
    try:
        proxy_handler = urllib.request.ProxyHandler({handler: pip})
        opener = urllib.request.build_opener(proxy_handler)
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        url = config["proxy"]["test_url"]
        logger.info('Testing proxy at:' + url)
        req = urllib.request.Request(url)  # change the URL to test here
        sock = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        logger.info('Error code: ', e.code)
        return e.code
    except Exception as detail:
        logger.info("ERROR:", detail)
        return True
    return False


def main():
    http_proxies = config["proxy"]["http_ip_port"]
    https_proxies = config["proxy"]["https_ip_port"]
    default_timeout = config["proxy"]["default_timeout"]

    socket.setdefaulttimeout(default_timeout)

    for currentProxy in http_proxies:
        if is_bad_proxy(currentProxy, 'http'):
            logger.info("Bad HTTP Proxy: " + currentProxy)
        else:
            logger.info("HTTP is working: " + currentProxy)

    for currentProxy in https_proxies:
        if is_bad_proxy(currentProxy, 'https'):
            logger.info("Bad HTTPS Proxy: " + currentProxy)
        else:
            logger.info("HTTPS is working: " + currentProxy)


if __name__ == '__main__':
    App.setup_directories()
    App.setup_logging()
    main()
