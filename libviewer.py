#!/usr/bin/env python

'''
Basic Viewer and ascii saver examples

Copyright (C) 2008 Alberto Gomez-Casado (University of Twente).

This program is released under the GNU General Public License version 2.
'''


import liboutlet as lout

class Viewer(object):
	source=[]
	data=[]
	dtype='all'
	action=[]
	

	def setdtype(self, dt):
		self.dtype=dt	

        def show(self):
		self.source.printbuf()

	def getdata(self):
		self.data=self.source.read_type(self.dtype)



class Ascii(Viewer):

	def __init__(self,outref):
		self.source=outref
		self.action=self.dump	

	def dump(self):
		self.getdata()
		destination=raw_input('Enter filename:')
		destfile=open(destination,'w+')
		destfile.write('\n'.join(self.data))
		destfile.close()
	
