#/usr/bin/python

import random
import json
import math

numJobs = 10000

numMapper = 4
numReducer = 1

rackSize = 20

numPhysComp = 320

durationMapTaskMs = 1000
fileSizeBytes = 16 * int(1e6 *8)

for i in range(0, numJobs):
	
	job = dict()
	job["am.type"]			= "mapreduce";
	job["job.start.ms"]		= "0";
	job["job.end.ms"]		= "10000";
	job["job.queue.name"]	= "sls_queue_1";
	job["job.id"]			= "job_%i" % i;
	job["job.user"]			= "default";
	job["job.tasks"]		= list();

	for j in range(0, numMapper):
		task = dict();
		
		#where is the input data?
		inputLocation = int(random.random() * numPhysComp)
		if inputLocation <= 0:
			inputLocation = 1;
		if inputLocation > numPhysComp:
			inputLocation = numPhysComp;
	
		rackID = int( math.ceil(inputLocation / rackSize) )
	
		task["container.host"]				= "/rack-%i/node%i" % (rackID, inputLocation)  #location der daten (so tun wir momentan)
		task["container.start.ms"]			= "0"
		task["container.end.ms"]			= str(durationMapTaskMs)
		task["container.priority"]			= "20"
		task["container.type"]				= "map"
		task["container.inputBytes"]		= str(fileSizeBytes)
		task["container.outputBytes"]		= str(fileSizeBytes)
		task["container.splitLocations"]	= list()
		task["container.splitLocations"].append(task["container.host"])


		job["job.tasks"].append(task)


	for j in range(0, numReducer):
		task = dict();
		
		#where is the input data?
		inputLocation = int(random.random() * numPhysComp)
		if inputLocation <= 0:
			inputLocation = 1;
		if inputLocation > numPhysComp:
			inputLocation = numPhysComp;

		rackID = int( math.ceil(inputLocation / rackSize) )
		
		
		task["container.host"]				= "/rack-%i/node%i" % (rackID, inputLocation)  #location der daten (so tun wir momentan)
		task["container.start.ms"]			= "0"
		task["container.end.ms"]			= str(durationMapTaskMs)
		task["container.priority"]			= "20"
		task["container.type"]				= "reduce"
		task["container.inputBytes"]		= str(numMapper * fileSizeBytes)
		task["container.outputBytes"]		= str(fileSizeBytes)


		job["job.tasks"].append(task)



	#write in json file
	print json.dumps(job, indent=1)









