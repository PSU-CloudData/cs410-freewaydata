import webapp2
from google.appengine.ext import ndb
import datetime
import logging
import jinja2

from FreewayData import Highway, Station, Detector, LoopData

class UtilitiesDataHandler(webapp2.RequestHandler):

	template_env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"), autoescape=True)

	# method definition for the 'GET' HTTP operation
	def get(self):
		if self.request.get("combine", default_value = '') == "combine":
			starttime = datetime.datetime.now()
			self.response.out.write("Performing combine...<br/>")
			self.combine()
			endtime = datetime.datetime.now()
			response = "Completed combine in %f seconds<br/>" % (endtime - starttime).seconds
			self.response.out.write(response)
		elif self.request.get("delete", default_value = '') == "delete":
			response = "Deleting all loop data..."
			self.response.out.write(response)
			self.deleteData()
		else:
			self.response.out.write(self.template_env.get_template("utilities.html").render({}))


	# combine method performs combination of Station and Detector data
	def combine(self):
		stns = []
		# store all detectors in stations
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