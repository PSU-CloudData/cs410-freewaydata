import webapp2
from google.appengine.ext import ndb
import datetime
import logging
import jinja2

from FreewayData import Highway, Station, Detector, LoopData
from BaseHandler import BaseHandler

class UtilitiesDataHandler(BaseHandler):

	# method definition for the 'GET' HTTP operation
	def get(self):
		if self.request.get("combine", default_value = '') == "detectors":
			starttime = datetime.datetime.now()
			self.response.out.write("Performing detector combine...<br/>")
			self.combine_detectors()
			endtime = datetime.datetime.now()
			response = "Completed detector combine in %f seconds<br/>" % (endtime - starttime).seconds
			self.response.out.write(response)
		elif self.request.get("combine", default_value = '') == "stations":
			starttime = datetime.datetime.now()
			self.response.out.write("Performing station combine...<br/>")
			self.combine_stations()
			endtime = datetime.datetime.now()
			response = "Completed station combine in %f seconds<br/>" % (endtime - starttime).seconds
			self.response.out.write(response)
		elif self.request.get("delete", default_value = '') == "delete":
			response = "Deleting all loop data..."
			self.response.out.write(response)
			self.deleteData()
		else:
			self.render_template("utilities.html", {})


	# combine method performs combination of Station and Detector data
	def combine_detectors(self):
		# store all detectors in stations
		stns = []
		det_q = Detector.query()
		for det in det_q.fetch():
			stn_q = Station.query()
			for stn in stn_q.fetch():
				stns.append(stn)
				if stn.stationid == det.stationid:
					stn.detectors.append(det)
					stn.put()
					response = "<hr>Put detector:%s in station:%s<br/>" % (det.key, stn)
					self.response.out.write(response)
		#remove detectors from datatore after combination
		self.deleteDetectors()


	def combine_stations(self):
		# store all stations in highways
		stns = []
		stn_q = Station.query()
		for stn in stn_q.fetch():
			logging.info("Got station with id %s", stn.stationid)
			hwy_q = Highway.query(Highway.highwayid == stn.highwayid)
			for hwy in hwy_q.fetch():
				logging.info("Appending station to highway %s", hwy)
				hwy.stations.append(stn.key)
				hwy.put()


	def deleteDetectors(self):
		detector_keys = Detector.query().fetch(keys_only = True)
		detector_entities = ndb.get_multi(detector_keys)
		ndb.delete_multi([d.key for d in detector_entities])


	def deleteData(self):
		loopdata_keys = LoopData.query().fetch(keys_only = True)
		loopdata_entities = ndb.get_multi(loopdata_keys)
		ndb.delete_multi([l.key for l in loopdata_entities])


app = webapp2.WSGIApplication([
    ('/utilities', UtilitiesDataHandler)
], debug=True)