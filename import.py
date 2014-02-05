import os
import urllib
import webapp2
import cgi
import logging
import csv
import datetime
import jinja2

from FreewayData import Highway, Station, Detector, LoopData

from google.appengine.ext import blobstore
from google.appengine.ext import db
from google.appengine.ext import webapp

from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import template

"""
Blob file model for datastore
"""
class FileInfo(db.Model):
	blob = blobstore.BlobReferenceProperty(required=True)
	uploaded_at = db.DateTimeProperty(required=True, auto_now_add=True)



"""
Upload request handlers
"""
class BaseHandler(webapp.RequestHandler):
	def render_template(self, file, template_args):
		path = os.path.join(os.path.dirname(__file__), "templates", file)
		self.response.out.write(template.render(path, template_args))


class FileUploadFormHandler(BaseHandler):
	def get(self):
		self.render_template("import.html", {})


class FileUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
	def post(self):
		blob_info = self.get_uploads()[0]
		file_info = FileInfo(blob=blob_info.key())
		db.put(file_info)
		self.redirect("/file/%d/success" % (file_info.key().id(),))


class AjaxSuccessHandler(BaseHandler):
	def get(self, file_id):
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write('%s/file/%s' % (self.request.host_url, file_id))


class FileInfoHandler(BaseHandler):
	def get(self, file_id):
		file_info = FileInfo.get_by_id(long(file_id))
		if not file_info:
			self.error(404)
			return
		self.render_template("file_info.html", {
			'file_info': file_info
		})


class FileDownloadHandler(blobstore_handlers.BlobstoreDownloadHandler):
	def get(self, file_id):
		file_info = FileInfo.get_by_id(long(file_id))
		if not file_info or not file_info.blob:
			self.error(404)
			return
		self.send_blob(file_info.blob, save_as=False)


class GenerateUploadUrlHandler(webapp2.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/plain'
		upload_url = blobstore.create_upload_url('/upload')
		logging.info("Upload URL:%s", upload_url)
		self.response.out.write(upload_url)


"""
Datastore import handler
"""
class DatastoreImportHandler(blobstore_handlers.BlobstoreDownloadHandler):
	def get(self, resource):
		# get the resource key
		resource = str(urllib.unquote(resource))
		# get BlobInfo from the blobstore using resource key
		blob_info = blobstore.BlobInfo.get(resource)
		# get the filename of the blob
		filename = blob_info.filename
		# get a BlobReader object for the resource
		blob_reader = blobstore.BlobReader(resource)
		# get a DictReader object to use for parsing the resource
		csv_reader = csv.DictReader(blob_reader)
		# get resource headers
		headers = csv_reader.fieldnames
		if filename == 'highways.csv':
			for line in csv_reader:
				h = Highway(id=line['highwayid'],
							highwayid=int(line['highwayid']),
							shortdirection=line['shortdirection'],
							direction=line['direction'],
							highwayname=line['highwayname'])
				h.put()
				self.response.out.write(h)
		elif filename == 'freeway_stations.csv':
			for line in csv_reader:
				s = Station(id=line['stationid'],
						stationid=int(line['stationid']),
						highwayid=int(line['highwayid']),
						milepost=float(line['milepost']),
						locationtext=line['locationtext'],
						upstream=int(line['upstream']),
						downstream=int(line['downstream']),
						stationclass=int(line['stationclass']),
						numberlanes=int(line['numberlanes']),
						latlon=ndb.GeoPt(line['latlon']))
				s.put()
				self.response.out.write(s)
		elif filename == 'freeway_detectors.csv':
			for line in csv_reader:
				d = Detector(id=line['detectorid'],
						detectorid=int(line['detectorid']),
						highwayid=int(line['highwayid']),
						milepost=float(line['milepost']),
						locationtext=line['locationtext'],
						detectorclass=int(line['detectorclass']),
						lanenumber=int(line['lanenumber']),
						stationid=int(line['stationid']))
				d.put()
				self.response.out.write(d)
		elif filename == 'fw_ld_92211.csv':
			for line in csv_reader:
				if 'detectorid' in line:
					l = LoopData(detectorid=int(line['detectorid']),
						starttime=datetime.datetime.strptime(line['starttime'], "%Y-%m-%d %H:%M:%S-07"),
						status=int(line['status']),
						dqflags=int(line['dqflags']))
					if line['volume'] != '':
						setattr(l, 'volume', int(line['volume']))
					if line['speed'] != '':
						setattr(l, 'speed', int(line['speed']))
					if line['occupancy'] != '':
						setattr(l, 'occupancy', int(line['occupancy']))
					l.put()
			self.response.out.write("Finished data import")
		else:
			self.response.out.write("Unrecognized data file: "+blob_info.filename)


app = webapp2.WSGIApplication([
    ('/import', FileUploadFormHandler),
    ('/upload', FileUploadHandler),
    ('/generate_upload_url', GenerateUploadUrlHandler),
    ('/file/(.*)/download', FileDownloadHandler),
    ('/file/(.*)/success', AjaxSuccessHandler),
    ('/file/(.*)', FileInfoHandler),
], debug=True)