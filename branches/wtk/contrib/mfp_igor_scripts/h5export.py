# Copyright (C) 2010 Alberto Gomez-Casado
#                    W. Trevor King <wking@drexel.edu>
#
# This file is part of Hooke.
#
# Hooke is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Hooke is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General
# Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Hooke.  If not, see
# <http://www.gnu.org/licenses/>.

import h5py
import numpy
import os
import sys

h5file=os.path.realpath(sys.argv[-1])
h5dir=os.path.dirname(h5file)

f=h5py.File(h5file)

exportdir=os.path.join(h5dir,'exported')
try:
	os.mkdir(exportdir)
except:
	print 'mkdir error, maybe the export directory already exists?'

def h5exportfunc(name):
	Deflname=name
     	if Deflname.endswith('Defl'):	   #search for _Defl dataset		
        	LVDTname=str.replace(Deflname,'Defl','LVDT')  #and correspondant LVDT dataset
		Defldata=f[Deflname][:]   #store the data in local var
	  	LVDTdata=f[LVDTname][:]
		#find useful attr (springc)
	  	try:
			notes=f[Deflname].attrs['IGORWaveNote']
	  		springmatch=notes.index("SpringConstant: ")+len("SpringConstant: ")
	  		springc=notes[springmatch:].split("\r",1)[0]  #probably extracting the leading numbers can be way more elegant than this
	  		print Deflname	
	  	except:
			print 'Something bad happened with '+Deflname+', ignoring it'
			return None
			#returning anything but None halts the visit procedure
		
		fp=open(os.path.join(exportdir,name.replace('/',''))+'.txt','w')  
		#uses the full HDF5 path (slashes out) to avoid potential overwriting		  
	  	#write attr
		fp.writelines("IGP-HDF5-Hooke\n")
		fp.writelines('SpringConstant: '+springc+'\n\n')
		fp.writelines('App x\tApp y\tRet x\tRet y\n')
		#write LVDT and Defl data
		half=Defldata.size/2
		for i in numpy.arange(0,half):
			fp.writelines(str(LVDTdata[i])+'\t'+str(Defldata[i])+'\t'+str(LVDTdata[i+half])+'\t'+str(Defldata[i+half])+'\n')	
		#close the file
		fp.close()
		return None


f.visit(h5exportfunc)
