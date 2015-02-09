#! /usr/bin/python
import random
import time
import urllib2

print "Content-Type: text/plain\n"

u = urllib2.urlopen("http://kermit.cs.upb.de:8000/sls_tasksPerSec.txt")

print u.read()
