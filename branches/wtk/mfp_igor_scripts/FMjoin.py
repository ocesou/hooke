#!/usr/bin/env python

'''
FMjoin.py
Copies all .ibw files contained in a folder and its subfolders into a single folder. Useful for force maps.

Usage: 
python FMjoin.py origindir destdir


Alberto Gomez-Casado (c) 2010, University of Twente (The Netherlands)
This program is released under the GNU General Public License version 2.
'''

import os
import shutil
import sys

def main(*args):
	if len(sys.argv) < 2:
		print 'You must at least specify origin and destination folders.'
		return 0
	origin=sys.argv[1]
	dest=sys.argv[2]
   
	if os.path.exists(origin):
		if os.path.exists(dest):
			if os.listdir(dest)!=[]:
	    			print 'Destination folder is not empty! Use another folder.'
	    			return 0
		else:
			print 'Destination folder does not exist, will create it'
			os.mkdir(dest)
	else:
		print 'You provided a wrong origin folder name, try again.'
	
	origin=os.path.abspath(origin)
	dest=os.path.abspath(dest)
    	
	for root, dirs, files in os.walk(origin):
		for filename in files:
			if filename.split('.')[1]!="ibw":
				continue
			filepath=os.path.join(root,filename)
			#to avoid overwriting, we collapse unique paths into filenames
			rawdest=filepath.split(os.path.commonprefix([origin, filepath]))[1]
			rawdest=rawdest.replace('/','') #for linux
			rawdest=rawdest.replace('\\','') #for windows
			destfile=os.path.join(dest,rawdest)
			print 'Copying '+rawdest
			shutil.copy(filepath,destfile)
    
        return 0
 
if __name__ == '__main__':
    sys.exit(main(*sys.argv))


