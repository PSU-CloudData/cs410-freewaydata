#!/usr/bin/env python

import webapp2
import logging
import os
import re
import csv
import datetime

from google.appengine.ext import ndb
from google.appengine.ext.webapp import template

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

from google.appengine.api import files
from google.appengine.api import taskqueue

from mapreduce import base_handler
from mapreduce import mapreduce_pipeline
from mapreduce import operation as op
from mapreduce import shuffler
from mapreduce import context
from mapreduce import util
from mapreduce import model

import zipfile
import StringIO

from FreewayData import Highway, Station, Detector, LoopData
from FileMetadata import FileMetadata
from BaseHandler import BaseHandler

class IndexHandler(BaseHandler):
  """ base IndexHandler for FreewayData MapReduce page
  
  The main page that users will interact with, which presents users with
  the ability to upload new data or run MapReduce jobs on their existing data.
  """

  def get(self):
    """ respond to HTTP GET requests
      
    Display main page that users will interact with, which presents users with
    the ability to upload new data or run MapReduce jobs on existing data.
	"""
    q = FileMetadata.query()
    results = q.fetch(10)

    items = [result for result in results]
    length = len(items)
	
    self.render_template("map_reduce.html",{
						 "items": items,
						 "length": length})

  def post(self):
    """ respond to HTTP POST requests
      
    Perform requested MapReduce operation on Datastore or Blobstore.
	"""
    filekey = self.request.get("filekey")
    blob_key = self.request.get("blobkey")

    if self.request.get("daily_speed_sum"):
      logging.info("Starting daily speed sum...")
      pipeline = DailySpeedSumPipeline(filekey, blob_key)
      pipeline.start()
      self.redirect(pipeline.base_path + "/status?root=" + pipeline.pipeline_id)
    else:
	  logging.info("Unrecognized operation.")

def split_into_rows(s):
	""" split a string into columns
	      
	Split s into a list of values using the ',' character as a delimiter
	"""
	return s.split('\n')


def split_into_columns(s):
	""" split a string into columns
	      
	Split s into a list of values using the ',' character as a delimiter
	"""
	s = re.sub(',,,', ',0,0,', s)
	s = re.sub(',,', ',0,', s)
	return s.split(',')


def daily_speed_sum_map(data):
	"""Daily Speed Sum map function"""
	(entry, text_fn) = data
	text = text_fn()

	for row in split_into_rows(text):
		logging.debug("Got %s", row)
		day = re.search('(2011-..-..) .*', row)
		if day:
			columns = split_into_columns(row)
			yield (day.group()[:10], columns[3])


def daily_speed_sum_reduce(key, values):
	"""Daily Speed Sum reduce function."""
	speedsum = 0
	speedcount = 0
	for value in values:
		if int(value) > 0:
			speedsum += int(value)
			speedcount += 1
	yield "%s: %s, %s\n" % (key, speedsum, speedcount)


class DailySpeedSumPipeline(base_handler.PipelineBase):
  """A pipeline to run daily_speed_sum.

  Args:
    blobkey: blobkey to process as string. Should be a zip archive with
      text files inside.
  """


  def run(self, filekey, blobkey):
    """ run the DailySpeedSum MapReduce job
	      
    Setup the MapReduce pipeline and yield StoreOutput function
	"""
    output = yield mapreduce_pipeline.MapreducePipeline(
        "daily_speed_sum",
        "map_reduce.daily_speed_sum_map",
        "map_reduce.daily_speed_sum_reduce",
        "mapreduce.input_readers.BlobstoreZipInputReader",
        "mapreduce.output_writers.BlobstoreOutputWriter",
		mapper_params={
            "blob_key": blobkey,
        },
        reducer_params={
            "mime_type": "text/plain",
        },
        shards=16)
    yield StoreOutput("DailySpeedSum", filekey, output)


class StoreOutput(base_handler.PipelineBase):
  """A pipeline to store the result of the MapReduce job in the database.

  Args:
    mr_type: the type of mapreduce job run (e.g., DailySpeedSum)
    encoded_key: the DB key corresponding to the metadata of this job
    output: the blobstore location where the output of the job is stored
  """

  def run(self, mr_type, encoded_key, output):
    logging.info("output is %s" % str(output))
    logging.info("key is %s" % encoded_key)
    key = ndb.Key(FileMetadata, encoded_key)
    m = key.get()

    if mr_type == "DailySpeedSum":
	  blob_key = blobstore.BlobKey(output[0])
	  if blob_key:
	    m.daily_speed_sum = blob_key

    m.put()



""" Pre-defined MapReduce job  "split_file" that will split lines using regular expressions (specified in mapreduce.yaml)
  
  Args:
    entity: entity to process as string. Should be a zip archive with
      text files inside.
"""
class DoneHandler(webapp2.RequestHandler):
  """Handler for completion of split_file operation."""
  def post(self):
    logging.info("Import done %s" % self.request.arguments())
    logging.info("Done")

