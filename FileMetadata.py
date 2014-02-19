from google.appengine.ext import ndb

class FileMetadata(ndb.Model):
	"""A helper class that will hold metadata for uploaded blobs.
	
	Keep track of where a file is uploaded to, along with other file statistics.
	"""
	content_type = ndb.StringProperty()
	creation = ndb.DateTimeProperty()
	filename = ndb.StringProperty()
	size = ndb.IntegerProperty()
	md5_hash = ndb.StringProperty()
	blobkey = ndb.StringProperty()
	daily_speed_sum = ndb.BlobKeyProperty()
	chunks = ndb.BlobKeyProperty(repeated=True)
	chunk_job = ndb.StringProperty()
