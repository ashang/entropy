#!/usr/bin/python
'''
    # DESCRIPTION:
    # Entropy Portage Interface

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

# EXIT STATUSES: 600-699



############
# Portage initialization
#####################################################################################

'''
def initializePortageTree():
    portage.settings.unlock()
    portage.settings['PORTDIR'] = etpConst['portagetreedir']
    portage.settings['DISTDIR'] = etpConst['distfilesdir']
    portage.settings['PORTDIR_OVERLAY'] = etpConst['overlays']
    portage.settings.lock()
    portage.portdb.__init__(etpConst['portagetreedir'])
'''

# Fix for wrong cache entries - DO NOT REMOVE
import os
from entropyConstants import *
#os.environ['PORTDIR'] = etpConst['portagetreedir']
#os.environ['PORTDIR_OVERLAY'] = etpConst['overlays']
#os.environ['DISTDIR'] = etpConst['distfilesdir']
import portage
import portage_const
from portage_dep import isvalidatom, isspecific, isjustname, dep_getkey, dep_getcpv #FIXME: Use the ones from entropyTools
from portage_util import grabdict_package
from portage_const import USER_CONFIG_PATH
#from serverConstants import *
#initializePortageTree()

# colours support
from outputTools import *
# misc modules
import string
import re
import sys
import os
import commands
import entropyTools

# Logging initialization
try:
    import logTools
    portageLog = logTools.LogFile(level=etpConst['spmbackendloglevel'],filename = etpConst['spmbackendlogfile'], header = "[Portage]")
    # portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"testFunction: example. ")
except:
    pass

############
# Functions and Classes
#####################################################################################

def getThirdPartyMirrors(mirrorname):
    return portage.thirdpartymirrors[mirrorname]

def getPortageEnv(var):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getPortageEnv: called.")
    try:
	rc = portage.config(clone=portage.settings).environ()[var]
	portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getPortageEnv: variable available -> "+str(var))
	return rc
    except KeyError:
	portageLog.log(ETP_LOGPRI_WARNING,ETP_LOGLEVEL_VERBOSE,"getPortageEnv: variable not available -> "+str(var))
	return None

# Packages in system (in the Portage language -> emerge system, remember?)
def getPackagesInSystem():
    system = portage.settings.packages
    sysoutput = []
    for x in system:
	y = getInstalledAtoms(x)
	if (y != None):
	    for z in y:
	        sysoutput.append(z)
    sysoutput.append("sys-kernel/linux-sabayon") # our kernel
    sysoutput.append("dev-db/sqlite") # our interface
    sysoutput.append("dev-python/pysqlite") # our python interface to our interface (lol)
    sysoutput.append("virtual/cron") # our cron service
    return sysoutput

def getConfigProtectAndMask():
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getConfigProtectAndMask: called.")
    config_protect = portage.settings['CONFIG_PROTECT']
    config_protect = config_protect.split()
    config_protect_mask = portage.settings['CONFIG_PROTECT_MASK']
    config_protect_mask = config_protect_mask.split()
    # explode
    protect = []
    for x in config_protect:
	if x.startswith("$"): #FIXME: small hack
	    x = commands.getoutput("echo "+x).split("\n")[0]
	protect.append(x)
    mask = []
    for x in config_protect_mask:
	if x.startswith("$"): #FIXME: small hack
	    x = commands.getoutput("echo "+x).split("\n")[0]
	mask.append(x)
    return string.join(protect," "),string.join(mask," ")

# resolve atoms automagically (best, not current!)
# sys-libs/application --> sys-libs/application-1.2.3-r1
def getBestAtom(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getBestAtom: called -> "+str(atom))
    try:
        rc = portage.portdb.xmatch("bestmatch-visible",str(atom))
	portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getBestAtom: result -> "+str(rc))
        return rc
    except ValueError:
	portageLog.log(ETP_LOGPRI_WARNING,ETP_LOGLEVEL_VERBOSE,"getBestAtom: conflict found. ")
	return "!!conflicts"

# same as above but includes masked ebuilds
def getBestMaskedAtom(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getBestAtom: called. ")
    atoms = portage.portdb.xmatch("match-all",str(atom))
    # find the best
    from portage_versions import best
    rc = best(atoms)
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getBestAtom: result -> "+str(rc))
    return rc

# I need a valid complete atom...
def calculateFullAtomsDependencies(atoms, deep = False, extraopts = ""):

    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"calculateFullAtomsDependencies: called -> "+str(atoms)+" | extra options: "+extraopts)

    # in order... thanks emerge :-)
    deepOpt = ""
    if (deep):
	deepOpt = "-Du"
    deplist = []
    blocklist = []
    
    # FIXME: rewrite this
    cmd = cdbRunEmerge+" --pretend --color=n --quiet "+deepOpt+" "+extraopts+" "+atoms
    result = commands.getoutput(cmd).split("\n")
    for line in result:
	if line.startswith("[ebuild"):
	    line = line.split("] ")[1].split(" [")[0].split()[0].strip()
	    deplist.append(line)
	if line.startswith("[blocks"):
	    line = line.split("] ")[1].split()[0].strip()
	    blocklist.append(line)

    # filter garbage
    _deplist = []
    for i in deplist:
	if (i != "") and (i != " "):
	    _deplist.append(i)
    deplist = _deplist
    _blocklist = []
    for i in blocklist:
	if (i != "") and (i != " "):
	    _blocklist.append(i)
    blocklist = _blocklist

    if deplist != []:
	portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"calculateFullAtomsDependencies: deplist -> "+str(len(deplist))+" | blocklist -> "+str(len(blocklist)))
        return deplist, blocklist
    else:
	portageLog.log(ETP_LOGPRI_ERROR,ETP_LOGLEVEL_VERBOSE,"calculateFullAtomsDependencies: deplist empty. Giving up.")
	rc = entropyTools.spawnCommand(cmd)
	sys.exit(100)


def calculateAtomUSEFlags(atom, format = True):
    
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"calculateAtomUSEFlags: called -> "+str(atom))

    
    uses = getUSEFlags()
    uses = uses.split()
    iuses = getPackageIUSE(atom)
    iuses = iuses.split()
    olduses = getInstalledPackageVar(atom,'USE')
    olduses = olduses.split()
    useforce = getUSEForce()
    usemask = getUSEMask()
    
    # package.use FIXME: this should also handle package.use.mask and use.mask
    etc_use = get_user_config('package.use',ebuild = atom)
    for x in etc_use:
	if x not in uses:
	    uses.append(x)
    
    iuses.sort()
    
    useparm = []
    for iuse in iuses:
	if iuse in uses:
	    if iuse in olduses:
		useparm.append(iuse)
	    else:
		useparm.append(iuse+"*")
	else:
	    if iuse in olduses:
		useparm.append("-"+iuse+"*")
	    elif iuse in useforce:
		useparm.append("("+iuse+")")
	    else:
	        if iuse in usemask:
		    useparm.append("(-"+iuse+")")
	        else:
		    useparm.append("-"+iuse)
    
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"calculateAtomUSEFlags: USE flags -> "+str(useparm))
    
    # pack properly
    enabled = []
    new = []
    disabled = []
    disabled_new = []
    impossible = []

    for x in useparm:
	if x.startswith("("):
	    impossible.append(x)
	elif x.startswith("-") and not x.endswith("*"):
	    disabled.append(x)
	elif x.startswith("-") and x.endswith("*"):
            disabled_new.append(x)
	elif x.endswith("*"):
	    new.append(x)
	else:
	    enabled.append(x)

    useparm = []
    useparm = enabled
    if (new):
        useparm += new
    if (disabled_new):
        useparm += disabled_new
    if (disabled):
        useparm += disabled
    if (impossible):
        useparm += impossible
    

    expanded = {}
    if (format):
	use_expand = portage.settings['USE_EXPAND'] # FIXME add support for USE_EXPAND_MASK ?
	use_expand_low = use_expand.lower()
	use_expand_low = use_expand_low.split()
	for expand in use_expand_low:
	    myexp = []
	    myexp = [x for x in useparm if x.startswith(expand+"_") or x.startswith("-"+expand+"_") or x.startswith("(-"+expand+"_") or x.startswith("("+expand+"_")]
	    if (myexp):
		useparm = [x for x in useparm if not x.startswith(expand+"_") and not x.startswith("-"+expand+"_") and not x.startswith("(-"+expand+"_") and not x.startswith("("+expand+"_")]
		expand_en = [x[len(expand)+1:] for x in myexp if not x.startswith("-") and not x.startswith("(")]
		expand_dis = ["-"+x[len(expand)+2:] for x in myexp if x.startswith("-")]
		expand_impossible_en = ["("+x[len(expand)+2:] for x in myexp if x.startswith("(") and not x.startswith("(-")]
		expand_impossible_dis = ["(-"+x[len(expand)+3:] for x in myexp if x.startswith("(-")]
		myexp = expand_en
		myexp += expand_en
		myexp += expand_impossible_en
		myexp += expand_impossible_dis
		myexp = list(set(myexp))
		myexp.sort()
		expanded[expand.upper()] = string.join(myexp," ")

    useparm = string.join(useparm," ")
    useparm = colorizeUseflags(useparm)
    if (format):
	if (expanded):
	    for key in expanded:
		if expanded[key]:
		    content = colorizeUseflags(expanded[key])
		    content = bold(" "+key+"=( ")+content+bold(" )")
		    useparm += content
    
    return useparm


def colorizeUseflags(usestring):
    out = []
    for use in usestring.split():
	# -cups
	if use.startswith("-") and (not use.endswith("*")):
	    use = darkblue(use)
	# -cups*
	elif use.startswith("-") and (use.endswith("*")):
	    use = yellow(use)
	# use flag not available
	elif use.startswith("("):
	    use = blue(use)
	# cups*
	elif use.endswith("*"):
	    use = green(use)
	else:
	    use = darkred(use)
	out.append(use)
    return string.join(out," ")


# should be only used when a pkgcat/pkgname <-- is not specified (example: db, amarok, AND NOT media-sound/amarok)
def getAtomCategory(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getAtomCategory: called. ")
    try:
        rc = portage.portdb.xmatch("match-all",str(atom))[0].split("/")[0]
        return rc
    except:
	portageLog.log(ETP_LOGPRI_ERROR,ETP_LOGLEVEL_VERBOSE,"getAtomCategory: error, can't extract category !")
	return None

# This function compare the version number of two atoms
# This function needs a complete atom, pkgcat (not mandatory) - pkgname - pkgver
# if atom1 < atom2 --> returns a NEGATIVE number
# if atom1 > atom2 --> returns a POSITIVE number
# if atom1 == atom2 --> returns 0
def compareAtoms(atom1,atom2):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"compareAtoms: called -> "+atom1+" && "+atom2)
    # filter pkgver
    x, atom1 = extractPkgNameVer(atom1)
    x, atom2 = extractPkgNameVer(atom2)
    from portage_versions import vercmp
    return vercmp(atom1,atom2)

# please always force =pkgcat/pkgname-ver if possible
def getInstalledAtom(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getInstalledAtom: called -> "+str(atom))
    rc = portage.db['/']['vartree'].dep_match(str(atom))
    if (rc != []):
	if (len(rc) == 1):
	    return rc[0]
	else:
            return rc[len(rc)-1]
    else:
        return None

def getPackageSlot(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getPackageSlot: called. ")
    if atom.startswith("="):
	atom = atom[1:]
    rc = portage.db['/']['vartree'].getslot(atom)
    if rc != "":
	portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getPackageSlot: slot found -> "+str(atom)+" -> "+str(rc))
	return rc
    else:
	portageLog.log(ETP_LOGPRI_WARNING,ETP_LOGLEVEL_VERBOSE,"getPackageSlot: slot not found -> "+str(atom))
	return None

# you must provide a complete atom
def collectBinaryFilesForInstalledPackage(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"collectBinaryFilesForInstalledPackage: called. ")
    if atom.startswith("="):
	atom = atom[1:]
    pkgcat = atom.split("/")[0]
    pkgnamever = atom.split("/")[1]
    dbentrypath = "/var/db/pkg/"+pkgcat+"/"+pkgnamever+"/CONTENTS"
    binarylibs = []
    if os.path.isfile(dbentrypath):
	f = open(dbentrypath,"r")
	contents = f.readlines()
	f.close()
	for i in contents:
	    file = i.split()[1]
	    if i.startswith("obj") and (file.find("lib") != -1) and (file.find(".so") != -1) and (not file.endswith(".la")):
		# FIXME: rough way
		binarylibs.append(i.split()[1].split("/")[len(i.split()[1].split("/"))-1])
        return binarylibs
    else:
	return binarylibs

def getEbuildDbPath(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getEbuildDbPath: called -> "+atom)
    return portage.db['/']['vartree'].getebuildpath(atom)

def getEbuildTreePath(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getEbuildTreePath: called -> "+atom)
    if atom.startswith("="):
	atom = atom[1:]
    rc = portage.portdb.findname(atom)
    if rc != "":
	return rc
    else:
	return None

def getPackageDownloadSize(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getPackageDownloadSize: called -> "+atom)
    if atom.startswith("="):
	atom = atom[1:]

    ebuild = getEbuildTreePath(atom)
    if (ebuild is not None):
	import portage_manifest
	dirname = os.path.dirname(ebuild)
	manifest = portage_manifest.Manifest(dirname, portage.settings["DISTDIR"])
	fetchlist = portage.portdb.getfetchlist(atom, portage.settings, all=True)[1]
	summary = [0,0]
	try:
	    summary[0] = manifest.getDistfilesSize(fetchlist)
	    counter = str(summary[0]/1024)
	    filler=len(counter)
	    while (filler > 3):
		filler-=3
		counter=counter[:filler]+","+counter[filler:]
	    summary[0]=counter+" kB"
	except KeyError, e:
	    return "N/A"
	return summary[0]
    else:
	return "N/A"

def getInstalledAtoms(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getInstalledAtoms: called -> "+atom)
    rc = portage.db['/']['vartree'].dep_match(str(atom))
    if (rc != []):
        return rc
    else:
        return None



# YOU MUST PROVIDE A COMPLETE ATOM with a pkgcat !
def unmerge(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"umerge: called -> "+atom)
    if isjustname(atom) or (not isvalidatom(atom)) or (atom.find("/") == -1):
	return 1
    else:
	pkgcat = atom.split("/")[0]
	pkgnamever = atom.split("/")[1]
	portage.settings.unlock()
	rc = portage.unmerge(pkgcat, pkgnamever, ETP_ROOT_DIR, portage.settings, 1)
	portage.settings.lock()
	return rc

# TO THIS FUNCTION:
# must be provided a valid and complete atom
def extractPkgNameVer(atom):
    import enzymeTools
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"extractPkgNameVer: called -> "+atom)
    package = dep_getcpv(atom)
    package = atom.split("/")[len(atom.split("/"))-1]
    package = package.split("-")
    pkgname = ""
    pkglen = len(package)
    if package[pkglen-1].startswith("r"):
        pkgver = package[pkglen-2]+"-"+package[pkglen-1]
	pkglen -= 2
    else:
	pkgver = package[len(package)-1]
	pkglen -= 1
    for i in range(pkglen):
	if i == pkglen-1:
	    pkgname += package[i]
	else:
	    pkgname += package[i]+"-"
    return pkgname,pkgver

def emerge(atom, options, outfile = None, redirect = "&>", simulate = False):
    import enzymeTools
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"emerge: called -> "+atom+" | options: "+str(options)+" | redirect: "+str(redirect)+" | outfile: "+str(outfile)+" | simulate: "+str(simulate))
    if (simulate):
	return 0,"" # simulation enabled
    if (outfile is None) and (redirect == "&>"):
	outfile = etpConst['packagestmpdir']+"/.emerge-"+str(getRandomNumber())
    elif (redirect is None):
	outfile = ""
	redirect = ""
    if os.path.isfile(outfile):
	try:
	    os.remove(outfile)
	except:
	    entropyTools.spawnCommand("rm -rf "+outfile)    
    # elog configuration
    elogopts = dbPORTAGE_ELOG_OPTS+" "
    # clean elog shit
    elogfile = atom.split("=")[len(atom.split("="))-1]
    elogfile = elogfile.split(">")[len(atom.split(">"))-1]
    elogfile = elogfile.split("<")[len(atom.split("<"))-1]
    elogfile = elogfile.split("/")[len(atom.split("/"))-1]
    elogfile = etpConst['logdir']+"/elog/*"+elogfile+"*"
    entropyTools.spawnCommand("rm -rf "+elogfile)
    
    distccopts = ""
    if (enzymeTools.getDistCCStatus()):
	# FIXME: add MAKEOPTS too
	distccopts += 'FEATURES="distcc" '
	distccjobs = str(len(enzymeTools.getDistCCHosts())+3)
	distccopts += 'MAKEOPTS="-j'+distccjobs+'" '
	#distccopts += 'MAKEOPTS="-j4" '
    rc = entropyTools.spawnCommand(distccopts+elogopts+cdbRunEmerge+" "+options+" "+atom, redirect+outfile)
    return rc, outfile

def parseElogFile(atom):

    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"parseElogFile: called. ")

    if atom.startswith("="):
	atom = atom[1:]
    if atom.startswith(">"):
	atom = atom[1:]
    if atom.startswith("<"):
	atom = atom[1:]
    if (atom.find("/") != -1):
	pkgcat = atom.split("/")[0]
	pkgnamever = atom.split("/")[1]+"*.log"
    else:
	pkgcat = "*"
	pkgnamever = atom+"*.log"
    elogfile = pkgcat+":"+pkgnamever
    reallogfile = commands.getoutput("find "+etpConst['logdir']+"/elog/ -name '"+elogfile+"'").split("\n")[0].strip()
    if os.path.isfile(reallogfile):
	# FIXME: improve this part
	logline = False
	logoutput = []
	f = open(reallogfile,"r")
	reallog = f.readlines()
	f.close()
	for line in reallog:
	    if line.startswith("INFO: postinst") or line.startswith("LOG: postinst"):
		logline = True
		continue
		# disable all the others
	    elif line.startswith("INFO:") or line.startswith("LOG:"):
		logline = False
		continue
	    if (logline) and (line.strip() != ""):
		# trap !
		logoutput.append(line.strip())
	return logoutput
    else:
	return []

def compareLibraryLists(pkgBinaryFiles,newPkgBinaryFiles):
    
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"compareLibraryLists: called. ")
    
    brokenBinariesList = []
    # check if there has been a API breakage
    if pkgBinaryFiles != newPkgBinaryFiles:
	_pkgBinaryFiles = []
	_newPkgBinaryFiles = []
	# extract only similar packages
	for pkg in pkgBinaryFiles:
	    if (pkg.find(".so") == -1):
		continue
	    _pkg = pkg.split(".so")[0]
	    for newpkg in newPkgBinaryFiles:
		if (pkg.find(".so") == -1):
		    continue
		_newpkg = newpkg.split(".so")[0]
		if (_newpkg == _pkg):
		    _pkgBinaryFiles.append(pkg)
		    _newPkgBinaryFiles.append(newpkg)
	pkgBinaryFiles = _pkgBinaryFiles
	newPkgBinaryFiles = _newPkgBinaryFiles
	
	#print "DEBUG:"
	#print pkgBinaryFiles
	#print newPkgBinaryFiles
	
	# check for version bumps
	for pkg in pkgBinaryFiles:
	    _pkgver = pkg.split(".so")[len(pkg.split(".so"))-1]
	    _pkg = pkg.split(".so")[0]
	    for newpkg in newPkgBinaryFiles:
		_newpkgver = newpkg.split(".so")[len(newpkg.split(".so"))-1]
		_newpkg = newpkg.split(".so")[0]
		if (_newpkg == _pkg):
		    # check version
		    if (_pkgver != _newpkgver):
			brokenBinariesList.append([ pkg, newpkg ])
    return brokenBinariesList


# create a .tbz2 file in the specified path
# old way, buggy with symlinks
def quickpkg(atom,dirpath):

    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"quickpkg_old: called -> "+atom+" | dirpath: "+dirpath)

    # getting package info
    pkgname = atom.split("/")[1]
    pkgcat = atom.split("/")[0]
    pkgfile = pkgname+".tbz2"
    dirpath += "/"+pkgname+".tbz2"
    tmpdirpath = etpConst['packagestmpdir']+"/"+pkgname+".tbz2"+"-tmpdir"
    if os.path.isdir(tmpdirpath): entropyTools.spawnCommand("rm -rf "+tmpdirpath)
    os.makedirs(tmpdirpath)
    dbdir = "/var/db/pkg/"+pkgcat+"/"+pkgname+"/"

    import tarfile
    import stat
    from portage import dblink
    trees = portage.db["/"]
    vartree = trees["vartree"]
    dblnk = dblink(pkgcat, pkgname, "/", vartree.settings, treetype="vartree", vartree=vartree)
    dblnk.lockdb()
    tar = tarfile.open(dirpath,"w:bz2")

    contents = dblnk.getcontents()
    id_strings = {}
    paths = contents.keys()
    paths.sort()
    
    for path in paths:
	try:
	    exist = os.lstat(path)
	except OSError:
	    continue # skip file
	ftype = contents[path][0]
	lpath = path
	arcname = path[1:]
	if 'dir' == ftype and \
	    not stat.S_ISDIR(exist.st_mode) and \
	    os.path.isdir(lpath):
	    lpath = os.path.realpath(lpath)
	tarinfo = tar.gettarinfo(lpath, arcname)
	tarinfo.uname = id_strings.setdefault(tarinfo.uid, str(tarinfo.uid))
	tarinfo.gname = id_strings.setdefault(tarinfo.gid, str(tarinfo.gid))
	
	if stat.S_ISREG(exist.st_mode):
	    tarinfo.type = tarfile.REGTYPE
	    f = open(path)
	    try:
		tar.addfile(tarinfo, f)
	    finally:
		f.close()
	else:
	    tar.addfile(tarinfo)

    tar.close()
    
    # appending xpak informations
    import xpak
    tbz2 = xpak.tbz2(dirpath)
    tbz2.recompose(dbdir)
    
    dblnk.unlockdb()
    
    # Remove tmp file
    entropyTools.spawnCommand("rm -rf "+tmpdirpath)
    
    if os.path.isfile(dirpath):
	return dirpath
    else:
	return False

# create a .tbz2 file in the specified path
def quickpkg_test(atom,dirpath):

    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"quickpkg: called -> "+atom+" | dirpath: "+dirpath)

    import shutil
    # getting package info
    pkgname = atom.split("/")[1]
    pkgcat = atom.split("/")[0]
    pkgfile = pkgname+".tbz2"
    dirpath += "/"+pkgname+".tbz2"
    dirpath = os.path.realpath(dirpath)
    tmpdirpath = etpConst['packagestmpdir']+"/"+pkgname+".tbz2"+"-tmpdir"
    if os.path.isdir(tmpdirpath): shutil.rmtree(tmpdirpath)
    os.makedirs(tmpdirpath)
    dbdir = "/var/db/pkg/"+pkgcat+"/"+pkgname+"/"
    
    # open file and read contents
    f = open(dbdir+dbCONTENTS,"r")
    contents = f.readlines()
    contents = [x.split()[1] for x in contents]
    f.close()
    
    contents.sort()
    # copy files to a tmpdir
    for x in contents:
	if os.path.lexists(x):
	    if os.path.isdir(x) and not os.path.islink(x):
		# true dir
		x = os.path.realpath(x)
		os.makedirs(tmpdirpath+x)
		user = os.stat(x)[4]
		group = os.stat(x)[5]
		os.chown(tmpdirpath+x,user,group)
		shutil.copystat(x,tmpdirpath+x)
	    else:
		dirname = os.path.realpath(os.path.dirname(x))
		if not os.path.isdir(tmpdirpath+'/'+dirname): # in case that realpath is not yet created
		    os.makedirs(tmpdirpath+'/'+dirname)
		    if os.path.isdir(dirname):
			user = os.stat(dirname)[4]
			group = os.stat(dirname)[5]
			shutil.copystat(dirname,tmpdirpath+dirname)
		    else:
			user = 0
			group = 0
		    os.chown(tmpdirpath+dirname,user,group)
		    
		x = dirname+"/"+os.path.basename(x)
	        os.system('cp -ax '+x+' '+tmpdirpath+'/'+x)
    
    # create tar
    os.system("cd "+tmpdirpath+"; tar cjf "+dirpath+" .")

    # appending xpak informations
    import xpak
    tbz2 = xpak.tbz2(dirpath)
    tbz2.recompose(dbdir)
    
    # Remove tmp file
    entropyTools.spawnCommand("rm -rf "+tmpdirpath)

    if os.path.isfile(dirpath):
	return dirpath
    else:
	return False

# NOTE: atom must be a COMPLETE atom, with version!
def isTbz2PackageAvailable(atom, verbose = False, stable = False, unstable = True):

    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"isTbz2PackageAvailable: called -> "+atom)

    # check if the package have been already merged
    atomName = atom.split("/")[len(atom.split("/"))-1]
    tbz2Available = False
    
    paths = []
    if (unstable):
	paths.append(etpConst['packagessuploaddir']+"/"+atomName+"-unstable.tbz2")
	paths.append(etpConst['packagesstoredir']+"/"+atomName+"-unstable.tbz2")
	paths.append(etpConst['packagesbindir']+"/"+atomName+"-unstable.tbz2")
    if (stable):
	paths.append(etpConst['packagessuploaddir']+"/"+atomName+"-stable.tbz2")
	paths.append(etpConst['packagesstoredir']+"/"+atomName+"-stable.tbz2")
	paths.append(etpConst['packagesbindir']+"/"+atomName+"-stable.tbz2")

    for path in paths:
	if (verbose): print_info("testing in directory: "+path)
	if os.path.isfile(path):
	    tbz2Available = path
	    if (verbose): print_info("found here: "+str(path))
	    break

    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"isTbz2PackageAvailable: result -> "+str(tbz2Available))
    return tbz2Available

def checkAtom(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"checkAtom: called -> "+str(atom))
    bestAtom = getBestAtom(atom)
    if bestAtom == "!!conflicts":
	bestAtom = ""
    if (isvalidatom(atom) == 1) or ( bestAtom != ""):
        return True
    return False


def getPackageDependencyList(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getPackageDependencyList: called -> "+str(atom))
    pkgSplittedDeps = []
    tmp = portage.portdb.aux_get(atom, ["DEPEND"])[0].split()
    for i in tmp:
	pkgSplittedDeps.append(i)
    tmp = portage.portdb.aux_get(atom, ["RDEPEND"])[0].split()
    for i in tmp:
	pkgSplittedDeps.append(i)
    tmp = portage.portdb.aux_get(atom, ["PDEPEND"])[0].split()
    for i in tmp:
	pkgSplittedDeps.append(i)
    return pkgSplittedDeps

def getUSEFlags():
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getUSEFlags: called.")
    return portage.settings['USE']

def getUSEForce():
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getUSEForce: called.")
    return portage.settings.useforce

def getUSEMask():
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getUSEMask: called.")
    return portage.settings.usemask

def getMAKEOPTS():
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getMAKEOPTS: called.")
    return portage.settings['MAKEOPTS']

def getCFLAGS():
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getCFLAGS: called.")
    return portage.settings['CFLAGS']

def getLDFLAGS():
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getLDFLAGS: called.")
    return portage.settings['LDFLAGS']

# you must provide a complete atom
def getPackageIUSE(atom):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getPackageIUSE: called.")
    return getPackageVar(atom,"IUSE")

def getInstalledPackageVar(atom, var):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getInstalledPackageVar: called.")
    try:
        if atom.startswith("="):
	    return portage.db['/']['vartree'].dbapi.aux_get(atom[1:], [var])[0]
        else:
	    return portage.db['/']['vartree'].dbapi.aux_get(atom, [var])[0]
    except:
	return ''

def getPackageVar(atom,var):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getPackageVar: called -> "+atom+" | var: "+var)
    if atom.startswith("="):
	atom = atom[1:]
    # can't check - return error
    if (atom.find("/") == -1):
	return 1
    return portage.portdb.aux_get(atom,[var])[0]

def synthetizeRoughDependencies(roughDependencies, useflags = None):
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"synthetizeRoughDependencies: called. ")
    if useflags is None:
        useflags = getUSEFlags()
    # returns dependencies, conflicts

    useMatch = False
    openParenthesis = 0
    openParenthesisFromOr = 0
    openOr = False
    useFlagQuestion = False
    dependencies = ""
    conflicts = ""
    useflags = useflags.split()
    
    length = len(roughDependencies)
    global atomcount
    atomcount = -1

    while atomcount < length:
	
	atomcount += 1
	try:
	    atom = roughDependencies[atomcount]
	except:
	    break
	
        if atom.startswith("("):
	    if (openOr):
		openParenthesisFromOr += 1
	    openParenthesis += 1
	    curparenthesis = openParenthesis # 2
	    if (useFlagQuestion == True) and (useMatch == False):
		skip = True
		while (skip == True):
		    atomcount += 1
		    atom = roughDependencies[atomcount]
		    if atom.startswith("("):
			curparenthesis += 1
		    elif atom.startswith(")"):
		        if (curparenthesis == openParenthesis):
			    skip = False
			curparenthesis -= 1
		useFlagQuestion = False

	elif atom.endswith("?"):
	    
	    #if (useFlagQuestion) and (not useMatch): # if we're already in a question and the question is not accepted, skip the cycle
	    #    continue
	    # we need to see if that useflag is enabled
	    useFlag = atom.split("?")[0]
	    useFlagQuestion = True # V
	    #openParenthesisFromLastUseFlagQuestion = 0
	    if useFlag.startswith("!"):
		checkFlag = useFlag[1:]
		try:
		    useflags.index(checkFlag)
		    useMatch = False
		except:
		    useMatch = True
	    else:
		try:
		    useflags.index(useFlag)
		    useMatch = True # V
		except:
		    useMatch = False
	
        elif atom.startswith(")"):
	
	    openParenthesis -= 1
	    if (openParenthesis == 0):
		useFlagQuestion = False
		useMatch = False
	    
	    if (openOr):
		# remove last "_or_" from dependencies
		if (openParenthesisFromOr == 1):
		    openOr = False
		    if dependencies.endswith(dbOR):
		        dependencies = dependencies[:len(dependencies)-len(dbOR)]
		        dependencies += " "
		elif (openParenthesisFromOr == 2):
		    if dependencies.endswith("|and|"):
		        dependencies = dependencies[:len(dependencies)-len("|and|")]
		        dependencies += dbOR
		openParenthesisFromOr -= 1

        elif atom.startswith("||"):
	    openOr = True # V
	
	elif (atom.find("/") != -1) and (not atom.startswith("!")) and (not atom.endswith("?")):
	    # it's a package name <pkgcat>/<pkgname>-???
	    if ((useFlagQuestion == True) and (useMatch == True)) or ((useFlagQuestion == False) and (useMatch == False)):
	        # check if there's an OR
		if (openOr):
		    dependencies += atom
		    # check if the or is fucked up
		    if openParenthesisFromOr > 1:
			dependencies += "|and|" # !!
		    else:
		        dependencies += dbOR
                else:
		    dependencies += atom
		    dependencies += " "

        elif atom.startswith("!") and (not atom.endswith("?")):
	    if ((useFlagQuestion) and (useMatch)) or ((not useFlagQuestion) and (not useMatch)):
		conflicts += atom
		if (openOr):
		    conflicts += dbOR
                else:
		    conflicts += " "
    

    # format properly
    tmpConflicts = list(set(conflicts.split()))
    conflicts = ''
    tmpData = []
    for i in tmpConflicts:
	i = i[1:] # remove "!"
	tmpData.append(i)
    conflicts = string.join(tmpData," ")

    tmpData = []
    tmpDeps = list(set(dependencies.split()))
    dependencies = ''
    for i in tmpDeps:
	tmpData.append(i)

    # now filter |or| and |and|
    _tmpData = []
    for dep in tmpData:
	
	if dep.find("|or|") != -1:
	    deps = dep.split("|or|")
	    # find the best
	    results = []
	    for x in deps:
		if x.find("|and|") != -1:
		    anddeps = x.split("|and|")
		    results.append(anddeps)
		else:
		    if x:
		        results.append([x])
	
	    # now parse results
	    for result in results:
		outdeps = result[:]
		for y in result:
		    yresult = getInstalledAtoms(y)
		    if (yresult != None):
			outdeps.remove(y)
		if (not outdeps):
		    # find it
		    for y in result:
			_tmpData.append(y)
		    break
	
	else:
	    _tmpData.append(dep)

    dependencies = string.join(_tmpData," ")

    return dependencies, conflicts

def getPortageAppDbPath():
    rc = getPortageEnv("ROOT")+portage_const.VDB_PATH
    if (not rc.endswith("/")):
	return rc+"/"
    return rc

# Collect installed packages
def getInstalledPackages():
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getInstalledPackages: called. ")
    import os
    appDbDir = getPortageAppDbPath()
    dbDirs = os.listdir(appDbDir)
    installedAtoms = []
    for pkgsdir in dbDirs:
	if os.path.isdir(appDbDir+pkgsdir):
	    pkgdir = os.listdir(appDbDir+pkgsdir)
	    for pdir in pkgdir:
	        pkgcat = pkgsdir.split("/")[len(pkgsdir.split("/"))-1]
	        pkgatom = pkgcat+"/"+pdir
	        if pkgatom.find("-MERGING-") == -1:
	            installedAtoms.append(pkgatom)
    return installedAtoms, len(installedAtoms)

def getInstalledPackagesCounters():
    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"getInstalledPackages: called. ")
    import os
    appDbDir = getPortageAppDbPath()
    dbDirs = os.listdir(appDbDir)
    installedAtoms = []
    for pkgsdir in dbDirs:
	pkgdir = os.listdir(appDbDir+pkgsdir)
	for pdir in pkgdir:
	    pkgcat = pkgsdir.split("/")[len(pkgsdir.split("/"))-1]
	    pkgatom = pkgcat+"/"+pdir
	    if pkgatom.find("-MERGING-") == -1:
		# get counter
		f = open(appDbDir+pkgsdir+"/"+pdir+"/"+dbCOUNTER,"r")
		counter = f.readline().strip()
		f.close()
	        installedAtoms.append([pkgatom,int(counter)])
    return installedAtoms, len(installedAtoms)

def packageSearch(keyword):

    portageLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"packageSearch: called. ")

    SearchDirs = []
    # search in etpConst['portagetreedir']
    # and in overlays after etpConst['overlays']
    # fill the list
    portageRootDir = etpConst['portagetreedir']
    if not portageRootDir.endswith("/"):
	portageRootDir = portageRootDir+"/"
    ScanningDirectories = []
    ScanningDirectories.append(portageRootDir)
    for dir in etpConst['overlays'].split():
	if (not dir.endswith("/")):
	    dir = dir+"/"
	if os.path.isdir(dir):
	    ScanningDirectories.append(dir)

    for directoryTree in ScanningDirectories:
	treeList = os.listdir(directoryTree)
	_treeList = []
	# filter unwanted dirs
	for dir in treeList:
	    if (dir.find("-") != -1) and os.path.isdir(directoryTree+dir):
		_treeList.append(directoryTree+dir)
	treeList = _treeList

	for dir in treeList:
	    subdirs = os.listdir(dir)
	    for sub in subdirs:
		if (not sub.startswith(".")) and (sub.find(keyword) != -1):
		    if os.path.isdir(dir+"/"+sub):
			reldir = re.subn(directoryTree,"", dir+"/"+sub)[0]
			SearchDirs.append(reldir)
    
    # filter dupies
    SearchDirs = list(set(SearchDirs))
    return SearchDirs


'''
    Imported from portagelib.py of Porthole, thanks!
