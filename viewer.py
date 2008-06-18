#!/usr/bin/env python

'''
Viewer test case

Copyright (C) 2008 Alberto Gomez-Casado (University of Twente).

This program is released under the GNU General Public License version 2.
'''


import libviewer as lview

class viewerCommands:
	
    def _plug_init(self):
	self.viewerlist=[]
		

    def do_vwnew(self,args):
	self.viewerlist.append(lview.Ascii(self.outlet))
	dt=raw_input('What type of data will this viewer handle? (force/distance/all)')
	print dt
	self.viewerlist[-1].setdtype(dt)


    def do_vwaction(self,args):
	'''
	triggers default action of viewer number n (default 0)
	'''

	if len(args)==0:
		args=0
	self.viewerlist[int(args)].action()
