#/usr/bin/python

import random
import json
import math

rackSize = 20

numPhysComp = 320


numRacks = int(math.ceil(numPhysComp/rackSize))


for i in range(0, numRacks):
	rack = dict()
	
	rack["rack"] = "rack-%i" % i
	
	startNode = i * rackSize + 1
	endNode = startNode + rackSize
	nodes = list()
	
	for j in range(startNode, endNode):
		n = dict()
		n["node"] = "node%i" % j
		nodes.append(n)
	
	rack["nodes"] = nodes
	
	#write in json file
	print json.dumps(rack, indent=1)









