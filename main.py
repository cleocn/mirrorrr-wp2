#!/usr/bin/env python

__author__ = "Brett Slatkin (bslatkin@gmail.com)"

import datetime
import hashlib
import logging
import re
import time
import urllib
import wsgiref.handlers
import requests
import webapp2

from jinja2 import Template,Environment, FileSystemLoader 

import transform_content
import mirrored_content 

###############################################################################

# DEBUG = False
DEBUG = True
HTTP_PREFIX = "http://"
#############################################################################

def get_url_key_name(url):
    url_hash = hashlib.sha256()
    url_hash.update(url)
    return "hash_" + url_hash.hexdigest()


###############################################################################

###############################################################################

class WarmupHandler(webapp2.RequestHandler):
    def get(self):
        pass


class BaseHandler(webapp2.RequestHandler):
    def get_relative_url(self):
        slash = self.request.url.find("/", len(self.request.scheme + "://"))
        if slash == -1:
            return "/"
        return self.request.url[slash:]

    def is_recursive_request(self):
        if "AppEngine-Google" in self.request.headers.get("User-Agent", ""):
            logging.warning("Ignoring recursive request by user-agent=%r; ignoring")
            self.error(404)
            return True
        return False


# class HomeHandler(BaseHandler):
#     def get(self):
#         self.response.out.write("index")


class HomeHandler(BaseHandler):
  def get(self):
    if self.is_recursive_request():
      return

    # Handle the input form to redirect the user to a relative url
    form_url = self.request.get("url")
    if form_url:
      # Accept URLs that still have a leading 'http://'
      inputted_url = urllib.unquote(form_url)
      if inputted_url.startswith(HTTP_PREFIX):
        inputted_url = inputted_url[len(HTTP_PREFIX):]
      return self.redirect("/" + inputted_url)

    # Do this dictionary construction here, to decouple presentation from
    # how we store data.
    secure_url = None
    if self.request.scheme == "http":
      secure_url = "https://%s%s" % (self.request.host, self.request.path_qs)
    context = {
      "secure_url": secure_url,
    }

    env = Environment(loader=FileSystemLoader('./'))
    template = env.get_template("home.html") 
    self.response.out.write(template.render( context))

class MirrorHandler(BaseHandler):
    def get(self, base_url):
        # MirroredContent = mirrored_content.MirroredContent()

        if self.is_recursive_request():
            return

        assert base_url

        # Log the user-agent and referrer, to see who is linking to us.
        logging.debug('User-Agent = "%s", Referrer = "%s"  ',
                      self.request.user_agent,
                      self.request.referer)
        # logging.debug('Base_url = "%s", url = "%s"', base_url, self.request.url)

        translated_address = self.get_relative_url()[1:]  # remove leading /
        mirrored_url = HTTP_PREFIX + translated_address

        # Use sha256 hash instead of mirrored url for the key name, since key
        # names can only be 500 bytes in length; URLs may be up to 2KB.
        key_name = get_url_key_name(mirrored_url)
        logging.info("Handling request for '%s' = '%s'", mirrored_url, key_name)

        content = mirrored_content.MirroredContent.get_by_key_name(key_name)
        cache_miss = False
        if content is None:
            logging.debug("Cache miss")
            cache_miss = True
            content = mirrored_content.MirroredContent.fetch_and_store(key_name, base_url,
                                                      translated_address,
                                                      mirrored_url,self.request.host)
        if content is None:
            return self.error(404)

        # for key, value in content.headers.iteritems():
        #     self.response.headers[key] = value
        if not DEBUG:
            self.response.headers["cache-control"] = \
                "max-age=%d" % EXPIRATION_DELTA_SECONDS

        self.response.headers["content-type"] = content.headers.get("content-type", "")
        self.response.out.write(content.data)
        # self.response.out.write("index2222")


###############################################################################

app = webapp2.WSGIApplication([
    (r"/", HomeHandler),
    (r"/main", HomeHandler),
    (r"/_ah/warmup", WarmupHandler),
    (r"/([^/]+).*", MirrorHandler),
], debug=DEBUG)


def main():
    from paste import httpserver
    httpserver.serve(app, host='0.0.0.0', port='7878')


if __name__ == '__main__':
    main()
