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
