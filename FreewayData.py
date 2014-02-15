from google.appengine.ext import ndb

class LoopData (ndb.Model):
	""" LoopData ndb class definition """
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
	""" Detector ndb class definition """
	detectorid = ndb.IntegerProperty(indexed = True)
	highwayid = ndb.IntegerProperty()
	milepost = ndb.FloatProperty()
	locationtext = ndb.StringProperty()
	detectorclass = ndb.IntegerProperty()
	lanenumber = ndb.IntegerProperty()
	stationid = ndb.IntegerProperty()

class Station (ndb.Model):
	""" Station ndb class definition """
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
	""" Highway ndb class definition """
	highwayid = ndb.IntegerProperty(indexed = True)
	shortdirection = ndb.StringProperty()
	direction = ndb.StringProperty()
	highwayname = ndb.StringProperty()
	stations = ndb.KeyProperty(repeated=True)

class TravelTime(ndb.Model):
	""" A class used to store sum/count IntervalLoopData values """
	sum = ndb.IntegerProperty()
	count = ndb.IntegerProperty()

class IntervalLoopData(ndb.Model):
	"""A helper class that represents IntervalLoopData counter values
	
	Store processed information from mapreduce jobs into the Datastore as IntervalLoopData entities
	for easy retrieval. Each entity represents a single day/detector combo, and will contain a single
	day_speed TravelTime property (count and sum of speed measurements) for each date that is contained in the dataset.
	Each entity has a day_speed Time Travel property, as well as corresponding lists of TravelTime properties
	containing up to 24 hour_speed, 96 fifteenmin_speed, and 480 fivemin_speed objects.
	"""
	date = ndb.DateProperty(indexed=True)
	detector = ndb.KeyProperty(indexed=True)
	day_speed = TravelTime()
	hour_speed = ndb.StructuredProperty(TravelTime, repeated=True)
	fifteenmin_speed = ndb.StructuredProperty(TravelTime, repeated=True)
	fivemin_speed = ndb.StructuredProperty(TravelTime, repeated=True)
