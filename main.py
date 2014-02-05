#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
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
#
import webapp2
import cgi
import urllib
import jinja2

from google.appengine.ext import blobstore

class MainHandler(webapp2.RequestHandler):

	template_env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"), autoescape=True)

	def get(self):
		startdate = self.request.get("startdate")
		enddate = self.request.get("enddate")
		freeway = self.request.get("freeway")
		direction = self.request.get("direction")

		self.response.out.write(self.template_env.get_template("index.html").render(
        {"startdate": startdate,
         "enddate": enddate,
         "freeway": freeway,
         "direction": direction}))

app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