'''
def get_user_config(file, name=None, ebuild=None):
    """
    Function for parsing package.use, package.mask, package.unmask
    and package.keywords.
    
    Returns /etc/portage/<file> as a dictionary of ebuilds, with
    dict[ebuild] = list of flags.
    If name is given, it will be parsed for ebuilds with xmatch('match-all'),
    and only those ebuilds will be returned in dict.
    
    If <ebuild> is given, it will be matched against each line in <file>.
    For package.use/keywords, a list of applicable flags is returned.
    For package.mask/unmask, a list containing the matching lines is returned.
    """
    #print_info("PORTAGELIB: get_user_config('%s')" % file)
    maskfiles = ['package.mask', 'package.unmask']
    otherfiles = ['package.use', 'package.keywords']
    package_files = otherfiles + maskfiles
    if file not in package_files:
        print_info(" * PORTAGELIB: get_user_config(): unsupported config file '%s'" % file)
        return None
    filename = '/'.join([portage_const.USER_CONFIG_PATH, file])
    if not os.access(filename, os.R_OK):
        print_info(" * PORTAGELIB: get_user_config(): no read access on '%s'?" % file)
        return {}
    configfile = open(filename, 'r')
    configlines = configfile.readlines()
    configfile.close()
    config = [line.split() for line in configlines]
    # e.g. [['media-video/mplayer', 'real', '-v4l'], [app-portage/porthole', 'sudo']]
    dict = {}
    if ebuild is not None:
        result = []
        for line in config:
            if line and line[0]:
                if line[0].startswith('#'):
                    continue
                match = portage.portdb.xmatch('match-list', line[0], mylist=[ebuild])
                if match:
                    if file in maskfiles: result.extend(line[0]) # package.mask/unmask
                    else: result.extend(line[1:]) # package.use/keywords
        return result
    if name:
        target = portage.portdb.xmatch('match-all', name)
        for line in config:
            if line and line[0]:
                if line[0].startswith('#'):
                    continue
                ebuilds = portage.portdb.xmatch('match-all', line[0])
                for ebuild in ebuilds:
                    if ebuild in target:
                        dict[ebuild] = line[1:]
    else:
        for line in config:
            if line and line[0]:
                if line[0].startswith('#'):
                    continue
                ebuilds = portage.portdb.xmatch('match-all', line[0])
                for ebuild in ebuilds:
                    dict[ebuild] = line[1:]
    return dict
