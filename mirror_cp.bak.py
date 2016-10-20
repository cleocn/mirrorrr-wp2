#!/usr/bin/env python
# Copyright 2008-2014 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = "Brett Slatkin (bslatkin@gmail.com)"

import datetime
import hashlib
import logging
import re
import time
import urllib
import wsgiref.handlers
# from google.appengine.api import memcache
import redis
# from google.appengine.api import urlfetch
import requests
# import webapp2
# from google.appengine.ext.webapp import template
from flask import Flask, render_template, request, redirect, make_response
from werkzeug.routing import BaseConverter
import json
# from google.appengine.runtime import apiproxy_errors
import transform_content

###############################################################################

DEBUG = False
EXPIRATION_DELTA_SECONDS = 3600

redis_config = {'host': '127.0.0.1', 'port': 6379, 'db': 0}
r = redis.StrictRedis(**redis_config)

app = Flask(__name__, template_folder='.', static_folder='static')


class RegexConverter(BaseConverter):
    def __init__(self, map, *args):
        self.map = map
        self.regex = args[0]


app.url_map.converters['regex'] = RegexConverter

# DEBUG = True
# EXPIRATION_DELTA_SECONDS = 10

HTTP_PREFIX = "http://"

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

MAX_CONTENT_SIZE = 10 ** 6 - 600


###############################################################################

def get_url_key_name(url):
    url_hash = hashlib.sha256()
    url_hash.update(url.encode('utf-8'))
    return "hash_" + url_hash.hexdigest()


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
        # return memcache.get(key_name)
        s = r.get(key_name)
        logging.debug(s)
        # logging.debug(json.loads(s))
        return s

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
        logging.debug("Fetching '%s'", mirrored_url)
        try:
            # response = urlfetch.fetch(mirrored_url)
            response = requests.get(mirrored_url)
        # except (urlfetch.Error, apiproxy_errors.Error):
        except Exception:
            logging.exception("Could not fetch URL")
            return None

        adjusted_headers = {}
        for key, value in response.headers.items():
            adjusted_key = key.lower()
            if adjusted_key not in IGNORE_HEADERS:
                adjusted_headers[adjusted_key] = value

        content = response.content
        if isinstance(content, bytes):
            content = content.decode('utf-8', 'ignore')
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
            # if not memcache.add(key_name, new_content, time=EXPIRATION_DELTA_SECONDS):
            testaaa = json.dumps(new_content.__dict__)
            # if not r.set(key_name, json.dumps(new_content)):
            if not r.set(key_name, testaaa):
                logging.error('memcache.add failed: key_name = "%s", '
                              'original_url = "%s"', key_name, mirrored_url)
        else:
            logging.warning("Content is over 1MB; not memcached")

        return new_content


###############################################################################

@app.route('/_ah/warmup')
def warmup(self):
    pass


def get_relative_url(url, scheme):
    slash = url.find("/", len(scheme + "://"))
    if slash == -1:
        return "/"
    return url[slash:]


def is_recursive_request(agent):
    # if "AppEngine-Google" in agent:
    #     logging.warning("Ignoring recursive request by user-agent=%r; ignoring")
    #     # self.error(404)
    #     return True
    return False


@app.route('/')
@app.route('/home')
def home():
    url = request.url
    scheme = request.scheme
    agent = request.user_agent
    if is_recursive_request(agent):
        return 'error'

    # Handle the input form to redirect the user to a relative url
    try:
        form_url = request.args.get("url")
    except Exception:
        form_url = None

    if form_url:
        # Accept URLs that still have a leading 'http://'
        inputted_url = urllib.parse.unquote(form_url)
        if inputted_url.startswith(HTTP_PREFIX):
            inputted_url = inputted_url[len(HTTP_PREFIX):]
        return redirect("/" + inputted_url)

    # Do this dictionary construction here, to decouple presentation from
    # how we store data.
    secure_url = None
    if request.scheme == "http":
        # secure_url = "https://%s%s" % (self.request.host, self.request.path_qs)
        secure_url = "https://%s%s" % (request.host, request.script_root + request.path)
    context = {
        "secure_url": secure_url,
    }
    # self.response.out.write(template.render("main.html", context))
    return render_template("main.html")


# @app.route('/([^/]+).*')
@app.route('/<base_url>')
def mirror(base_url):
    url = request.url
    scheme = request.scheme
    agent = request.user_agent

    if is_recursive_request(agent):
        return
    # base_url = "http://www.baidu.com"
    assert base_url

    # Log the user-agent and referrer, to see who is linking to us.
    logging.debug('User-Agent = "%s", Referrer = "%s"',
                  request.user_agent,
                  request.referrer)
    logging.debug('Base_url = "%s", url = "%s"', base_url, request.url)

    translated_address = get_relative_url(url, scheme)[1:]  # remove leading /
    mirrored_url = HTTP_PREFIX + translated_address

    # Use sha256 hash instead of mirrored url for the key name, since key
    # names can only be 500 bytes in length; URLs may be up to 2KB.
    key_name = get_url_key_name(mirrored_url)
    logging.info("Handling request for '%s' = '%s'", mirrored_url, key_name)

    content = MirroredContent.get_by_key_name(key_name)

    cache_miss = False
    if content is None:
        logging.debug("Cache miss")
        cache_miss = True
        content = MirroredContent.fetch_and_store(key_name, base_url,
                                                  translated_address,
                                                  mirrored_url)
    if content is None:
        return '404'
    if isinstance(content, bytes):
        content = content.decode('utf-8')
    if isinstance(content, MirroredContent):
        content = json.dumps(content.__dict__)
    content = json.loads(content)
    for key, value in content['headers'].items():
        response = make_response(content['data'])

        response.headers[key] = value
    if not DEBUG:
        response.headers["cache-control"] = \
            "max-age=%d" % EXPIRATION_DELTA_SECONDS

    # self.response.out.write(content.data)
    return response


if __name__ == '__main__':
    app.run(debug=True)
###############################################################################

# app = webapp2.WSGIApplication([
#     (r"/", HomeHandler),
#     (r"/main", HomeHandler),
#     (r"/_ah/warmup", WarmupHandler),
#     (r"/([^/]+).*", MirrorHandler),
# ], debug=DEBUG)
