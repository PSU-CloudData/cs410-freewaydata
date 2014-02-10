from google.appengine.ext import ndb

""" LoopData ndb class definition """
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

""" Detector ndb class definition """
class Detector (ndb.Model):
	detectorid = ndb.IntegerProperty(indexed = True)
	highwayid = ndb.IntegerProperty()
	milepost = ndb.FloatProperty()
	locationtext = ndb.StringProperty()
	detectorclass = ndb.IntegerProperty()
	lanenumber = ndb.IntegerProperty()
	stationid = ndb.IntegerProperty()

""" Station ndb class definition """
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

""" Highway ndb class definition """
class Highway (ndb.Model):
	highwayid = ndb.IntegerProperty(indexed = True)
	shortdirection = ndb.StringProperty()
	direction = ndb.StringProperty()
	highwayname = ndb.StringProperty()
	stations = ndb.KeyProperty(repeated=True)