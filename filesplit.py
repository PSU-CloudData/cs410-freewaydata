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
  """The main page that users will interact with, which presents users with
  the ability to upload new data or run MapReduce jobs on their existing data.
  """

  def get(self):
    q = FileMetadata.query()
    results = q.fetch(10)

    items = [result for result in results]
    length = len(items)
	
    self.render_template("filesplit.html",{
						 "items": items,
						 "length": length})

  def post(self):
    filekey = self.request.get("filekey")
    blob_key = self.request.get("blobkey")

    if self.request.get("filesplit"):
      logging.info("Starting file split...")
      pipeline = FileSplitPipeline(filekey, blob_key)
      pipeline.start()
      self.redirect(pipeline.base_path + "/status?root=" + pipeline.pipeline_id)
    else:
	  logging.info("Unrecognized operation.")

def split_into_chunks(s, c):
	chunks = []
	remainder = s
	while len(remainder) >= 0:
		chunks.append(remainder[:c])
		remainder = remainder[c:]
		if len(remainder) < c:
			break
	logging.info("Returning chunks:%s" % chunks)
	return chunks

def file_split_map(data):
  """File split map function"""
  (byte_offset, line_value) = data
  
  logging.debug("Got %s", line_value)
  day = re.search('.*2011-09-30 00:05.*', line_value)
  if day:
    yield (day.group()[0], line_value)


def file_split_reduce(key, values):
  """File split reduce function."""
  for value in values:
    yield "%s\n" % value

class FileSplitPipeline(base_handler.PipelineBase):
  """A pipeline to run file split.

  Args:
    blobkey: blobkey to process as string. Should be a zip archive with
      text files inside.
  """


  def run(self, filekey, blobkey):
    output = yield mapreduce_pipeline.MapreducePipeline(
        "file_split",
        "filesplit.file_split_map",
        "filesplit.file_split_reduce",
        "mapreduce.input_readers.BlobstoreZipLineInputReader",
        "mapreduce.output_writers.BlobstoreOutputWriter",
		mapper_params={
            "blob_keys": blobkey,
        },
        reducer_params={
            "mime_type": "text/plain",
        },
        shards=16)
    yield StoreOutput("FileSplit", filekey, output)

class StoreOutput(base_handler.PipelineBase):
  """A pipeline to store the result of the MapReduce job in the database.

  Args:
    mr_type: the type of mapreduce job run (e.g., FileSplit)
    encoded_key: the DB key corresponding to the metadata of this job
    output: the blobstore location where the output of the job is stored
  """

  def run(self, mr_type, encoded_key, output):
    logging.info("output is %s" % str(output))
    logging.info("key is %s" % encoded_key)
    key = ndb.Key(FileMetadata, encoded_key)
    m = key.get()

    if mr_type == "FileSplit":
      blob_key = blobstore.BlobKey(output[0])
      if blob_key:
        m.chunks.append(blob_key)
      else:
	    logging.error("Could not get key from output")

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
  for line in blob_reader:
    logging.info("Got line:%s", line)


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
    # Remove counter not needed for stats
    if 'mapper_calls' in counters.keys():
		del counters['mapper_calls']
    for counter in counters.keys():
	  if counter != 'mapper_calls' and counter != 'mapper-walltime-ms':
	    logging.info("Counter %s:%s", counter, counters[counter])

from mapreduce import operation as op

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
			csv_headers = csv_reader.fieldnames
			if 'speed' in csv_headers:
				for line in csv_reader:
					#logging.info("Got line:%s", line)
					date = re.search('(..-..-..) .*', line['starttime'])
					if line['speed'] != '' and date:
						yield op.counters.Increment('%s_speed_sum' % date.group()[:8], int(line['speed']))
			else:
				logging.error("No field named 'speed' found in CSV headers:%s", csv_headers)

app = webapp2.WSGIApplication(
    [
        ('/done', ImportDoneHandler),
		('/filesplit', IndexHandler),
    ],
    debug=True)