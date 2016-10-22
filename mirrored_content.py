
import datetime
import hashlib
import logging
import re
import time
import urllib
import wsgiref.handlers

import requests
import webapp2
import transform_content
import memcache

###############################################################################

EXPIRATION_DELTA_SECONDS = 3600

# EXPIRATION_DELTA_SECONDS = 10
memcache = memcache.Client(['127.0.0.1:11211'])


logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')

IGNORE_HEADERS = frozenset([
    "set-cookie",
    "expires",
    "cache-control",

    # Ignore hop-by-hop headers
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
])

TRANSFORMED_CONTENT_TYPES = frozenset([
    "text/html",
    "text/css",
])

MAX_CONTENT_SIZE = 0#10 ** 6 - 600

requests.adapters.DEFAULT_RETRIES =  10
s = requests.session()
s.keep_alive = False

###############################################################################


class MirroredContent(object):
    def __init__(self, original_address, translated_address,
                 status, headers, data, base_url):
        self.original_address = original_address
        self.translated_address = translated_address
        self.status = status
        self.headers = headers
        self.data = data
        self.base_url = base_url

    @staticmethod
    def get_by_key_name(key_name):
        return memcache.get(key_name)

    @staticmethod
    def fetch_and_store(key_name, base_url, translated_address, mirrored_url):
        """Fetch and cache a page.

        Args:
          key_name: Hash to use to store the cached page.
          base_url: The hostname of the page that's being mirrored.
          translated_address: The URL of the mirrored page on this site.
          mirrored_url: The URL of the original page. Hostname should match
            the base_url.

        Returns:
          A new MirroredContent object, if the page was successfully retrieved.
          None if any errors occurred or the content could not be retrieved.
        """
        logging.debug("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        logging.debug("Fetching '%s'", mirrored_url)
        headers = {
            'content-type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'
            }
        try:
            response = requests.get(mirrored_url,headers=headers)
        except Exception:
            logging.exception("Could not fetch URL")
            return None

        adjusted_headers = {}
        for key, value in response.headers.iteritems():
            adjusted_key = key.lower()
            if adjusted_key not in IGNORE_HEADERS:
                adjusted_headers[adjusted_key] = value

        content = response.content
        page_content_type = adjusted_headers.get("content-type", "")
        for content_type in TRANSFORMED_CONTENT_TYPES:
            # startswith() because there could be a 'charset=UTF-8' in the header.
            if page_content_type.startswith(content_type):
                content = transform_content.TransformContent(base_url, mirrored_url,
                                                             content)
                break

        new_content = MirroredContent(
            base_url=base_url,
            original_address=mirrored_url,
            translated_address=translated_address,
            status=response.status_code,
            headers=adjusted_headers,
            data=content)

        # Do not memcache content over 1MB
        if len(content) < MAX_CONTENT_SIZE:
            if not memcache.set(key_name, new_content):
                logging.error('memcache.add failed: key_name = "%s", '
                              'original_url = "%s"', key_name, mirrored_url)
        else:
            logging.warning("Content is over 1MB; not memcached")

        return new_content