def split_file(entity):
	""" Method defined for "Split lines using regular expression" MR job specified in mapreduce.yaml

	Note: this function will be problematic with large datasets due to counter map size limitation of 1MB

	Args:
	entity: entity to process as string. Should be a zip archive with
	  text files inside.
	"""
	ctx = context.get()
	params = ctx.mapreduce_spec.mapper.params
	blob_key = params['blob_key']
	split_re = params['split_re']

	logging.info("Got key:%s expression:%s", blob_key, split_re)
	blob_reader = blobstore.BlobReader(blob_key, buffer_size=1048576)
	logging.info("Got filename:%s", blob_reader.blob_info.filename)
	fw_ld = re.search('freeway_loopdata.*', blob_reader.blob_info.filename)
	if fw_ld:
		if blob_reader.blob_info.content_type == "application/zip":
			logging.info("Got content type:%s", blob_reader.blob_info.content_type)
			zip_file = zipfile.ZipFile(blob_reader)
			file = zip_file.open(zip_file.namelist()[0])
		elif blob_reader.blob_info.content_type == "text/plain":
			logging.info("Got content type:%s", blob_reader.blob_info.content_type)
			file = blob_reader
		else:
			logging.info("Unrecognized content type:%s", blob_reader.blob_info.content_type)

		if file:
			csv_reader = csv.DictReader(file)
			csv_headers = csv_reader.fieldnames
			if 'speed' in csv_headers:
				for line in csv_reader:
					date = re.search('.*(%s).*' % split_re, line['starttime'])
					if date:
						logging.info("%s", line)
			else:
				logging.error("No field named 'speed' found in CSV headers:%s", csv_headers)

""" Pre-defined MapReduce job  "import_loopdata" that will process a freeway_loopdata.csv file)
  
  Args:
    entity: entity to process as string. Should be a zip archive with
      text files inside.
"""
class ImportDoneHandler(webapp2.RequestHandler):
  """Handler for completion of split_file operation."""
  def post(self):
    job_id = self.request.headers['Mapreduce-Id']
    state = model.MapreduceState.get_by_job_id(job_id)
    logging.info("Import for job %s done" % job_id)
    counters = state.counters_map.counters
    # Remove counters not needed for stats
    if 'mapper-calls' in counters.keys():
		del counters['mapper-calls']
    if 'mapper-walltime-ms' in counters.keys():
		del counters['mapper-walltime-ms']
    for counter in counters.keys():
	    logging.info("Counter %s:%s", counter, counters[counter])


def import_loopdata(entity):
	""" Method defined for "Import freeway loopdata" MR job specified in mapreduce.yaml
		
		Args:
		entity: entity to process as string. Should be a zip archive with
		text files inside.
		"""
	ctx = context.get()
	params = ctx.mapreduce_spec.mapper.params
	blob_key = params['blob_key']
	
	logging.info("Got key:%s", blob_key)
	blob_reader = blobstore.BlobReader(blob_key, buffer_size=1048576)
	logging.info("Got filename:%s", blob_reader.blob_info.filename)
	fw_ld = re.search('freeway_loopdata.*', blob_reader.blob_info.filename)
	if fw_ld:
		if blob_reader.blob_info.content_type == "application/zip":
			logging.info("Got content type:%s", blob_reader.blob_info.content_type)
			zip_file = zipfile.ZipFile(blob_reader)
			file = zip_file.open(zip_file.namelist()[0])
		elif blob_reader.blob_info.content_type == "text/plain":
			logging.info("Got content type:%s", blob_reader.blob_info.content_type)
			file = blob_reader
		else:
			logging.info("Unrecognized content type:%s", blob_reader.blob_info.content_type)
		
		if file:
			csv_reader = csv.DictReader(file)
			for line in csv_reader:
 				logging.info("Got line:%s", line)
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
 					yield op.db.Put(l)
		else:
				logging.error("No field named 'speed' found in CSV headers:%s", csv_headers)


def daily_speed_sum(entity):
	""" Method defined for "Perform daily speed sum" MR job specified in mapreduce.yaml
		
		Args:
		entity: entity to process as string. Should be a zip archive with
		text files inside.
		"""
	ctx = context.get()
	params = ctx.mapreduce_spec.mapper.params
	blob_key = params['blob_key']
	
	logging.info("Got key:%s", blob_key)
	blob_reader = blobstore.BlobReader(blob_key, buffer_size=1048576)
	if blob_reader:
		logging.info("Got filename:%s", blob_reader.blob_info.filename)
		fw_ld = re.search('freeway_loopdata.*', blob_reader.blob_info.filename)
		if fw_ld:
			if blob_reader.blob_info.content_type == "application/zip":
				logging.info("Got content type:%s", blob_reader.blob_info.content_type)
				zip_file = zipfile.ZipFile(blob_reader)
				file = zip_file.open(zip_file.namelist()[0])
			elif blob_reader.blob_info.content_type == "text/plain":
				logging.info("Got content type:%s", blob_reader.blob_info.content_type)
				file = blob_reader
			else:
				logging.info("Unrecognized content type:%s", blob_reader.blob_info.content_type)
			
			if file:
				csv_reader = csv.DictReader(file)
				csv_headers = csv_reader.fieldnames
				if 'speed' in csv_headers:
					for line in csv_reader:
						#logging.info("Got line:%s", line)
						date = re.search('(2011-..-..) .*', line['starttime'])
						if line['speed'] != '' and date:
							yield op.counters.Increment('%s_%s_speed_count' % (line['detectorid'], date.group()[:10]))
							yield op.counters.Increment('%s_%s_speed_sum' % (line['detectorid'], date.group()[:10]), int(line['speed']))
				else:
					logging.error("No field named 'speed' found in CSV headers:%s", csv_headers)
	else:
		logging.error("No blob was found for key %s", blob_key)

app = webapp2.WSGIApplication(
    [
        ('/done', ImportDoneHandler),
		('/map_reduce', IndexHandler),
    ],
    debug=True)