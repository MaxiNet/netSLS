#! /usr/bin/python
# -*- coding: utf-8 -*-
 
import argparse
import logging
import Pyro4
import time
import os
import subprocess
import re

import cgi

from pprint import pprint

__author__ = 'arne'

if hasattr(Pyro4.config, 'SERIALIZERS_ACCEPTED'):
    # From Pyro 4.25, pickle is not supported by default due to security.
    # However, it is required to serialise some objects used by maxinet.
    Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = 'pickle'


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--ns", help="nameserver to use", required=True, type=str, metavar="NAMESERVER")
    parser.add_argument("--nsport", help="namserver port", type=int, default=9090)
    parser.add_argument("--hmac", help="hmac key to use", type=str)
    parser.add_argument("--intensity", help="hmac key to use", type=int, default=17)
    args = parser.parse_args()
    return args


class MiniNetRemote:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def main(self,args):


        if(args.hmac):
            Pyro4.config.HMAC_KEY=args.hmac

        self.nameserver = Pyro4.locateNS(args.ns, args.nsport)
        curi = self.nameserver.lookup("config")
        config = Pyro4.Proxy(curi)

        hosts = config.getHosts()

        timeout = 10  # timeout (seconds) for worker startup

        self.cmd={}
        self.mnCreate={}

        for i in range(0, len(hosts)):
            self.logger.info("waiting for Worker " + str(i + 1) +
                             " to register on nameserver...")
            started = False
            end = time.time() + timeout
            while(not started):
                try:
                    wmncreat = self.nameserver.lookup("worker" + str(i + 1) + ".mnCreator")
                    wcmd =  self.nameserver.lookup("worker" + str(i + 1) + ".cmd")


                    started = True
                    self.mnCreate[i]= Pyro4.Proxy(wmncreat)
                    self.cmd[i]=  Pyro4.Proxy(wcmd)

                except Pyro4.errors.NamingError:
                    if(time.time() > end):
                        raise RuntimeError("Timed out waiting for worker " +
                                           str(i + 1) + ".mnCreator to " +
                                           "register.")
                    time.sleep(0.1)


        if args.intensity ==0:
            self.doCMD(["hostname", 'pkill -SIGSTOP traffGen || true'])
        else:
            self.doCMD(
                ["echo scaleFactorSize=%f > /tmp/hup.conf" % (args.intensity/5.0),
               "cat /tmp/hup.conf",
               "pkill --signal SIGCONT traffGen || true",
               "pkill --signal SIGHUP traffGen || true"
            ])


    def doCMD(self, cmdline):
        print "<table border=1>"
        for cmd in self.cmd.values():
            print "<tr><th>%s</th></tr>" % cmd.get_hostname()
            for cmdl in cmdline:
                print "<tr><td>%s</td><td> %s</td></tr>" % (cmdl, cmd.check_output(cmdl))

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


def doCGI(args):
    print "Content-Type: text/html\n"
    cgi.parse()
    form = cgi.FieldStorage()

    #for p in form:
    #   pprint((p, form.getfirst(p)))

    intensity = int(form.getfirst('intensity'))
    if 'intensity' in form:
        print "<li>Befehl bekommen die Intensit&auml;t auf %d zu stellen!</li>" % intensity
    args.intensity = intensity

    psaux = subprocess.check_output(["ps","ax"])
    m = re.search("MaxiNetServer.*:9090[^0-9]*([0-9]+)[^0-9]",psaux)
    args.hmac= m.group(1)

if __name__=="__main__":
    if 'REQUEST_METHOD' in os.environ:
        iamcgi = True
        import cgitb; cgitb.enable()
    else:
        iamcgi = False

    if not iamcgi:
        args = parse_args()
    else:
        args = AttrDict()
        doCGI(args)
        args.ns = "fgcn-of-20.cs.upb.de"
        args.nsport = 9090

    mnr = MiniNetRemote()

    mnr.main(args)
