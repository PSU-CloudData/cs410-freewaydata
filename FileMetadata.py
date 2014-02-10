from google.appengine.ext import ndb

""" FileMetadata ndb class definition """
class FileMetadata(ndb.Model):
	content_type = ndb.StringProperty()
	creation = ndb.DateTimeProperty()
	filename = ndb.StringProperty()
	size = ndb.IntegerProperty()
	md5_hash = ndb.StringProperty()
	blobkey = ndb.StringProperty()
	chunks = ndb.BlobKeyProperty(repeated=True)