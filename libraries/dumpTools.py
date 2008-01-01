#!/usr/bin/python
'''
    # DESCRIPTION:
    # load/save a data to file by dumping its structure

    Copyright (C) 2007 Fabio Erculiani

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
'''
from entropyConstants import *
import cPickle

'''
   @description: dump object to file
   @input: name of the object, object
   @output: status code
'''
def dumpobj(name, object, completePath = False):
    while 1: # trap ctrl+C
        # etpConst['dumpstoragedir']
        try:
            if completePath:
                dmpfile = name
            else:
                if not os.path.isdir(etpConst['dumpstoragedir']):
                    os.makedirs(etpConst['dumpstoragedir'])
                dmpfile = etpConst['dumpstoragedir']+"/"+name+".dmp"
            f = open(dmpfile,"wb")
            cPickle.dump(object,f)
            f.flush()
            f.close()
        except IOError, e:
            raise IOError,"can't write to file "+name
        except:
            raise
        break


'''
   @description: load object from a file
   @input: name of the object
   @output: object or, if error -1
'''
def loadobj(name, completePath = False):
    if completePath:
        dmpfile = name
    else:
        dmpfile = etpConst['dumpstoragedir']+"/"+name+".dmp"
    if os.path.isfile(dmpfile):
	try:
            f = open(dmpfile,"rb")
            x = cPickle.load(f)
            f.close()
            return x
	except cPickle.UnpicklingError:
	    os.remove(dmpfile)
	    raise SyntaxError,"cannot load object"

def removeobj(name):
    if os.path.isfile(etpConst['dumpstoragedir']+"/"+name+".dmp"):
        try:
            os.remove(etpConst['dumpstoragedir']+"/"+name+".dmp")
        except OSError:
            pass