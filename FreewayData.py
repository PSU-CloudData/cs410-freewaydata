import webapp2
from google.appengine.ext import ndb
import datetime
import logging

class LoopData (ndb.Model):
	detectorid = ndb.IntegerProperty(indexed = True)
	starttime = ndb.DateTimeProperty(indexed = True)
	volume = ndb.IntegerProperty(default = 0)
	speed = ndb.IntegerProperty(default = 0)
	occupancy = ndb.IntegerProperty(default = 0)
	status = ndb.IntegerProperty()
	dqflags = ndb.IntegerProperty()
	minute	= ndb.ComputedProperty(lambda self: self.starttime.minute)
	hour = ndb.ComputedProperty(lambda self: self.starttime.hour)

class Detector (ndb.Model):
	detectorid = ndb.IntegerProperty(indexed = True)
	highwayid = ndb.IntegerProperty()
	milepost = ndb.FloatProperty()
	locationtext = ndb.StringProperty()
	detectorclass = ndb.IntegerProperty()
	lanenumber = ndb.IntegerProperty()
	stationid = ndb.IntegerProperty()

class Station (ndb.Model):
	stationid = ndb.IntegerProperty(indexed = True)
	highwayid = ndb.IntegerProperty()
	milepost = ndb.FloatProperty()
	locationtext = ndb.StringProperty()
	upstream = ndb.IntegerProperty()
	downstream = ndb.IntegerProperty()
	stationclass = ndb.IntegerProperty()
	numberlanes = ndb.IntegerProperty()
	latlon = ndb.GeoPtProperty()
	detectors = ndb.StructuredProperty(Detector, repeated=True)
	highway = ndb.KeyProperty()

class Highway (ndb.Model):
	highwayid = ndb.IntegerProperty(indexed = True)
	shortdirection = ndb.StringProperty()
	direction = ndb.StringProperty()
	highwayname = ndb.StringProperty()

class FreewayDataHandler(webapp2.RequestHandler):
	def get(self):
		start = "%sT%s:00:00" % (self.request.get("startdate", default_value = '09/22/2011'),
								self.request.get("starttime", default_value = '00'))
		end = "%sT%s:00:00" % (self.request.get("enddate", default_value = '09/22/2011'),
								self.request.get("endtime", default_value = '00'))
		hwy = self.request.get("highway")
		dir = self.request.get("direction")
		
		logging.debug("Start: "+start+" End: "+end+" Highway: "+hwy+" Direction: "+dir+"<br/>")
		logging.debug(datetime.datetime.strptime(start, "%m/%d/%YT%H:%M:%S"))
		logging.debug(" to ")
		logging.debug(datetime.datetime.strptime(end, "%m/%d/%YT%H:%M:%S"))
		logging.debug("<br/>")
				
		self.travelTime(start, end, hwy, dir)

	def travelTime(self, start, end, hw, dir):
		hwy_q = Highway.query(Highway.highwayname == hw, Highway.shortdirection == dir)
		for hwy in hwy_q.fetch():
			stn_q = Station.query(Station.highwayid == hwy.highwayid)
			for stn in stn_q.fetch():
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
    ('/freewaydata', FreewayDataHandler)
], debug=True)
