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
import logging
import datetime
from google.appengine.ext import blobstore

from BaseHandler import BaseHandler
from FreewayData import Highway, Station, Detector, LoopData

class FreewayDataHandler(BaseHandler):

	def getHighways(self):
		hwy_q = Highway.query()
		results = hwy_q.fetch(12)
		hwys = [hwy for hwy in results]
		return hwys
	
	def getStationsForHighway(self, hw, dir):
		hwy_q = Highway.query(Highway.highwayname == hw, Highway.shortdirection == dir)
		stations = []
		for hwy in hwy_q.fetch():
			stn_q = Station.query(Station.highwayid == hwy.highwayid)
			results = stn_q.fetch(40)
			stations = [station for station in results]
		return stations
	
	def get(self):
		if self.request.get("startdate", default_value = '09/15/2011') != '':
			sdate = self.request.get("startdate", default_value = '09/22/2011')
		else:
			sdate = '09/15/2011'
		
		if self.request.get("enddate", default_value = '11/15/2011') != '':
			edate = self.request.get("enddate", default_value = '11/15/2011')
		else:
			edate = '11/15/2011'
			
		start = "%sT%s:00:00" % (sdate, self.request.get("starttime", default_value = '00'))
		
		end = "%sT%s:00:00" % (edate, self.request.get("endtime", default_value = '00'))
		
		hwy = self.request.get("highway", default_value = "I-205")

		dir = self.request.get("direction", default_value = "N")
		
		logging.debug("Start: "+start+" End: "+end+" Highway: "+hwy+" Direction: "+dir+"<br/>")
		logging.debug(datetime.datetime.strptime(start, "%m/%d/%YT%H:%M:%S"))
		logging.debug(" to ")
		logging.debug(datetime.datetime.strptime(end, "%m/%d/%YT%H:%M:%S"))
		logging.debug("<br/>")
			
		hwys = self.getHighways()
		hwys_length = len(hwys)
		
		stns = self.getStationsForHighway(hwy, dir)
		stns_length = len(stns)
		
		self.render_template("index.html",
							 {"highway":hwy,
							  "direction":dir,
							  "highways":hwys,
							  "hwys_length":hwys_length,
							  "stations": stns,
							 "stns_length":stns_length})
		#self.travelTime(start, end, hwy, dir)
		


	def travelTime(self, start, end, hw, dir):
		stations = getStationsForHighway(hw)
		
		for stn in stations:
			self.response.out.write("Checking station with id:%d<br/>" % stn.stationid)
			for det in stn.detectors:
				det_count_speed = 0
				det_total_speed = 0
				self.response.out.write("&nbsp;&nbsp;")
				self.response.out.write(det)
				self.response.out.write("<br/>")
				det_q = LoopData.query( LoopData.detectorid == det.detectorid,
									   LoopData.starttime >= datetime.datetime.strptime(start, "%m/%d/%YT%H:%M:%S"),
									   LoopData.starttime <= datetime.datetime.strptime(end, "%m/%d/%YT%H:%M:%S"))
				for data in det_q.fetch():
					det_total_speed += data.speed
					det_count_speed += 1
					if det_count_speed > 0 and det_total_speed > 0:
						travel_time = (10.09/(det_total_speed/det_count_speed))*60
						response = "&nbsp;&nbsp;Average travel time for station:%s detector:%s (%s readings):%f minutes<br/>" % (det.stationid, det.detectorid, det_count_speed, travel_time)
					self.response.out.write(response)


app = webapp2.WSGIApplication([
    ('/', FreewayDataHandler)
], debug=True)
