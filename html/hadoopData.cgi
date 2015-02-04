#! /usr/bin/python
import random
import time

print "Content-Type: text/plain\n"

print int(time.time() + random.normalvariate(0,3))% 100

