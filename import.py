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
from google.appengine.ext.blobstore import BlobInfo
from google.appengine.ext import db, ndb
from google.appengine.ext import webapp

from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import template

""" FileMetadata db class definition """
class FileMetadata(db.Model):
	content_type = db.StringProperty()
	creation = db.DateTimeProperty()
	filename = db.StringProperty()
	size = db.IntegerProperty()
	md5_hash = db.StringProperty()
	blobkey = db.StringProperty()

"""
Upload request handlers
"""
class BaseHandler(webapp.RequestHandler):
	def render_template(self, file, template_args):
		path = os.path.join(os.path.dirname(__file__), "templates", file)
		self.response.out.write(template.render(path, template_args))


class FileUploadFormHandler(BaseHandler):
	def get(self):
		q = FileMetadata.all()
		results = q.fetch(10)
				
		items = [result for result in results]

		length = len(items)
			
		self.render_template("import.html",
								 {"length": length,
								 "items": items})
				
								 
	def post(self):
		# get the resource key
		resource = self.request.get('blobkey')
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
						latlon=ndb.GeoPt(line['latlon']),
						highway=ndb.Key(Highway, line['highwayid']))
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
		elif filename == 'freeway_loopdata.csv':
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




class FileUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
	def post(self):
		blob_info = self.get_uploads()[0]
				
		file_metadata = FileMetadata(content_type = blob_info.content_type,
								creation = blob_info.creation,
								filename = blob_info.filename,
								size = blob_info.size,
								md5_hash = blob_info.md5_hash,
								blobkey = str(blob_info.key()))
		
		db.put(file_metadata)
		self.redirect("/file/%s/success" % (file_metadata.blobkey,))


class AjaxSuccessHandler(BaseHandler):
	def get(self, file_id):
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write('%s/file/%s' % (self.request.host_url, file_id))


class FileInfoHandler(BaseHandler):
	def get(self, file_id):
		file_info = FileMetadata.get_by_id(long(file_id))
		if not file_info:
			self.error(404)
			return
		self.render_template("file_info.html", {
			'file_info': file_info
		})


class FileDownloadHandler(blobstore_handlers.BlobstoreDownloadHandler):
	def get(self, file_id):
		file_info = str(urllib.unquote(file_id)).strip()
		if not file_info:
			self.error(404)
			return
		self.send_blob(BlobInfo.get(file_id), save_as=False)


class GenerateUploadUrlHandler(webapp2.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/plain'
		upload_url = blobstore.create_upload_url('/upload')
		logging.info("Upload URL:%s", upload_url)
		self.response.out.write(upload_url)


app = webapp2.WSGIApplication([
    ('/import', FileUploadFormHandler),
    ('/upload', FileUploadHandler),
    ('/generate_upload_url', GenerateUploadUrlHandler),
    ('/file/(.*)/download', FileDownloadHandler),
    ('/file/(.*)/success', AjaxSuccessHandler),
    ('/file/(.*)', FileInfoHandler),
], debug=True)