# Copyright (C) 2010 Alberto Gomez-Casado
#                    W. Trevor King <wking@drexel.edu>
#
# This file is part of Hooke.
#
# Hooke is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# Hooke is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Hooke.  If not, see
# <http://www.gnu.org/licenses/>.

'''
FMjoin.py
Copies all .ibw files contained in a folder and its subfolders into a single folder. Useful for force maps.

Usage: 
python FMjoin.py origindir destdir
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


