import urllib
import webapp2
import cgi
import logging
import csv
import datetime

from google.appengine.ext import blobstore
from google.appengine.ext.blobstore import BlobInfo
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers

from FileMetadata import FileMetadata
from BaseHandler import BaseHandler
from FreewayData import Highway, Station, Detector, LoopData

"""
Upload request handlers
"""

class FileUploadFormHandler(BaseHandler):
	""" FileUploadFormHandler class definition
	
	Provides a file upload interface
	"""
	def get(self):
		""" respond to HTTP GET requests
	
		Display a user interface for uploading data to Blobstore
		"""
		q = FileMetadata.query()
		results = q.fetch(10)
		
		items = [result for result in results]
		
		length = len(items)
		
		upload_url = blobstore.create_upload_url('/upload')
				
		self.render_template("import.html",{
							 "length": length,
							 "items": items,
							 "upload_url":upload_url})
	
	
	def post(self):
		""" respond to HTTP POST requests
	
		Perform import of blob data referenced by blobkey
		"""
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
	""" FileUploadHandler class definition
	
	Handle uploads of data to Blobstore
	"""
	def post(self):
		""" respond to HTTP POST requests
	
		Create FileMetadata entity in Datastore to keep track of uploaded files
		"""
		blob_info = self.get_uploads()[0]
		
		file_metadata = FileMetadata(id = str(blob_info.key()),
									 content_type = blob_info.content_type,
									 creation = blob_info.creation,
									 filename = blob_info.filename,
									 size = blob_info.size,
									 md5_hash = blob_info.md5_hash,
									 blobkey = str(blob_info.key()))
									 
		file_metadata.put()
		self.redirect("/import")


class FileInfoHandler(BaseHandler):
	""" FileInfoHandler class definition
	
	Display information about uploaded files
	"""
	def get(self, file_id):
		""" Respond to HTTP GET requests
	
		Render a file info page from FileMetadata matching key file_id
		
		Args:
		  file_id: a key that references some FileMetadata entity in the Datastore
		"""
		file_key = ndb.Key(FileMetadata, str(urllib.unquote(file_id)).strip())
		file_info = file_key.get()
		logging.info("File info:%s for key:%s", file_info, file_key)
		if not file_info:
			self.error(404)
			return
		self.render_template("file_info.html", {
							 'file_info': file_info
							 })


class FileDownloadHandler(blobstore_handlers.BlobstoreDownloadHandler):
	""" FileDownloadHandler class definition
	
	Download files from Blobstore
	"""
	def get(self, file_id):
		""" Respond to HTTP GET requests
		
		Download files from Blobstore that are referenced by file_id key
		
		Args:
		  file_id a key that references some FileMetadata entity in the Datastore
		"""
		file_info = str(urllib.unquote(file_id)).strip()
		if not file_info:
			self.error(404)
			return
		self.send_blob(BlobInfo.get(file_id), save_as=False)


app = webapp2.WSGIApplication([
							   ('/import', FileUploadFormHandler),
							   ('/upload', FileUploadHandler),
							   ('/file/(.*)/download', FileDownloadHandler),
							   ('/file/(.*)', FileInfoHandler),
							   ('/blobstore/(.*)', FileDownloadHandler),
							   ], debug=True)