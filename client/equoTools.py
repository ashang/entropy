#!/usr/bin/python
'''
    # DESCRIPTION:
    # Equo Library used by Python frontends

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

from sys import path, getfilesystemencoding
import os
import shutil
path.append('/usr/lib/entropy/libraries')
from entropyConstants import *
from clientConstants import *
from outputTools import *
from remoteTools import downloadData, getOnlineContent
from entropyTools import unpackGzip, unpackBzip2, compareMd5, bytesIntoHuman, askquestion, getRandomNumber, isjustname, dep_getkey, compareVersions as entropyCompareVersions, filterDuplicatedEntries, extractDuplicatedEntries, uncompressTarBz2, extractXpak, applicationLockCheck, countdown, isRoot, spliturl, remove_tag, dep_striptag, md5sum, allocateMaskedFile, istextfile, isnumber, extractEdb, getNewerVersion, getNewerVersionTag, unpackXpak, lifobuffer, writeNewBranch
from databaseTools import etpDatabase, openRepositoryDatabase, openClientDatabase, openGenericDatabase, fetchRepositoryIfNotAvailable
import triggerTools
import confTools
import dumpTools

# Logging initialization
import logTools
equoLog = logTools.LogFile(level = etpConst['equologlevel'],filename = etpConst['equologfile'], header = "[Equo]")

### Caching functions

def loadCaches():
    print_info(darkred(" @@ ")+blue("Loading On-Disk Cache..."))
    # atomMatch
    try:
        mycache = dumpTools.loadobj(etpCache['atomMatch'])
	if isinstance(mycache, dict):
	    atomMatchCache = mycache.copy()
    except:
	atomMatchCache = {}
	dumpTools.dumpobj(etpCache['atomMatch'],{})

    # removal dependencies
    try:
        mycache3 = dumpTools.loadobj(etpCache['generateDependsTree'])
	if isinstance(mycache3, dict):
	    generateDependsTreeCache = mycache3.copy()
    except:
	generateDependsTreeCache = {}
	dumpTools.dumpobj(etpCache['generateDependsTree'],{})


def saveCaches():
    dumpTools.dumpobj(etpCache['atomMatch'],atomMatchCache)
    if os.path.isfile(etpConst['dumpstoragedir']+"/"+etpCache['atomMatch']+".dmp"):
	if os.stat(etpConst['dumpstoragedir']+"/"+etpCache['atomMatch']+".dmp")[6] > etpCacheSizes['atomMatch']:
	    # clean cache
	    dumpTools.dumpobj(etpCache['atomMatch'],{})
    dumpTools.dumpobj(etpCache['generateDependsTree'],generateDependsTreeCache)
    if os.path.isfile(etpConst['dumpstoragedir']+"/"+etpCache['generateDependsTree']+".dmp"):
	if os.stat(etpConst['dumpstoragedir']+"/"+etpCache['generateDependsTree']+".dmp")[6] > etpCacheSizes['generateDependsTree']:
	    # clean cache
	    dumpTools.dumpobj(etpCache['generateDependsTree'],{})
    for dbinfo in dbCacheStore:
	dumpTools.dumpobj(dbinfo,dbCacheStore[dbinfo])
	# check size
	if os.path.isfile(etpConst['dumpstoragedir']+"/"+dbinfo+".dmp"):
	    if dbinfo.startswith(etpCache['dbMatch']):
	        if os.stat(etpConst['dumpstoragedir']+"/"+dbinfo+".dmp")[6] > etpCacheSizes['dbMatch']:
		    # clean cache
		    dumpTools.dumpobj(dbinfo,{})
	    elif dbinfo.startswith(etpCache['dbInfo']):
	        if os.stat(etpConst['dumpstoragedir']+"/"+dbinfo+".dmp")[6] > etpCacheSizes['dbInfo']:
		    # clean cache
		    dumpTools.dumpobj(dbinfo,{})
	    elif dbinfo.startswith(etpCache['dbSearch']):
	        if os.stat(etpConst['dumpstoragedir']+"/"+dbinfo+".dmp")[6] > etpCacheSizes['dbSearch']:
		    # clean cache
		    dumpTools.dumpobj(dbinfo,{})

########################################################
####
##   Repositories Tools
#

def repositories(options):
    
    # Options available for all the packages submodules
    myopts = options[1:]
    equoRequestAsk = False
    equoRequestPretend = False
    equoRequestPackagesCheck = False
    equoRequestForceUpdate = False
    rc = 0
    for opt in myopts:
	if (opt == "--ask"):
	    equoRequestAsk = True
	elif (opt == "--pretend"):
	    equoRequestPretend = True
	elif (opt == "--force"):
	    equoRequestForceUpdate = True

    if (options[0] == "update"):
	rc = syncRepositories(forceUpdate = equoRequestForceUpdate)

    if (options[0] == "status"):
	for repo in etpRepositories:
	    showRepositoryInfo(repo)

    if (options[0] == "repoinfo"):
	showRepositories()
    return rc

# this function shows a list of enabled repositories
def showRepositories():
    print_info(darkred(" * ")+darkgreen("Active Repositories:"))
    repoNumber = 0
    for repo in etpRepositories:
	repoNumber += 1
	print_info(blue("\t#"+str(repoNumber))+bold(" "+etpRepositories[repo]['description']))
	sourcecount = 0
	for pkgrepo in etpRepositories[repo]['packages']:
	    sourcecount += 1
	    print_info(red("\t\tPackages Mirror #"+str(sourcecount)+" : ")+darkgreen(pkgrepo))
	print_info(red("\t\tDatabase URL: ")+darkgreen(etpRepositories[repo]['database']))
	print_info(red("\t\tRepository name: ")+bold(repo))
	print_info(red("\t\tRepository database path: ")+blue(etpRepositories[repo]['dbpath']))
    return 0

def showRepositoryInfo(reponame):
    repoNumber = 0
    for repo in etpRepositories:
	repoNumber += 1
	if repo == reponame:
	    break
    print_info(blue("#"+str(repoNumber))+bold(" "+etpRepositories[reponame]['description']))
    if os.path.isfile(etpRepositories[reponame]['dbpath']+"/"+etpConst['etpdatabasefile']):
	status = "active"
    else:
	status = "never synced"
    print_info(darkgreen("\tStatus: ")+darkred(status))
    urlcount = 0
    for repourl in etpRepositories[reponame]['packages'][::-1]:
	urlcount += 1
        print_info(red("\tPackages URL #"+str(urlcount)+": ")+darkgreen(repourl))
    print_info(red("\tDatabase URL: ")+darkgreen(etpRepositories[reponame]['database']))
    print_info(red("\tRepository name: ")+bold(reponame))
    print_info(red("\tRepository database path: ")+blue(etpRepositories[reponame]['dbpath']))
    revision = getRepositoryRevision(reponame)
    mhash = getRepositoryDbFileHash(reponame)

    print_info(red("\tRepository database checksum: ")+mhash)
    print_info(red("\tRepository revision: ")+darkgreen(str(revision)))
    return 0

# @returns -1 if the file does not exist
# @returns int>0 if the file exists
def getRepositoryRevision(reponame):
    if os.path.isfile(etpRepositories[reponame]['dbpath']+"/"+etpConst['etpdatabaserevisionfile']):
	f = open(etpRepositories[reponame]['dbpath']+"/"+etpConst['etpdatabaserevisionfile'],"r")
	revision = int(f.readline().strip())
	f.close()
    else:
	revision = -1
    return revision

# @returns -1 if the file is not available
# @returns int>0 if the revision has been retrieved
def getOnlineRepositoryRevision(reponame):
    url = etpRepositories[reponame]['database']+"/"+etpConst['etpdatabaserevisionfile']
    status = getOnlineContent(url)
    if (status != False):
	status = status[0].strip()
	return int(status)
    else:
	return -1

# @returns -1 if the file does not exist
# @returns int>0 if the file exists
def getRepositoryDbFileHash(reponame):
    if os.path.isfile(etpRepositories[reponame]['dbpath']+"/"+etpConst['etpdatabasehashfile']):
	f = open(etpRepositories[reponame]['dbpath']+"/"+etpConst['etpdatabasehashfile'],"r")
	mhash = f.readline().strip().split()[0]
	f.close()
    else:
	mhash = "-1"
    return mhash

def syncRepositories(reponames = [], forceUpdate = False, quiet = False):

    # check if I am root
    if (not isRoot()):
	print_error(red("\t You must run this application as root."))
	return 1

    # check etpRepositories
    if len(etpRepositories) == 0:
	if (not quiet):
	    print_error(darkred(" * ")+red("No repositories specified in ")+etpConst['repositoriesconf'])
	return 127

    if (not quiet):
        print_info(darkred(" @@ ")+darkgreen("Repositories syncronization..."))
    repoNumber = 0
    syncErrors = False
    
    if (reponames == []):
	for x in etpRepositories:
	    reponames.append(x)
    
    dbupdated = False
    
    # Test network connectivity
    conntest = getOnlineContent("http://svn.sabayonlinux.org")
    if conntest == False:
	print_info(darkred(" @@ ")+darkgreen("You are not connected to the Internet. You should do it."))
	return 2
    
    for repo in reponames:
	
	repoNumber += 1
	
	if (not quiet):
	    print_info(blue("  #"+str(repoNumber))+bold(" "+etpRepositories[repo]['description']))
	    print_info(red("\tDatabase URL: ")+darkgreen(etpRepositories[repo]['database']))
	    print_info(red("\tDatabase local path: ")+darkgreen(etpRepositories[repo]['dbpath']))
	
	# check if database is already updated to the latest revision
	onlinestatus = getOnlineRepositoryRevision(repo)
	if (onlinestatus != -1):
	    localstatus = getRepositoryRevision(repo)
	    if (localstatus == onlinestatus) and (forceUpdate == False):
		if (not quiet):
		    print_info(bold("\tAttention: ")+red("database is already up to date."))
		continue
	
	# get database lock
	rc = downloadData(etpRepositories[repo]['database']+"/"+etpConst['etpdatabasedownloadlockfile'],"/dev/null")
	if rc != "-3": # cannot download database
	    if (not quiet):
	        print_error(bold("\tATTENTION -> ")+red("repository is being updated. Try again in few minutes."))
	    syncErrors = True
	    continue
	
	# database is going to be updated
	dbupdated = True
	# clear database interface cache belonging to this repository
	dumpTools.dumpobj(etpCache['dbInfo']+repo,{})
	
	cmethod = etpConst['etpdatabasecompressclasses'].get(etpRepositories[repo]['dbcformat'])
	if cmethod == None: raise Exception
	
	# starting to download
	if (not quiet):
	    print_info(red("\tDownloading database ")+darkgreen(etpConst[cmethod[2]])+red(" ..."))
	# create dir if it doesn't exist
	if not os.path.isdir(etpRepositories[repo]['dbpath']):
	    if (not quiet):
	        print_info(red("\t\tCreating database directory..."))
	    os.makedirs(etpRepositories[repo]['dbpath'])
	# download
	downloadData(etpRepositories[repo]['database']+"/"+etpConst[cmethod[2]],etpRepositories[repo]['dbpath']+"/"+etpConst[cmethod[2]])
	
	if (not quiet):
	    print_info(red("\tUnpacking database to ")+darkgreen(etpConst['etpdatabasefile'])+red(" ..."))
	eval(cmethod[1])(etpRepositories[repo]['dbpath']+"/"+etpConst[cmethod[2]])
	# download etpdatabasehashfile
	if (not quiet):
	    print_info(red("\tDownloading checksum ")+darkgreen(etpConst['etpdatabasehashfile'])+red(" ..."))
	downloadData(etpRepositories[repo]['database']+"/"+etpConst['etpdatabasehashfile'],etpRepositories[repo]['dbpath']+"/"+etpConst['etpdatabasehashfile'])
	# checking checksum
	if (not quiet):
	    print_info(red("\tChecking downloaded database ")+darkgreen(etpConst['etpdatabasefile'])+red(" ..."), back = True)
	f = open(etpRepositories[repo]['dbpath']+"/"+etpConst['etpdatabasehashfile'],"r")
	md5hash = f.readline().strip()
	md5hash = md5hash.split()[0]
	f.close()
	rc = compareMd5(etpRepositories[repo]['dbpath']+"/"+etpConst['etpdatabasefile'],md5hash)
	if rc:
	    if (not quiet):
	        print_info(red("\tDownloaded database status: ")+bold("OK"))
	else:
	    if (not quiet):
	        print_error(red("\tDownloaded database status: ")+darkred("ERROR"))
	        print_error(red("\t An error occured while checking database integrity"))
	    # delete all
	    if os.path.isfile(etpRepositories[repo]['dbpath']+"/"+etpConst['etpdatabasehashfile']):
		os.remove(etpRepositories[repo]['dbpath']+"/"+etpConst['etpdatabasehashfile'])
	    if os.path.isfile(etpRepositories[repo]['dbpath']+"/"+etpConst[cmethod[2]]):
		os.remove(etpRepositories[repo]['dbpath']+"/"+etpConst[cmethod[2]])
	    if os.path.isfile(etpRepositories[repo]['dbpath']+"/"+etpConst['etpdatabaserevisionfile']):
		os.remove(etpRepositories[repo]['dbpath']+"/"+etpConst['etpdatabaserevisionfile'])
	    syncErrors = True
	    continue
	
	# download etpdatabaserevisionfile
	if (not quiet):
	    print_info(red("\tDownloading revision ")+darkgreen(etpConst['etpdatabaserevisionfile'])+red(" ..."))
	downloadData(etpRepositories[repo]['database']+"/"+etpConst['etpdatabaserevisionfile'],etpRepositories[repo]['dbpath']+"/"+etpConst['etpdatabaserevisionfile'])
	
	if (not quiet):
	    print_info(red("\tUpdated repository revision: ")+bold(str(getRepositoryRevision(repo))))
	print_info(darkgreen("\tUpdate completed"))

    if syncErrors:
	if (not quiet):
	    print_warning(darkred(" @@ ")+red("Something bad happened. Please have a look."))
	return 128

    if (dbupdated):
	
	# safely clean ram caches
	atomMatchCache.clear()
	dumpTools.dumpobj(etpCache['atomMatch'],{})
	generateDependsTreeCache.clear()
	dumpTools.dumpobj(etpCache['generateDependsTree'],{})
	dbCacheStore.clear()
	
	# generate cache
        import cacheTools
        cacheTools.generateCache(quiet = quiet, depcache = True, configcache = False)

    return 0

def backupClientDatabase():
    if os.path.isfile(etpConst['etpdatabaseclientfilepath']):
	rnd = getRandomNumber()
	source = etpConst['etpdatabaseclientfilepath']
	dest = etpConst['etpdatabaseclientfilepath']+".backup."+str(rnd)
	shutil.copy2(source,dest)
	user = os.stat(source)[4]
	group = os.stat(source)[5]
	os.chown(dest,user,group)
	shutil.copystat(source,dest)
	return dest
    return ""


########################################################
####
##   Dependency handling functions
#

'''
   @description: matches the package that user chose, using dbconnection.atomMatch searching in all available repositories.
   @input atom: user choosen package name
   @output: the matched selection, list: [package id,repository name] | if nothing found, returns: ( -1,1 )
   @ exit errors:
	    -1 => repository cannot be fetched online
'''
def atomMatch(atom, caseSentitive = True, matchSlot = None, matchBranches = (), xcache = True):

    if xcache:
        cached = atomMatchCache.get(atom)
        if cached:
	    if (cached['matchSlot'] == matchSlot) and (cached['matchBranches'] == matchBranches):
	        return cached['result']

    repoResults = {}
    exitstatus = 0
    exitErrors = {}
    
    for repo in etpRepositories:
	# sync database if not available
	rc = fetchRepositoryIfNotAvailable(repo)
	if (rc != 0):
	    exitstatus = -1
	    exitErrors[repo] = -1
	    continue
	# open database
	dbconn = openRepositoryDatabase(repo, xcache = xcache)
	
	# search
	query = dbconn.atomMatch(atom, caseSensitive = caseSentitive, matchSlot = matchSlot, matchBranches = matchBranches)
	if query[1] == 0:
	    # package found, add to our dictionary
	    repoResults[repo] = query[0]
	
	dbconn.closeDB()

    # handle repoResults
    packageInformation = {}
    
    # nothing found
    if len(repoResults) == 0:
	atomMatchCache[atom] = {}
	atomMatchCache[atom]['result'] = -1,1
	atomMatchCache[atom]['matchSlot'] = matchSlot
	atomMatchCache[atom]['matchBranches'] = matchBranches
	return -1,1
    
    elif len(repoResults) == 1:
	# one result found
	for repo in repoResults:
	    atomMatchCache[atom] = {}
	    atomMatchCache[atom]['result'] = repoResults[repo],repo
	    atomMatchCache[atom]['matchSlot'] = matchSlot
	    atomMatchCache[atom]['matchBranches'] = matchBranches
	    return repoResults[repo],repo
    
    elif len(repoResults) > 1:
	# we have to decide which version should be taken
	
	# get package information for all the entries
	for repo in repoResults:
	    
	    # open database
	    dbconn = openRepositoryDatabase(repo)
	
	    # search
	    packageInformation[repo] = {}
	    packageInformation[repo]['version'] = dbconn.retrieveVersion(repoResults[repo])
	    packageInformation[repo]['versiontag'] = dbconn.retrieveVersionTag(repoResults[repo])
	    packageInformation[repo]['revision'] = dbconn.retrieveRevision(repoResults[repo])
	    dbconn.closeDB()

	versions = []
	repoNames = []
	# compare versions
	for repo in packageInformation:
	    repoNames.append(repo)
	    versions.append(packageInformation[repo]['version'])
	
	# found duplicates, this mean that we have to look at the revision and then, at the version tag
	# if all this shait fails, get the uppest repository
	# if no duplicates, we're done
	#print versions
	filteredVersions = filterDuplicatedEntries(versions)
	if (len(versions) > len(filteredVersions)):
	    # there are duplicated results, fetch them
	    # get the newerVersion
	    #print versions
	    newerVersion = getNewerVersion(versions)
	    newerVersion = newerVersion[0]
	    # is newerVersion, the duplicated one?
	    duplicatedEntries = extractDuplicatedEntries(versions)
	    needFiltering = False
	    if newerVersion in duplicatedEntries:
		needFiltering = True
	    
	    if (needFiltering):
		# we have to decide which one is good
		#print "need filtering"
		# we have newerVersion
		conflictingEntries = {}
		for repo in packageInformation:
		    if packageInformation[repo]['version'] == newerVersion:
			conflictingEntries[repo] = {}
			#conflictingEntries[repo]['version'] = packageInformation[repo]['version']
			conflictingEntries[repo]['versiontag'] = packageInformation[repo]['versiontag']
			conflictingEntries[repo]['revision'] = packageInformation[repo]['revision']
		
		# at this point compare tags
		tags = []
		for repo in conflictingEntries:
		    tags.append(conflictingEntries[repo]['versiontag'])
		newerTag = getNewerVersionTag(tags)
		newerTag = newerTag[0]
		
		# is the chosen tag duplicated?
		duplicatedTags = extractDuplicatedEntries(tags)
		needFiltering = False
		if newerTag in duplicatedTags:
		    needFiltering = True
		
		if (needFiltering):
		    #print "also tags match"
		    # yes, it is. we need to compare revisions
		    conflictingTags = {}
		    for repo in conflictingEntries:
		        if conflictingEntries[repo]['versiontag'] == newerTag:
			    conflictingTags[repo] = {}
			    #conflictingTags[repo]['version'] = conflictingEntries[repo]['version']
			    #conflictingTags[repo]['versiontag'] = conflictingEntries[repo]['versiontag']
			    conflictingTags[repo]['revision'] = conflictingEntries[repo]['revision']
		    
		    #print tags
		    #print conflictingTags
		    revisions = []
		    for repo in conflictingTags:
			revisions.append(str(conflictingTags[repo]['revision']))
		    newerRevision = getNewerVersionTag(revisions)
		    newerRevision = newerRevision[0]
		    duplicatedRevisions = extractDuplicatedEntries(revisions)
		    needFiltering = False
		    if newerRevision in duplicatedRevisions:
			needFiltering = True
		
		    if (needFiltering):
			# ok, we must get the repository with the biggest priority
			#print "d'oh"
		        # I'm pissed off, now I get the repository name and quit
			for repository in etpRepositoriesOrder:
			    for repo in conflictingTags:
				if repository == repo:
				    # found it, WE ARE DOOONE!
				    atomMatchCache[atom] = {}
				    atomMatchCache[atom]['result'] = repoResults[repo],repo
				    atomMatchCache[atom]['matchSlot'] = matchSlot
				    atomMatchCache[atom]['matchBranches'] = matchBranches
				    return [repoResults[repo],repo]
		    
		    else:
			# we are done!!!
		        reponame = ''
			#print conflictingTags
		        for x in conflictingTags:
		            if str(conflictingTags[x]['revision']) == str(newerRevision):
			        reponame = x
			        break
			atomMatchCache[atom] = {}
			atomMatchCache[atom]['result'] = repoResults[reponame],reponame
			atomMatchCache[atom]['matchSlot'] = matchSlot
			atomMatchCache[atom]['matchBranches'] = matchBranches
		        return repoResults[reponame],reponame
		
		else:
		    # we're finally done
		    reponame = ''
		    for x in conflictingEntries:
		        if conflictingEntries[x]['versiontag'] == newerTag:
			    reponame = x
			    break
		    atomMatchCache[atom] = {}
		    atomMatchCache[atom]['result'] = repoResults[reponame],reponame
		    atomMatchCache[atom]['matchSlot'] = matchSlot
		    atomMatchCache[atom]['matchBranches'] = matchBranches
		    return repoResults[reponame],reponame

	    else:
		# we are fine, the newerVersion is not one of the duplicated ones
		reponame = ''
		for x in packageInformation:
		    if packageInformation[x]['version'] == newerVersion:
			reponame = x
			break
		atomMatchCache[atom] = {}
		atomMatchCache[atom]['result'] = repoResults[reponame],reponame
		atomMatchCache[atom]['matchSlot'] = matchSlot
		atomMatchCache[atom]['matchBranches'] = matchBranches
		return repoResults[reponame],reponame

	    #print versions
	
	else:
	    # yeah, we're done, just return the info
	    #print versions
	    newerVersion = getNewerVersion(versions)
	    # get the repository name
	    newerVersion = newerVersion[0]
	    reponame = ''
	    for x in packageInformation:
		if packageInformation[x]['version'] == newerVersion:
		    reponame = x
		    break
	    #print reponame
	    atomMatchCache[atom] = {}
	    atomMatchCache[atom]['result'] = repoResults[reponame],reponame
	    atomMatchCache[atom]['matchSlot'] = matchSlot
	    atomMatchCache[atom]['matchBranches'] = matchBranches
	    return repoResults[reponame],reponame

def listAllAvailableBranches():
    branches = set()
    for repo in etpRepositories:
        dbconn = openRepositoryDatabase(repo)
        branches.update(dbconn.listAllBranches())
        dbconn.closeDB()
    return branches

'''
   @description: generates the dependencies of a [id,repository name] combo.
   @input packageInfo: tuple composed by int(id) and str(repository name), if this one is int(0), the client database will be opened.
   @output: ordered dependency list
'''
getDependenciesCache = {}
def getDependencies(packageInfo):

    ''' caching '''
    cached = getDependenciesCache.get(tuple(packageInfo))
    if cached:
	return cached['result']

    idpackage = packageInfo[0]
    reponame = packageInfo[1]
    if reponame == 0:
	dbconn = openClientDatabase()
    else:
	dbconn = openRepositoryDatabase(reponame)
    
    # retrieve dependencies
    depend = dbconn.retrieveDependencies(idpackage)
    # and conflicts
    conflicts = dbconn.retrieveConflicts(idpackage)
    for x in conflicts:
	depend.add("!"+x)
    dbconn.closeDB()

    ''' caching '''
    getDependenciesCache[tuple(packageInfo)] = {}
    getDependenciesCache[tuple(packageInfo)]['result'] = depend

    return depend

'''
   @description: filter the already installed dependencies
   @input dependencies: list of dependencies to check
   @output: filtered list, aka the needed ones and the ones satisfied
'''
filterSatisfiedDependenciesCache = {}
filterSatisfiedDependenciesCmpResults = {} # 0: not installed, <0 a<b | >0 a>b
def filterSatisfiedDependencies(dependencies, deepdeps = False):

    unsatisfiedDeps = set()
    satisfiedDeps = set()
    # now create a list with the unsatisfied ones
    # query the installed packages database
    #print etpConst['etpdatabaseclientfilepath']
    clientDbconn = openClientDatabase()
    if (clientDbconn != -1):
        for dependency in dependencies:

	    depsatisfied = set()
	    depunsatisfied = set()

            ''' caching '''
	    cached = filterSatisfiedDependenciesCache.get(dependency)
	    if cached:
		if (cached['deepdeps'] == deepdeps):
		    unsatisfiedDeps.update(cached['depunsatisfied'])
		    satisfiedDeps.update(cached['depsatisfied'])
		    continue

	    ### conflict
	    if dependency[0] == "!":
		testdep = dependency[1:]
		xmatch = clientDbconn.atomMatch(testdep)
		if xmatch[0] != -1:
		    unsatisfiedDeps.add(dependency)
		else:
		    satisfiedDeps.add(dependency)
		continue

	    repoMatch = atomMatch(dependency)
	    if repoMatch[0] != -1:
		dbconn = openRepositoryDatabase(repoMatch[1])
		repo_pkgver = dbconn.retrieveVersion(repoMatch[0])
		repo_pkgtag = dbconn.retrieveVersionTag(repoMatch[0])
		repo_pkgrev = dbconn.retrieveRevision(repoMatch[0])
		dbconn.closeDB()
	    else:
		# dependency does not exist in our database
		unsatisfiedDeps.add(dependency)
		continue

	    clientMatch = clientDbconn.atomMatch(dependency)
	    if clientMatch[0] != -1:
		
		installedVer = clientDbconn.retrieveVersion(clientMatch[0])
		installedTag = clientDbconn.retrieveVersionTag(clientMatch[0])
		installedRev = clientDbconn.retrieveRevision(clientMatch[0])
		
		if (deepdeps):
		    cmp = compareVersions((repo_pkgver,repo_pkgtag,repo_pkgrev),(installedVer,installedTag,installedRev))
		    #print repo_pkgver+"<-->"+installedVer
		    #print cmp
		    if cmp != 0:
		        #print dependency
			filterSatisfiedDependenciesCmpResults[dependency] = cmp
	                depunsatisfied.add(dependency)
		    else:
		        depsatisfied.add(dependency)
		else:
		    depsatisfied.add(dependency)
	    else:
		#print " ----> "+dependency+" NOT installed."
		filterSatisfiedDependenciesCmpResults[dependency] = 0
		depunsatisfied.add(dependency)
	
	    
	    unsatisfiedDeps.update(depunsatisfied)
	    satisfiedDeps.update(depsatisfied)
	    
	    ''' caching '''
	    filterSatisfiedDependenciesCache[dependency] = {}
	    filterSatisfiedDependenciesCache[dependency]['depunsatisfied'] = depunsatisfied
	    filterSatisfiedDependenciesCache[dependency]['depsatisfied'] = depsatisfied
	    filterSatisfiedDependenciesCache[dependency]['deepdeps'] = deepdeps
    
        clientDbconn.closeDB()

    return unsatisfiedDeps, satisfiedDeps

'''
   @description: generates a dependency tree using unsatisfied dependencies
   @input package: atomInfo (idpackage,reponame)
   @output: dependency tree dictionary, plus status code
'''
generateDependencyTreeCache = {}
matchFilter = set()
def generateDependencyTree(atomInfo, emptydeps = False, deepdeps = False, usefilter = False):

    if (not usefilter):
	matchFilter.clear()

    ''' caching '''
    cached = generateDependencyTreeCache.get(tuple(atomInfo))
    if cached:
	if (cached['emptydeps'] == emptydeps) and \
	    (cached['deepdeps'] == deepdeps) and \
	    (cached['usefilter'] == usefilter):
	    return cached['result']

    #print atomInfo
    mydbconn = openRepositoryDatabase(atomInfo[1])
    myatom = mydbconn.retrieveAtom(atomInfo[0])
    mydbconn.closeDB()

    # caches
    treecache = set()
    matchcache = set()
    # special events
    dependenciesNotFound = set()
    conflicts = set()

    mydep = (1,myatom)
    #mytree = []
    mybuffer = lifobuffer()
    deptree = set()
    if not ((atomInfo in matchFilter) and (usefilter)):
        mybuffer.push((1,myatom))
        #mytree.append((1,myatom))
        deptree.add((1,atomInfo))
    clientDbconn = openClientDatabase()

    
    while mydep != None:

        # already analyzed in this call
        if mydep[1] in treecache:
            mydep = mybuffer.pop()
            continue
        treecache.add(mydep[1])

        # conflicts
        if mydep[1][0] == "!":
            xmatch = clientDbconn.atomMatch(mydep[1][1:])
            if xmatch[0] != -1:
                conflicts.add(xmatch[0])
            mydep = mybuffer.pop()
            continue

        # atom found?
        match = atomMatch(mydep[1])
        if match[0] == -1:
            dependenciesNotFound.add(mydep[1])
            mydep = mybuffer.pop()
            continue

        # already analyzed by the calling function
        if (match in matchFilter) and (usefilter):
            mydep = mybuffer.pop()
            continue
        if usefilter: matchFilter.add(match)

        # result already analyzed?
        if match in matchcache:
            mydep = mybuffer.pop()
            continue

        treedepth = mydep[0]+1

        # handle possible library breakage
        action = filterSatisfiedDependenciesCmpResults.get(mydep)
        if action and ((action < 0) or (action > 0)): # do not use != 0 since action can be "None"
            i = clientDbconn.atomMatch(mydep)
            if i[0] != -1:
                oldneeded = clientDbconn.retrieveNeeded(i[0])
                if oldneeded: # if there are needed
                    ndbconn = openRepositoryDatabase(atom[1])
                    needed = ndbconn.retrieveNeeded(atom[0])
                    ndbconn.closeDB()
                    oldneeded.difference_update(needed)
                    if oldneeded:
                        # reverse lookup to find belonging package
                        for need in oldneeded:
                            myidpackages = clientDbconn.searchNeeded(need)
                            for myidpackage in myidpackages:
                                myname = clientDbconn.retrieveName(myidpackage)
                                mycategory = clientDbconn.retrieveCategory(myidpackage)
                                myslot = clientDbconn.retrieveSlot(myidpackage)
                                mykey = mycategory+"/"+myname
                                mymatch = atomMatch(mykey, matchSlot = myslot) # search in our repo
                                if mymatch[0] != -1:
                                    mydbconn = openRepositoryDatabase(mymatch[1])
                                    mynewatom = mydbconn.retrieveAtom(mymatch[0])
                                    mydbconn.closeDB()
                                    if (mymatch not in matchcache) and (mynewatom not in treecache):
                                        mybuffer.push((treedepth,mynewatom))
                                else:
                                    # we bastardly ignore the missing library for now
                                    continue

        
        # all checks passed, well done
        matchcache.add(match)
        deptree.add((mydep[0],match)) # add match

        myundeps = getDependencies(match)
        # in this way filterSatisfiedDependenciesCmpResults is alway consistent
        mytestdeps, xxx = filterSatisfiedDependencies(myundeps, deepdeps = deepdeps)
        if (not emptydeps):
            myundeps = mytestdeps
        for x in myundeps:
            mybuffer.push((treedepth,x))
        
        mydep = mybuffer.pop()

    newdeptree = {}
    for x in deptree:
        key = x[0]
        item = x[1]
        try:
            newdeptree[key].add(item)
        except:
            newdeptree[key] = set()
            newdeptree[key].add(item)
    del deptree
    
    clientDbconn.closeDB()
    
    if (dependenciesNotFound):
	# Houston, we've got a problem
	flatview = list(dependenciesNotFound)
	return flatview,-2

    # conflicts
    newdeptree[0] = conflicts

    ''' caching '''
    generateDependencyTreeCache[tuple(atomInfo)] = {}
    generateDependencyTreeCache[tuple(atomInfo)]['result'] = newdeptree,0
    generateDependencyTreeCache[tuple(atomInfo)]['emptydeps'] = emptydeps
    generateDependencyTreeCache[tuple(atomInfo)]['deepdeps'] = deepdeps
    generateDependencyTreeCache[tuple(atomInfo)]['usefilter'] = usefilter
    treecache.clear()
    matchcache.clear()
    
    return newdeptree,0 # note: newtree[0] contains possible conflicts


'''
   @description: generates a list cotaining the needed dependencies of a list requested atoms
   @input package: list of atoms that would be installed in list form, whose each element is composed by [idpackage,repository name]
   @output: list containing, for each element: [idpackage,repository name]
   		@ if dependencies couldn't be satisfied, the output will be -1
   @note: this is the function that should be used for 3rd party applications after using atomMatch()
'''
def getRequiredPackages(foundAtoms, emptydeps = False, deepdeps = False, spinning = False):
    deptree = {}
    deptree[0] = set()
    
    if spinning: atomlen = len(foundAtoms); count = 0
    matchFilter.clear() # clear generateDependencyTree global filter
    for atomInfo in foundAtoms:
	if spinning: count += 1; print_info(":: "+str(round((float(count)/atomlen)*100,1))+"% ::", back = True)
	#print depcount
	newtree, result = generateDependencyTree(atomInfo, emptydeps, deepdeps, usefilter = True)
	if (result != 0):
	    return newtree, result
	elif (newtree):
            parent_keys = deptree.keys()
            # add conflicts
            max_parent_key = parent_keys[-1]
            deptree[0].update(newtree[0])
            
            # reverse dict
            levelcount = 0
            reversetree = {}
            for key in newtree.keys()[::-1]:
                if key == 0:
                    continue
                levelcount += 1
                reversetree[levelcount] = newtree[key]
            del newtree
            
            for mylevel in reversetree.keys():
                deptree[max_parent_key+mylevel] = reversetree[mylevel].copy()
            del reversetree

    matchFilter.clear()
    
    return deptree,0


'''
   @description: generates a depends tree using provided idpackages (from client database)
   		 !!! you can see it as the function that generates the removal tree
   @input package: idpackages list
   @output: 	depends tree dictionary, plus status code
'''
def generateDependsTree(idpackages, deep = False):

    ''' caching '''
    cached = generateDependsTreeCache.get(tuple(idpackages))
    if cached:
	if (cached['deep'] == deep):
	    return cached['result']

    dependscache = {}
    clientDbconn = openClientDatabase()

    dependsOk = False
    treeview = set(idpackages)
    treelevel = idpackages[:]
    tree = {}
    treedepth = 0 # I start from level 1 because level 0 is idpackages itself
    tree[treedepth] = set(idpackages)
    monotree = set(idpackages) # monodimensional tree
    
    # check if dependstable is sane before beginning
    rx = clientDbconn.retrieveDepends(idpackages[0])
    if rx == -2:
	# generation needed
	clientDbconn.regenerateDependsTable(output = False)
    
    while (not dependsOk):
	treedepth += 1
	tree[treedepth] = set()
        for idpackage in treelevel:

	    passed = dependscache.get(idpackage,None)
	    systempkg = clientDbconn.isSystemPackage(idpackage)
	    if passed or systempkg:
		try:
		    while 1: treeview.remove(idpackage)
		except:
		    pass
		continue

	    # obtain its depends
	    depends = clientDbconn.retrieveDepends(idpackage)
	    # filter already satisfied ones
	    depends = [x for x in depends if x not in list(monotree)]
	    if (depends): # something depends on idpackage
		for x in depends:
		    if x not in tree[treedepth]:
			tree[treedepth].add(x)
			monotree.add(x)
		        treeview.add(x)
	    elif deep: # if no depends found, grab its dependencies and check
		
	        mydeps = set(clientDbconn.retrieveDependencies(idpackage))
		_mydeps = set()
		for x in mydeps:
		    match = clientDbconn.atomMatch(x)
		    if match and match[1] == 0:
		        _mydeps.add(match[0])
		mydeps = _mydeps
		# now filter them
		mydeps = [x for x in mydeps if x not in list(monotree)]
		for x in mydeps:
		    #print clientDbconn.retrieveAtom(x)
		    mydepends = clientDbconn.retrieveDepends(x)
		    mydepends = [y for y in mydepends if y not in list(monotree)]
		    if (not mydepends):
			tree[treedepth].add(x)
			monotree.add(x)
			treeview.add(x)

	    dependscache[idpackage] = True
	    try:
		while 1: treeview.remove(idpackage)
	    except:
	        pass
	
	treelevel = list(treeview)[:]
	if (not treelevel):
	    if not tree[treedepth]:
		del tree[treedepth] # probably the last one is empty then
	    dependsOk = True

    newtree = tree.copy() # tree list
    if (tree):
	# now filter newtree
	treelength = len(newtree)
	for count in range(treelength)[::-1]:
	    x = 0
	    while x < count:
		# remove dups in this list
		for z in newtree[count]:
		    try:
			while 1:
			    newtree[x].remove(z)
			    #print "removing "+str(z)
		    except:
			pass
		x += 1
    
    del tree
    
    clientDbconn.closeDB()
    
    ''' caching '''
    generateDependsTreeCache[tuple(idpackages)] = {}
    generateDependsTreeCache[tuple(idpackages)]['result'] = newtree,0
    generateDependsTreeCache[tuple(idpackages)]['deep'] = deep
    return newtree,0 # treeview is used to show deps while tree is used to run the dependency code.


'''
   @description: compare two lists composed by [version,tag,revision] and [version,tag,revision]
   			if listA > listB --> positive number
			if listA == listB --> 0
			if listA < listB --> negative number	
   @input package: listA[version,tag,rev] and listB[version,tag,rev]
   @output: integer number
'''
def compareVersions(listA,listB):
    if len(listA) != 3 or len(listB) != 3:
	raise Exception, "compareVersions: listA and/or listB must be long 3"
    # start with version
    rc = entropyCompareVersions(listA[0],listB[0])
    
    if (rc == 0):
	# check tag
	if listA[1] > listB[1]:
	    return 1
	elif listA[1] < listB[1]:
	    return -1
	else:
	    # check rev
	    if listA[2] > listB[2]:
		return 1
	    elif listA[2] < listB[2]:
		return -1
	    else:
		return 0
    return rc


########################################################
####
##   Files handling
#

'''
   @description: check if Equo has to download the given package
   @input package: filename to check inside the packages directory -> file, checksum of the package -> checksum
   @output: -1 = should be downloaded, -2 = digest broken (not mandatory), remove & download, 0 = all fine, we don't need to download it
'''
def checkNeededDownload(filepath,checksum = None):
    # is the file available
    if os.path.isfile(etpConst['entropyworkdir']+"/"+filepath):
	if checksum is None:
	    return 0
	else:
	    # check digest
	    md5res = compareMd5(etpConst['entropyworkdir']+"/"+filepath,checksum)
	    if (md5res):
		return 0
	    else:
		return -2
    else:
	return -1


'''
   @description: download a package into etpConst['packagesbindir'] passing all the available mirrors
   @input package: repository -> name of the repository, filename -> name of the file to download, digest -> md5 hash of the file
   @output: 0 = all fine, -3 = error on all the available mirrors
'''
def fetchFileOnMirrors(repository, filename, digest = False):

    uris = etpRepositories[repository]['packages'][::-1]
    remaining = set(uris[:])

    mirrorcount = 0
    for uri in uris:
	
	if len(remaining) == 0:
	    # tried all the mirrors, quitting for error
	    return -3
	mirrorcount += 1
	mirrorCountText = "( mirror #"+str(mirrorcount)+" ) "
        # now fetch the new one
	url = uri+"/"+filename
	print_info(red("   ## ")+mirrorCountText+blue("Downloading from: ")+red(spliturl(url)[1]))
	rc = fetchFile(url, digest)
	if rc == 0:
	    print_info(red("   ## ")+mirrorCountText+blue("Successfully downloaded from: ")+red(spliturl(url)[1]))
	    return 0
	else:
	    # something bad happened
	    if rc == -1:
		print_info(red("   ## ")+mirrorCountText+blue("Error downloading from: ")+red(spliturl(url)[1])+" - file not available on this mirror.")
	    elif rc == -2:
		print_info(red("   ## ")+mirrorCountText+blue("Error downloading from: ")+red(spliturl(url)[1])+" - wrong checksum.")
	    elif rc == -3:
		print_info(red("   ## ")+mirrorCountText+blue("Error downloading from: ")+red(spliturl(url)[1])+" - not found.")
	    elif rc == -4:
		print_info(red("   ## ")+mirrorCountText+blue("Discarded download."))
		return -1
	    else:
		print_info(red("   ## ")+mirrorCountText+blue("Error downloading from: ")+red(spliturl(url)[1])+" - unknown reason.")
	    try:
	        remaining.remove(uri)
	    except:
		pass

'''
   @description: download a package into etpConst['packagesbindir'] and check for digest if digest is not False
   @input package: url -> HTTP/FTP url, digest -> md5 hash of the file
   @output: -1 = download error (cannot find the file), -2 = digest error, 0 = all fine
'''
def fetchFile(url, digest = False):
    # remove old
    filename = os.path.basename(url)
    filepath = etpConst['packagesbindir']+"/"+etpConst['branch']+"/"+filename
    if os.path.exists(filepath):
	os.remove(filepath)

    # now fetch the new one
    try:
        fetchChecksum = downloadData(url,filepath)
    except KeyboardInterrupt:
	return -4
    except:
	return -1
    if fetchChecksum == "-3":
	return -3
    if (digest != False):
	#print digest+" <--> "+fetchChecksum
	if (fetchChecksum != digest):
	    # not properly downloaded
	    return -2
	else:
	    return 0
    return 0

def matchChecksum(infoDict):
    dlcount = 0
    match = False
    while dlcount <= 5:
	print_info(red("   ## ")+blue("Checking package checksum..."), back = True)
	dlcheck = checkNeededDownload(infoDict['download'], checksum = infoDict['checksum'])
	if dlcheck == 0:
	    print_info(red("   ## ")+blue("Package checksum matches."))
	    match = True
	    break # file downloaded successfully
	else:
	    dlcount += 1
	    print_info(red("   ## ")+blue("Package checksum does not match. Redownloading... attempt #"+str(dlcount)), back = True)
	    fetch = fetchFileOnMirrors(infoDict['repository'],infoDict['download'],infoDict['checksum'])
	    if fetch != 0:
		print_info(red("   ## ")+blue("Cannot properly fetch package! Quitting."))
		return 1
    if (not match):
	print_info(red("   ## ")+blue("Cannot properly fetch package or checksum does not match. Try running again '")+bold("equo update")+blue("'"))
	return 1
    return 0

def removePackage(infoDict):
    
    atom = infoDict['removeatom']
    content = infoDict['removecontent']
    removeidpackage = infoDict['removeidpackage']

    equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"Removing package: "+str(atom))

    # clear on-disk cache
    generateDependsTreeCache.clear()
    dumpTools.dumpobj(etpCache['generateDependsTree'],generateDependsTreeCache)

    # load content cache if found empty
    if etpConst['collisionprotect'] > 0:
        if (not contentCache):
	    clientDbconn = openClientDatabase()
	    xlist = clientDbconn.listAllFiles(clean = True)
	    for x in xlist:
		contentCache[x] = 1
	    clientDbconn.closeDB()

    # remove from database
    if removeidpackage != -1:
	print_info(red("   ## ")+blue("Removing from database: ")+red(infoDict['removeatom']))
	removePackageFromDatabase(removeidpackage)

    # Handle gentoo database
    if (etpConst['gentoo-compat']):
	gentooAtom = dep_striptag(remove_tag(atom)) # FIXME: remove dep_striptag asap
        equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"Removing package from Gentoo database: "+str(gentooAtom))
	removePackageFromGentooDatabase(gentooAtom)

    # load CONFIG_PROTECT and its mask - client database at this point has been surely opened, so our dicts are already filled
    protect = etpConst['dbconfigprotect']
    mask = etpConst['dbconfigprotectmask']

    # merge data into system
    for file in content:
	# collision check
	if etpConst['collisionprotect'] > 0:
	    if file in contentCache:
		print_warning(darkred("   ## ")+red("Collision found during remove for ")+file.encode(getfilesystemencoding())+" - cannot overwrite")
        	equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"Collision found during remove for "+file.encode(getfilesystemencoding())+" - cannot overwrite")
		continue
	    try:
	        del contentCache[file]
	    except:
	        pass
	file = file.encode(getfilesystemencoding())

	protected = False
	if (not infoDict['removeconfig']) and (not infoDict['diffremoval']):
	    try:
	        # -- CONFIGURATION FILE PROTECTION --
	        if os.access(file,os.R_OK):
	            for x in protect:
		        if file.startswith(x):
		            protected = True
		            break
	            if (protected):
		        for x in mask:
		            if file.startswith(x):
			        protected = False
			        break
	            if (protected) and os.path.isfile(file):
		        protected = istextfile(file)
		    else:
		        protected = False # it's not a file
	        # -- CONFIGURATION FILE PROTECTION --
	    except:
		pass # some filenames are buggy encoded
	
	if (protected):
            equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_VERBOSE,"[remove] Protecting config file:  "+str(file))
	    print_warning(darkred("   ## ")+red("[remove] Protecting config file: ")+str(file))
	else:
	    try:
	        os.remove(file)
	        #print file
	        # is now empty?
	        filedir = os.path.dirname(file)
	        dirlist = os.listdir(filedir)
	        if (not dirlist):
		    os.removedirs(filedir)
	    except OSError:
	        try:
		    os.removedirs(file) # is it a dir?, empty?
	            #print "debug: was a dir"
	        except:
		    #print "debug: the dir wasn't empty? -> "+str(file)
		    pass
    return 0


'''
   @description: unpack the given file on the system, update database and also update gentoo db if requested
   @input package: package file (without path)
   @output: 0 = all fine, >0 = error!
'''
def installPackage(infoDict):

    clientDbconn = openClientDatabase()
    package = infoDict['download']

    # clear on-disk cache
    generateDependsTreeCache.clear()
    dumpTools.dumpobj(etpCache['generateDependsTree'],{})

    equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"Installing package: "+str(infoDict['atom']))

    # load content cache if found empty
    if etpConst['collisionprotect'] > 0:
        if (not contentCache):
	    xlist = clientDbconn.listAllFiles(clean = True)
	    for x in xlist:
		contentCache[x] = 1

    # unpack and install
    if infoDict['repository'].endswith(".tbz2"):
        pkgpath = etpRepositories[infoDict['repository']]['pkgpath']
    else:
        pkgpath = etpConst['entropyworkdir']+"/"+package
    unpackDir = etpConst['entropyunpackdir']+"/"+package
    if os.path.isdir(unpackDir):
	os.system("rm -rf "+unpackDir)
    imageDir = unpackDir+"/image"
    os.makedirs(imageDir)
    
    rc = uncompressTarBz2(pkgpath,imageDir)
    if (rc != 0):
	return rc
    if not os.path.isdir(imageDir):
	return 2
    
    # load CONFIG_PROTECT and its mask
    protect = etpRepositories[infoDict['repository']]['configprotect']
    mask = etpRepositories[infoDict['repository']]['configprotectmask']
    
    packageContent = []
    # setup imageDir properly
    imageDir = imageDir.encode(getfilesystemencoding())
    # merge data into system
    for currentdir,subdirs,files in os.walk(imageDir):
	# create subdirs
        for dir in subdirs:
	    #dirpath += "/"+dir
	    imagepathDir = currentdir + "/" + dir
	    rootdir = imagepathDir[len(imageDir):]
	    # get info
	    if (rootdir):
		if os.path.islink(rootdir):
		    if not os.path.exists(rootdir): # broken symlink
			#print "I want to remove "+rootdir
			#print os.readlink(rootdir)
		        os.remove(rootdir)
		elif os.path.isfile(rootdir): # weird
    		    equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"WARNING!!! "+str(rootdir)+" is a file when it should be a directory !! Removing in 10 seconds...")
		    print_warning(red(" *** ")+bold(rootdir)+red(" is a file when it should be a directory !! Removing in 10 seconds..."))
		    import time
		    time.sleep(10)
		    os.remove(rootdir)
	        if (not os.path.isdir(rootdir)) and (not os.access(rootdir,os.R_OK)):
		    #print "creating dir "+rootdir
		    os.makedirs(rootdir)
	    user = os.stat(imagepathDir)[4]
	    group = os.stat(imagepathDir)[5]
	    os.chown(rootdir,user,group)
	    shutil.copystat(imagepathDir,rootdir)
	#dirpath = ''
	for file in files:
	    fromfile = currentdir+"/"+file
	    tofile = fromfile[len(imageDir):]
	    
	    if etpConst['collisionprotect'] > 1:
		if tofile in contentCache:
		    print_warning(darkred("   ## ")+red("Collision found during install for ")+file.encode(getfilesystemencoding())+" - cannot overwrite")
    		    equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"WARNING!!! Collision found during install for "+file.encode(getfilesystemencoding())+" - cannot overwrite")
    		    equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"[collision] Protecting config file: "+str(tofile))
		    print_warning(darkred("   ## ")+red("[collision] Protecting config file: ")+str(tofile))
		    continue

	    # -- CONFIGURATION FILE PROTECTION --
	    protected = False

	    try:
	        for x in protect:
		    if tofile.startswith(x):
		        protected = True
		        break
	        if (protected): # check if perhaps, file is masked, so unprotected
		    for x in mask:
		        if tofile.startswith(x):
			    protected = False
			    break
	    
	        if os.access(tofile,os.F_OK):
		    try:
		        if not protected: os.remove(tofile)
		    except:
		        if not protected:
		            rc = os.system("rm -f "+tofile)
		            if (rc != 0):
			        return 3
	        else:
		    protected = False # file doesn't exist

	        # check if it's a text file
	        if (protected) and os.path.isfile(tofile):
		    protected = istextfile(tofile)
	        else:
		    protected = False # it's not a file

	        # check md5
	        if (protected) and os.path.isfile(tofile) and os.path.isfile(fromfile):
		    mymd5 = md5sum(fromfile)
		    sysmd5 = md5sum(tofile)
		    if mymd5 == sysmd5:
		        protected = False # files are the same
	        else:
		    protected = False # a broken symlink inside our image dir

	        # request new tofile then
	        if (protected):
		    equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"Protecting config file: "+str(tofile))
		    print_warning(darkred("   ## ")+red("Protecting config file: ")+str(tofile))
		    tofile = allocateMaskedFile(tofile)
		    
	    
	        # -- CONFIGURATION FILE PROTECTION --
	
	    except:
	        pass # some files are buggy encoded

	    try:
		# this also handles symlinks
		shutil.move(fromfile,tofile)
		try:
		    packageContent.append(tofile.encode("utf-8"))
		except:
		    equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"Cannot convert filename into UTF-8, skipping: "+str(tofile))
		    print_warning(darkred("   ## ")+red("Cannot convert filename into UTF-8, skipping ")+str(tofile))
		    pass
	    except IOError,(errno,strerror):
		if errno == 2:
		    # better to pass away, sometimes gentoo packages are fucked up and contain broken things
		    pass
		else:
		    rc = os.system("mv "+fromfile+" "+tofile)
		    if (rc != 0):
		        return 4
		    packageContent.append(tofile)
	    try:
	        user = os.stat(fromfile)[4]
	        group = os.stat(fromfile)[5]
	        os.chown(tofile,user,group)
	        shutil.copystat(fromfile,tofile)
	    except:
		pass # sometimes, gentoo packages are fucked up and contain broken symlinks
	    
	    if (protected):
		# add to disk cache
		confTools.addtocache(tofile)

    # inject into database
    print_info(red("   ## ")+blue("Updating database with: ")+red(infoDict['atom']))

    installPackageIntoDatabase(infoDict['idpackage'], infoDict['repository'])

    # remove old files and gentoo stuff
    if (infoDict['removeidpackage'] != -1):
	# doing a diff removal
	equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"Remove old package: "+str(infoDict['removeatom']))
	infoDict['removeidpackage'] = -1 # disabling database removal
	if (etpConst['gentoo-compat']):
	    equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"Removing Gentoo database entry for "+str(infoDict['removeatom']))
	    print_info(red("   ## ")+blue("Cleaning old package files...")+" ## w/Gentoo compatibility")
	else:
	    print_info(red("   ## ")+blue("Cleaning old package files..."))
	removePackage(infoDict)

    clientDbconn.closeDB()


    if (etpConst['gentoo-compat']):
	equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"Installing new Gentoo database entry: "+str(infoDict['atom']))
	rc = installPackageIntoGentooDatabase(infoDict,pkgpath)
	if (rc >= 0):
	    shutil.rmtree(unpackDir,True)
	    return rc
    
    # remove unpack dir
    shutil.rmtree(unpackDir,True)
    return 0

'''
   @description: remove package entry from Gentoo database
   @input gentoo package atom (cat/name+ver):
   @output: 0 = all fine, <0 = error!
'''
def removePackageFromGentooDatabase(atom):

    if (isjustname(atom)):
	return -2

    # handle gentoo-compat
    _portage_avail = False
    try:
	from portageTools import getPortageAppDbPath as _portage_getPortageAppDbPath, getInstalledAtoms as _portage_getInstalledAtoms
	_portage_avail = True
    except:
	return -1 # no Portage support

    if (_portage_avail):
	portDbDir = _portage_getPortageAppDbPath()
	removePath = portDbDir+atom
	#print removePath
	try:
	    shutil.rmtree(removePath,True)
	except:
	    pass
	key = dep_getkey(atom)
	othersInstalled = _portage_getInstalledAtoms(key) #FIXME: really slow
	if othersInstalled == None:
	    # safest way (error free) is to use sed without loading the file
	    # escape /
	    skippedKey = ''
	    for x in key:
		if x == "/":
		    x = "\/"
		skippedKey += x
	    os.system("sed -i '/"+skippedKey+"/d' /var/lib/portage/world")

    return 0

'''
   @description: inject the database information into the Gentoo database
   @input package: dictionary containing information collected by installPackages (important are atom, slot, category, name, version)
   @output: 0 = all fine, >0 = error!
'''
def installPackageIntoGentooDatabase(infoDict,packageFile):
    
    # handle gentoo-compat
    _portage_avail = False
    try:
	from portageTools import getPackageSlot as _portage_getPackageSlot, getPortageAppDbPath as _portage_getPortageAppDbPath
	_portage_avail = True
    except:
	return -1 # no Portage support
    if (_portage_avail):
	portDbDir = _portage_getPortageAppDbPath()
	# extract xpak from unpackDir+etpConst['packagecontentdir']+"/"+package
	key = infoDict['category']+"/"+infoDict['name']
	#print _portage_getInstalledAtom(key)
	atomsfound = set()
	for xdir in os.listdir(portDbDir):
	    if (xdir == infoDict['category']):
		for ydir in os.listdir(portDbDir+"/"+xdir):
		    if (key == dep_getkey(xdir+"/"+ydir)):
			atomsfound.add(xdir+"/"+ydir)
	
	# atomsfound = _portage_getInstalledAtoms(key) too slow!
	
	### REMOVE
	# parse slot and match and remove)
	if atomsfound:
	    pkgToRemove = ''
	    for atom in atomsfound:
	        atomslot = _portage_getPackageSlot(atom)
		# get slot from gentoo db
	        if atomslot == infoDict['slot']:
		    #print "match slot, remove -> "+str(atomslot)
		    pkgToRemove = atom
		    break
	    if (pkgToRemove):
	        removePath = portDbDir+pkgToRemove
	        os.system("rm -rf "+removePath)
	        #print "removing -> "+removePath
	
	### INSTALL NEW
	extractPath = etpConst['entropyunpackdir']+"/"+os.path.basename(packageFile)+"/xpak"
	if os.path.isdir(extractPath):
	    shutil.rmtree(extractPath)
	else:
	    os.makedirs(extractPath)
        
        smartpackage = False
        if infoDict['repository'].endswith(".tbz2"):
            smartpackage = etpRepositories[infoDict['repository']]['smartpackage']
        
        if (smartpackage):
            # we need to get the .xpak from database
            xdbconn = openRepositoryDatabase(infoDict['repository'])
            xpakdata = xdbconn.retrieveXpakMetadata(infoDict['idpackage'])
            if xpakdata:
                # save into a file
                f = open(extractPath+".xpak","wb")
                f.write(xpakdata)
                f.flush()
                f.close()
                xpakstatus = unpackXpak(extractPath+".xpak",extractPath)
            else:
                xpakstatus = None
            xdbconn.closeDB()
        else:
            xpakstatus = extractXpak(packageFile,extractPath)
        if xpakstatus != None:
            if not os.path.isdir(portDbDir+infoDict['category']):
                os.makedirs(portDbDir+infoDict['category'])
            destination = portDbDir+infoDict['category']+"/"+infoDict['name']+"-"+infoDict['version']
            if os.path.isdir(destination):
                shutil.rmtree(destination)
            
            os.rename(extractPath,destination)
            
            # update counter
            if os.path.isfile("/var/cache/edb/counter"):
                # fetch number
                try:
                    f = open("/var/cache/edb/counter","r")
                    counter = int(f.readline().strip())
                    f.close()
                    # write new counter to file
                    if os.path.isfile(destination+"/"+dbCOUNTER):
                        f = open(destination+"/"+dbCOUNTER,"w")
                        f.write(str(counter)+"\n")
                        f.flush()
                        f.close()
                        counter += 1
                        f = open("/var/cache/edb/counter","w")
                        f.write(str(counter)+"\n")
                        f.flush()
                        f.close()
                except:
                    pass

    return 0

'''
   @description: injects package info into the installed packages database
   @input int(idpackage): idpackage matched into repository
   @input str(repository): name of the repository where idpackage is
   @output: 0 = all fine, >0 = error!
'''
def installPackageIntoDatabase(idpackage, repository):

    # fetch info
    dbconn = openRepositoryDatabase(repository)
    data = dbconn.getPackageData(idpackage)
    # get current revision
    rev = dbconn.retrieveRevision(idpackage)
    branch = dbconn.retrieveBranch(idpackage)
    newcontent = dbconn.retrieveContent(idpackage)
    
    exitstatus = 0
    clientDbconn = openClientDatabase()

    # load content cache
    if etpConst['collisionprotect'] > 0:
        if (not contentCache):
	    xlist = clientDbconn.listAllFiles(clean = True)
	    for x in xlist:
		contentCache[x] = 1

        # sync contentCache before install
        for x in newcontent:
	    contentCache[x] = 1
    
    dbconn.closeDB()
    
    idpk, rev, x, status = clientDbconn.handlePackage(etpData = data, forcedRevision = rev)
    del x
    if (not status):
	clientDbconn.closeDB()
	print "DEBUG!!! THIS SHOULD NOT NEVER HAPPEN. Package "+str(idpk)+" has not been inserted, status: "+str(status)
	exitstatus = 1 # it hasn't been insterted ? why??
    else: # all fine

	# regenerate contentCache
        if etpConst['collisionprotect'] > 0:
	    xlist = clientDbconn.listAllFiles(clean = True)
	    contentCache.clear()
	    for x in xlist:
		contentCache[x] = 1

        # add idpk to the installedtable
        clientDbconn.removePackageFromInstalledTable(idpk)
        clientDbconn.addPackageToInstalledTable(idpk,repository)
	# update dependstable
	try:
	    depends = clientDbconn.listIdpackageDependencies(idpk)
	    for depend in depends:
		atom = depend[1]
		iddep = depend[0]
		match = clientDbconn.atomMatch(atom)
		if (match[0] != -1):
		    clientDbconn.removeDependencyFromDependsTable(iddep)
		    clientDbconn.addDependRelationToDependsTable(iddep,match[0])

	except:
	    clientDbconn.regenerateDependsTable()

    clientDbconn.closeDB()
    return exitstatus

'''
   @description: remove the package from the installed packages database..
   		 This function is a wrapper around databaseTools.removePackage that will let us to add our custom things
   @input int(idpackage): idpackage matched into repository
   @output: 0 = all fine, >0 = error!
'''
def removePackageFromDatabase(idpackage):
    
    clientDbconn = openClientDatabase()
    # load content cache
    if etpConst['collisionprotect'] > 0:
        if (not contentCache):
	    xlist = clientDbconn.listAllFiles(clean = True)
	    for x in xlist:
		contentCache[x] = 1
        # sync contentCache before removal
        content = clientDbconn.retrieveContent(idpackage)
        for x in content:
	    try:
	        del contentCache[x]
	    except:
	        pass
    
    clientDbconn.removePackage(idpackage)
    
    clientDbconn.closeDB()
    return 0




########################################################
####
##   Database Tools
#

def package(options):

    if len(options) < 1:
	return 0

    # Options available for all the packages submodules
    myopts = options[1:]
    equoRequestAsk = False
    equoRequestPretend = False
    equoRequestPackagesCheck = False
    equoRequestVerbose = False
    equoRequestDeps = True
    equoRequestEmptyDeps = False
    equoRequestOnlyFetch = False
    equoRequestQuiet = False
    equoRequestDeep = False
    equoRequestConfigFiles = False
    equoRequestReplay = False
    equoRequestUpgrade = False
    equoRequestUpgradeTo = ''
    rc = 0
    _myopts = []
    mytbz2paths = []
    for opt in myopts:
	if (opt == "--ask"):
	    equoRequestAsk = True
	elif (opt == "--pretend"):
	    equoRequestPretend = True
	elif (opt == "--verbose"):
	    equoRequestVerbose = True
	elif (opt == "--nodeps"):
	    equoRequestDeps = False
	elif (opt == "--empty"):
	    equoRequestEmptyDeps = True
	elif (opt == "--quiet"):
	    equoRequestQuiet = True
	elif (opt == "--fetch"):
	    equoRequestOnlyFetch = True
	elif (opt == "--deep"):
	    equoRequestDeep = True
	elif (opt == "--configfiles"):
	    equoRequestConfigFiles = True
	elif (opt == "--replay"):
	    equoRequestReplay = True
	elif (opt == "--upgrade"):
	    equoRequestUpgrade = True
	else:
            if (equoRequestUpgrade):
                equoRequestUpgradeTo = opt
	    elif opt.endswith(".tbz2") and os.access(opt,os.R_OK):
		mytbz2paths.append(opt)
	    else:
	        _myopts.append(opt)
    myopts = _myopts

    if (options[0] == "deptest"):
	loadCaches()
	rc, garbage = dependenciesTest(quiet = equoRequestQuiet, ask = equoRequestAsk, pretend = equoRequestPretend)

    elif (options[0] == "install"):
	if (myopts) or (mytbz2paths):
	    loadCaches()
	    rc, status = installPackages(myopts, ask = equoRequestAsk, pretend = equoRequestPretend, verbose = equoRequestVerbose, deps = equoRequestDeps, emptydeps = equoRequestEmptyDeps, onlyfetch = equoRequestOnlyFetch, deepdeps = equoRequestDeep, configFiles = equoRequestConfigFiles, tbz2 = mytbz2paths)
	else:
	    print_error(red(" Nothing to do."))
	    rc = 127

    elif (options[0] == "world"):
	loadCaches()
	rc, status = worldUpdate(ask = equoRequestAsk, pretend = equoRequestPretend, verbose = equoRequestVerbose, onlyfetch = equoRequestOnlyFetch, replay = (equoRequestReplay or equoRequestEmptyDeps), upgradeTo = equoRequestUpgradeTo)

    elif (options[0] == "remove"):
	if len(myopts) > 0:
	    loadCaches()
	    rc, status = removePackages(myopts, ask = equoRequestAsk, pretend = equoRequestPretend, verbose = equoRequestVerbose, deps = equoRequestDeps, deep = equoRequestDeep, configFiles = equoRequestConfigFiles)
	else:
	    print_error(red(" Nothing to do."))
	    rc = 127

    return rc


def database(options):

    databaseExactMatch = False
    _options = []
    for opt in options:
	if opt == "--exact": # removed
	    databaseExactMatch = True
	else:
	    _options.append(opt)
    options = _options

    if len(options) < 1:
	return 0

    if (options[0] == "generate"):
	
	print_warning(bold("####### ATTENTION -> ")+red("The installed package database will be regenerated."))
	print_warning(bold("####### ATTENTION -> ")+red("Sabayon Linux Officially Repository MUST be on top of the repositories list in ")+etpConst['repositoriesconf'])
	print_warning(bold("####### ATTENTION -> ")+red("This method is only used for testing at the moment and you need Portage installed. Don't worry about Portage warnings."))
	print_warning(bold("####### ATTENTION -> ")+red("Please use this function ONLY if you are using an Entropy-enabled Sabayon distribution."))
	rc = askquestion("     Can I continue ?")
	if rc == "No":
	    return 0
	rc = askquestion("     Are you REALLY sure ?")
	if rc == "No":
	    return 0
	rc = askquestion("     Do you even know what you're doing ?")
	if rc == "No":
	    return 0

	# clean caches
	import cacheTools
	cacheTools.cleanCache(quiet = True)
	const_resetCache()
	
	# ok, he/she knows it... hopefully
	# if exist, copy old database
	print_info(red(" @@ ")+blue("Creating backup of the previous database, if exists.")+red(" @@"))
	newfile = backupClientDatabase()
	if (newfile):
	    print_info(red(" @@ ")+blue("Previous database copied to file ")+newfile+red(" @@"))
	
	# Now reinitialize it
	print_info(darkred("  Initializing the new database at "+bold(etpConst['etpdatabaseclientfilepath'])), back = True)
	clientDbconn = openClientDatabase(generate = True)
	clientDbconn.initializeDatabase()
	print_info(darkgreen("  Database reinitialized correctly at "+bold(etpConst['etpdatabaseclientfilepath'])))
	
	# now collect packages in the system
	from portageTools import getInstalledPackages as _portage_getInstalledPackages
	print_info(red("  Collecting installed packages..."))
	
	portagePackages = _portage_getInstalledPackages()
	portagePackages = portagePackages[0]
	
	print_info(red("  Now analyzing database content..."))

	foundPackages = []

	# do for each database
	missingPackages = portagePackages[:]
	for portagePackage in portagePackages: # for portagePackage in remainingPackages
	    print_info(red("  Analyzing ")+bold(portagePackage), back = True)
	    data = atomMatch("="+portagePackage)
	    if (data[0] != -1):
	        foundPackages.append(data)
		missingPackages.remove(portagePackage)
	
	notmatchingstatus = ''
	if len(missingPackages) > 0:
	    f = open("/tmp/equo-not-matching.txt","w")
	    for x in missingPackages:
		f.write(x+"\n")
	    f.flush()
	    f.close()
	    notmatchingstatus = " [wrote: /tmp/equo-not-matching.txt]"
	    
	
	print_info(red("  ### Packages matching: ")+bold(str(len(foundPackages))))
	print_info(red("  ### Packages not matching: ")+bold(str(len(missingPackages)))+notmatchingstatus)
	
	print_info(red("  Now filling the new database..."))
	
	count = 0
	total = str(len(foundPackages))
	
	for x in foundPackages:
	    # open its database
	    count += 1
	    dbconn = openRepositoryDatabase(x[1])
	    atomName = dbconn.retrieveAtom(x[0])
	    atomInfo = dbconn.getPackageData(x[0])
	    dbconn.closeDB()
	    # filling
	    print_info("  "+bold("(")+darkgreen(str(count))+"/"+blue(total)+bold(")")+red(" Injecting ")+bold(atomName), back = True)
	    # fill client database
	    idpk, rev, xx, status = clientDbconn.addPackage(atomInfo)
	    # now add the package to the installed table
	    clientDbconn.addPackageToInstalledTable(idpk,x[1])

	print_info(red("  Now generating depends caching table..."))
	clientDbconn.regenerateDependsTable()
	print_info(red("  Database reinitialized successfully."))

	clientDbconn.closeDB()

    elif (options[0] == "resurrect"):

	print_warning(bold("####### ATTENTION -> ")+red("The installed package database will be resurrected, this will take a LOT of time."))
	print_warning(bold("####### ATTENTION -> ")+red("Please use this function ONLY if you are using an Entropy-enabled Sabayon distribution."))
	rc = askquestion("     Can I continue ?")
	if rc == "No":
	    return 0
	rc = askquestion("     Are you REALLY sure ?")
	if rc == "No":
	    return 0
	rc = askquestion("     Do you even know what you're doing ?")
	if rc == "No":
	    return 0
	
	# clean caches
	import cacheTools
	cacheTools.cleanCache(quiet = True)
	const_resetCache()

	# ok, he/she knows it... hopefully
	# if exist, copy old database
	print_info(red(" @@ ")+blue("Creating backup of the previous database, if exists.")+red(" @@"))
	newfile = backupClientDatabase()
	if (newfile):
	    print_info(red(" @@ ")+blue("Previous database copied to file ")+newfile+red(" @@"))
	
	# Now reinitialize it
	print_info(darkred("  Initializing the new database at "+bold(etpConst['etpdatabaseclientfilepath'])), back = True)
	clientDbconn = openClientDatabase()
	clientDbconn.initializeDatabase()
	print_info(darkgreen("  Database reinitialized correctly at "+bold(etpConst['etpdatabaseclientfilepath'])))
	
	print_info(red("  Collecting installed files. Writing: "+etpConst['packagestmpfile']+" Please wait..."), back = True)
	
	# since we use find, see if it's installed
	find = os.system("which find &> /dev/null")
	if find != 0:
	    print_error(darkred("Attention: ")+red("You must have 'find' installed!"))
	    return
	# spawn process
	if os.path.isfile(etpConst['packagestmpfile']):
	    os.remove(etpConst['packagestmpfile'])
	os.system("find / -mount 1> "+etpConst['packagestmpfile'])
	if not os.path.isfile(etpConst['packagestmpfile']):
	    print_error(darkred("Attention: ")+red("find couldn't generate an output file."))
	    return
	
	f = open(etpConst['packagestmpfile'],"r")
	# creating list of files
	filelist = set()
	file = f.readline().strip()
	while file:
	    filelist.add(file)
	    file = f.readline().strip()
	f.close()
	entries = len(filelist)
	
	print_info(red("  Found "+str(entries)+" files on the system. Assigning packages..."))
	atoms = {}
	pkgsfound = set()
	
	for repo in etpRepositories:
	    print_info(red("  Matching in repository: ")+etpRepositories[repo]['description'])
	    # get all idpackages
	    dbconn = openRepositoryDatabase(repo)
	    idpackages = dbconn.listAllIdpackages(branch = etpConst['branch'])
	    count = str(len(idpackages))
	    cnt = 0
	    for idpackage in idpackages:
		cnt += 1
		idpackageatom = dbconn.retrieveAtom(idpackage)
		print_info("  ("+str(cnt)+"/"+count+")"+red(" Matching files from packages..."), back = True)
		# content
		content = dbconn.retrieveContent(idpackage)
		for file in content:
		    if file in filelist:
			pkgsfound.add((idpackage,repo))
			atoms[(idpackage,repo)] = idpackageatom
			filelist.difference_update(set(content))
			break
	    dbconn.closeDB()
	
	print_info(red("  Found "+str(len(pkgsfound))+" packages. Filling database..."))
	count = str(len(pkgsfound))
	cnt = 0
	#XXXos.remove(etpConst['packagestmpfile'])
	
	for pkgfound in pkgsfound:
	    cnt += 1
	    print_info("  ("+str(cnt)+"/"+count+") "+red("Adding: ")+atoms[pkgfound], back = True)
	    installPackageIntoDatabase(pkgfound[0],pkgfound[1])

	print_info(red("  Database resurrected successfully."))
	print_warning(red("  Keep in mind that virtual/meta packages couldn't be matched. They don't own any files."))

    elif (options[0] == "depends"):
	print_info(red("  Regenerating depends caching table..."))
	clientDbconn = openClientDatabase()
	clientDbconn.regenerateDependsTable()
	clientDbconn.closeDB()
	print_info(red("  Depends caching table regenerated successfully."))


########################################################
####
##   Actions Handling
#


def worldUpdate(ask = False, pretend = False, verbose = False, onlyfetch = False, replay = False, upgradeTo = ''):

    # check if I am root
    if (not isRoot()):
        print_warning(red("Running with ")+bold("--pretend")+red("..."))
	pretend = True

    if not pretend:
        syncRepositories()

    # verify selected release (branch)
    if (upgradeTo):
        availbranches = listAllAvailableBranches()
        if upgradeTo not in availbranches:
            print_error(red("Selected release: ")+bold(upgradeTo)+red(" is not available."))
            return 1,-2
        else:
            branches = (upgradeTo,)
    else:
        branches = (etpConst['branch'],)
    
    if (not pretend) and (upgradeTo):
        # update configuration
        writeNewBranch(upgradeTo)
    
    updateList = set()
    fineList = set()
    removedList = set()
    clientDbconn = openClientDatabase()
    # get all the installed packages
    packages = clientDbconn.listAllPackages()
    
    print_info(red(" @@ ")+blue("Calculating world packages..."))
    for package in packages:
	tainted = False
	atom = package[0]
	idpackage = package[1]
	name = clientDbconn.retrieveName(idpackage)
	category = clientDbconn.retrieveCategory(idpackage)
	revision = clientDbconn.retrieveRevision(idpackage)
	slot = clientDbconn.retrieveSlot(idpackage)
	atomkey = category+"/"+name
	# search in the packages
	match = atomMatch(atom)
	if match[0] == -1: # atom has been changed, or removed?
	    tainted = True
	else: # not changed, is the revision changed?
	    adbconn = openRepositoryDatabase(match[1])
	    arevision = adbconn.retrieveRevision(match[0])
	    adbconn.closeDB()
	    if revision != arevision:
		tainted = True
	    elif (replay):
		tainted = True
	if (tainted):
	    # Alice! use the key! ... and the slot
	    matchresults = atomMatch(atomkey, matchSlot = slot, matchBranches = branches)
	    if matchresults[0] != -1:
		mdbconn = openRepositoryDatabase(matchresults[1])
		matchatom = mdbconn.retrieveAtom(matchresults[0])
		mdbconn.closeDB()
		updateList.add((matchatom,matchresults))
	    else:
		removedList.add(idpackage)
                # look for packages that would match key with any slot (for eg, gcc updates), slot changes handling
                matchresults = atomMatch(atomkey, matchBranches = branches)
                if matchresults[0] != -1:
                    mdbconn = openRepositoryDatabase(matchresults[1])
                    matchatom = mdbconn.retrieveAtom(matchresults[0])
                    mdbconn.closeDB()
                    # compare versions
                    unsatisfied, satisfied = filterSatisfiedDependencies((matchatom,))
                    if unsatisfied:
                        updateList.add((matchatom,matchresults))
	else:
	    fineList.add(idpackage)

    if (verbose or pretend):
	print_info(red(" @@ ")+darkgreen("Packages matching update:\t\t")+bold(str(len(updateList))))
	print_info(red(" @@ ")+darkred("Packages matching not available:\t\t")+bold(str(len(removedList))))
	print_info(red(" @@ ")+blue("Packages matching already up to date:\t")+bold(str(len(fineList))))

    # disable collisions protection, better
    oldcollprotect = etpConst['collisionprotect']
    etpConst['collisionprotect'] = 0

    if (updateList):
        rc = installPackages(atomsdata = updateList, ask = ask, pretend = pretend, verbose = verbose, onlyfetch = onlyfetch)
	if rc[0] != 0:
	    return rc
    else:
	print_info(red(" @@ ")+blue("Nothing to update."))

    

    etpConst['collisionprotect'] = oldcollprotect

    if (removedList):
	removedList = list(removedList)
	removedList.sort()
	print_info(red(" @@ ")+blue("On the system there are packages that are not available anymore in the online repositories."))
	print_info(red(" @@ ")+blue("Even if they are usually harmless, it is suggested to remove them."))
	
	if (not pretend):
	    if (ask):
	        rc = askquestion("     Would you like to query them ?")
	        if rc == "No":
		    clientDbconn.closeDB()
		    return 0,0
	    else:
		print_info(red(" @@ ")+blue("Running query in ")+red("5 seconds")+blue("..."))
		print_info(red(" @@ ")+blue(":: Hit CTRL+C to stop"))
		import time
	        time.sleep(5)
	
	    # run removePackages with --nodeps
	    removePackages(atomsdata = removedList, ask = ask, verbose = verbose, deps = False, systemPackagesCheck = False, configFiles = True)
	else:
	    print_info(red(" @@ ")+blue("Calculation complete."))

    else:
	print_info(red(" @@ ")+blue("Nothing to remove."))

    clientDbconn.closeDB()
    return 0,0

def installPackages(packages = [], atomsdata = [], ask = False, pretend = False, verbose = False, deps = True, emptydeps = False, onlyfetch = False, deepdeps = False, configFiles = False, tbz2 = []):

    # check if I am root
    if (not isRoot()):
        print_warning(red("Running with ")+bold("--pretend")+red("..."))
	pretend = True
    
    dirsCleanup = set()
    def dirscleanup():
	for x in dirsCleanup:
	    try:
	        if os.path.isdir(x): shutil.rmtree(x)
	    except:
		pass
    if (atomsdata):
	foundAtoms = atomsdata
    else:
        foundAtoms = []
        for package in packages:
	    foundAtoms.append([package,atomMatch(package)])
	if tbz2:
	    for pkg in tbz2:
	        # create a repository for each database
	        basefile = os.path.basename(pkg)
	        if os.path.isdir(etpConst['entropyunpackdir']+"/"+basefile[:-5]):
		    shutil.rmtree(etpConst['entropyunpackdir']+"/"+basefile[:-5])
	        os.makedirs(etpConst['entropyunpackdir']+"/"+basefile[:-5])
	        dbfile = extractEdb(pkg,dbpath = etpConst['entropyunpackdir']+"/"+basefile[:-5]+"/packages.db")
                if dbfile == None:
                    print_warning(red("## ATTENTION:")+bold(" "+basefile+" ")+red(" is not a valid Entropy package. Skipping..."))
                    continue
		dirsCleanup.add(os.path.dirname(dbfile))
	        # add dbfile
	        etpRepositories[basefile] = {}
	        etpRepositories[basefile]['description'] = "Dynamic database from "+basefile
	        etpRepositories[basefile]['packages'] = []
	        etpRepositories[basefile]['dbpath'] = os.path.dirname(dbfile)
	        etpRepositories[basefile]['pkgpath'] = os.path.realpath(pkg) # extra info added
	        etpRepositories[basefile]['configprotect'] = set()
	        etpRepositories[basefile]['configprotectmask'] = set()
                etpRepositories[basefile]['smartpackage'] = False # extra info added
	        mydbconn = openGenericDatabase(dbfile)
	        # read all idpackages
	        myidpackages = mydbconn.listAllIdpackages() # all branches admitted from external files
                if len(myidpackages) > 1:
                    etpRepositories[basefile]['smartpackage'] = True
	        for myidpackage in myidpackages:
                    foundAtoms.append([pkg,(int(myidpackage),basefile)])
                mydbconn.closeDB()

    # filter packages not found
    _foundAtoms = []
    for result in foundAtoms:
	exitcode = result[1][0]
	if (exitcode != -1):
	    _foundAtoms.append(result[1])
	else:
	    print_warning(red("## ATTENTION: no match for ")+bold(" "+result[0]+" ")+red(" in database. If you omitted the category, try adding it."))

    foundAtoms = _foundAtoms
    
    # are packages in foundAtoms?
    if (not foundAtoms):
	print_error(red("No packages found"))
        dirscleanup()
	return 127,-1

    if (ask or pretend or verbose):
        # now print the selected packages
        print_info(red(" @@ ")+blue("These are the chosen packages:"))
        totalatoms = len(foundAtoms)
        atomscounter = 0
        for atomInfo in foundAtoms:
	    atomscounter += 1
	    idpackage = atomInfo[0]
	    reponame = atomInfo[1]
	    # open database
	    dbconn = openRepositoryDatabase(reponame)

	    # get needed info
	    pkgatom = dbconn.retrieveAtom(idpackage)
	    pkgver = dbconn.retrieveVersion(idpackage)
	    pkgtag = dbconn.retrieveVersionTag(idpackage)
	    if not pkgtag:
	        pkgtag = "NoTag"
	    pkgrev = dbconn.retrieveRevision(idpackage)
	    pkgslot = dbconn.retrieveSlot(idpackage)
	
	    # client info
	    installedVer = "Not installed"
	    installedTag = "NoTag"
	    installedRev = "NoRev"
	    clientDbconn = openClientDatabase()
	    if (clientDbconn != -1):
	        pkginstalled = clientDbconn.atomMatch(dep_getkey(pkgatom), matchSlot = pkgslot)
	        if (pkginstalled[1] == 0):
	            # found
		    idx = pkginstalled[0]
		    installedVer = clientDbconn.retrieveVersion(idx)
		    installedTag = clientDbconn.retrieveVersionTag(idx)
		    if not installedTag:
			installedTag = "NoTag"
		    installedRev = clientDbconn.retrieveRevision(idx)
		clientDbconn.closeDB()

	    print_info("   # "+red("(")+bold(str(atomscounter))+"/"+blue(str(totalatoms))+red(")")+" "+bold(pkgatom)+" >>> "+red(etpRepositories[reponame]['description']))
	    print_info("\t"+red("Versioning:\t")+" "+blue(installedVer)+" / "+blue(installedTag)+" / "+blue(str(installedRev))+bold(" ===> ")+darkgreen(pkgver)+" / "+darkgreen(pkgtag)+" / "+darkgreen(str(pkgrev)))
	    # tell wether we should update it
	    if installedVer == "Not installed":
	        installedVer = "0"
	    if installedTag == "NoTag":
	        installedTag == ''
	    if installedRev == "NoRev":
	        installedRev == 0
	    cmp = compareVersions((pkgver,pkgtag,pkgrev),(installedVer,installedTag,installedRev))
	    if (cmp == 0):
	        action = darkgreen("No update needed")
	    elif (cmp > 0):
	        if (installedVer == "0"):
		    action = darkgreen("Install")
	        else:
	            action = blue("Upgrade")
	    else:
	        action = red("Downgrade")
	    print_info("\t"+red("Action:\t\t")+" "+action)
	
	    dbconn.closeDB()

	if (verbose or ask or pretend):
            print_info(red(" @@ ")+blue("Number of packages: ")+str(totalatoms))
    
        if (deps):
            if (ask):
                rc = askquestion("     Would you like to continue with dependencies calculation ?")
                if rc == "No":
                    dirscleanup()
	            return 0,0

    runQueue = []
    removalQueue = [] # aka, conflicts
    
    print_info(red(" @@ ")+blue("Calculating dependencies..."))

    if (deps):
        treepackages, result = getRequiredPackages(foundAtoms, emptydeps, deepdeps, spinning = True)
        # add dependencies, explode them
	
	if (result == -2):
	    print_error(red(" @@ ")+blue("Cannot find needed dependencies: ")+str(treepackages))
	    for atom in treepackages:
		for repo in etpRepositories:
		    rdbconn = openRepositoryDatabase(repo)
		    riddep = rdbconn.searchDependency(atom)
		    if riddep != -1:
		        ridpackages = rdbconn.searchIdpackageFromIddependency(riddep)
			if ridpackages:
			    print_error(red(" @@ ")+blue("Dependency found and probably needed by:"))
			for i in ridpackages:
			    iatom = rdbconn.retrieveAtom(i)
			    print_error(red("     # ")+" [from:"+repo+"] "+darkred(iatom))
		    rdbconn.closeDB()
            dirscleanup()
	    return 130, -1
	    
	elif (result == -1): # no database connection
	    print_error(red(" @@ ")+blue("Cannot find the Installed Packages Database. It's needed to accomplish dependency resolving. Try to run ")+bold("equo database generate"))
            dirscleanup()
	    return 200, -1
	
	for x in range(len(treepackages)):
	    if x == 0:
		# conflicts
		for a in treepackages[x]:
		    removalQueue.append(a)
	    else:
		for a in treepackages[x]:
		    runQueue.append(a)
	
    else:
	for atomInfo in foundAtoms:
	    runQueue.append(atomInfo)

    downloadSize = 0
    onDiskUsedSize = 0
    onDiskFreedSize = 0
    pkgsToInstall = 0
    pkgsToUpdate = 0
    pkgsToReinstall = 0
    pkgsToDowngrade = 0
    pkgsToRemove = len(removalQueue)
    actionQueue = {}

    if (not runQueue) and (not removalQueue):
	print_error(red("Nothing to do."))
        dirscleanup()
	return 127,-1

    if (runQueue):
	if (ask or pretend):
	    print_info(red(" @@ ")+blue("These are the packages that would be ")+bold("merged:"))
	
	if not (ask or pretend): count = 0
	atomlen = len(runQueue)
	for packageInfo in runQueue:
	    if not (ask or pretend): count += 1; print_info(":: Collecting data: "+str(round((float(count)/atomlen)*100,1))+"% ::", back = True)
	    dbconn = openRepositoryDatabase(packageInfo[1])
	    mydata = dbconn.getBaseData(packageInfo[0])
	    pkgatom = mydata[0]
	    pkgver = mydata[2]
	    pkgtag = mydata[3]
	    pkgrev = mydata[18]
	    pkgslot = mydata[14]
	    pkgdigest = mydata[13]
	    pkgfile = mydata[12]
	    pkgcat = mydata[5]
	    pkgname = mydata[1]
            pkgtrigger = dbconn.retrieveTrigger(packageInfo[0])
	    pkgmessages = dbconn.retrieveMessages(packageInfo[0]) # still new
	    onDiskUsedSize += dbconn.retrieveOnDiskSize(packageInfo[0]) # still new
	    
	    # fill action queue
	    actionQueue[pkgatom] = {}
	    actionQueue[pkgatom]['repository'] = packageInfo[1]
	    actionQueue[pkgatom]['idpackage'] = packageInfo[0]
	    actionQueue[pkgatom]['slot'] = pkgslot
	    actionQueue[pkgatom]['atom'] = pkgatom
	    actionQueue[pkgatom]['version'] = pkgver
	    actionQueue[pkgatom]['category'] = pkgcat
	    actionQueue[pkgatom]['name'] = pkgname
	    actionQueue[pkgatom]['removeidpackage'] = -1
	    actionQueue[pkgatom]['download'] = pkgfile
	    actionQueue[pkgatom]['checksum'] = pkgdigest
	    actionQueue[pkgatom]['messages'] = pkgmessages
	    actionQueue[pkgatom]['removeconfig'] = configFiles
	    dl = checkNeededDownload(pkgfile, None) # we'll do a good check during installPackage
	    actionQueue[pkgatom]['fetch'] = dl
	    if dl < 0:
		pkgsize = dbconn.retrieveSize(packageInfo[0])
		downloadSize += int(pkgsize)
	
	    # get installed package data
	    installedVer = '0'
	    installedTag = ''
	    installedRev = 0
	    clientDbconn = openClientDatabase()
            if (clientDbconn != -1):
                pkginstalled = clientDbconn.atomMatch(dep_getkey(pkgatom), matchSlot = pkgslot)
                if (pkginstalled[1] == 0):
	            # found
		    idx = pkginstalled[0]
		    installedVer = clientDbconn.retrieveVersion(idx)
		    installedTag = clientDbconn.retrieveVersionTag(idx)
		    installedRev = clientDbconn.retrieveRevision(idx)
		    actionQueue[pkgatom]['removeidpackage'] = idx
		    actionQueue[pkgatom]['removeatom'] = clientDbconn.retrieveAtom(idx)
		    actionQueue[pkgatom]['removecontent'] = clientDbconn.retrieveAtom(idx)
		    onDiskFreedSize += clientDbconn.retrieveOnDiskSize(idx)
	        clientDbconn.closeDB()

	    if not (ask or pretend or verbose):
		continue

	    action = 0
	    flags = " ["
	    cmp = compareVersions([pkgver,pkgtag,pkgrev],[installedVer,installedTag,installedRev])
	    if (cmp == 0):
		pkgsToReinstall += 1
		actionQueue[pkgatom]['removeidpackage'] = -1 # disable removal, not needed
	        flags += red("R")
		action = 1
	    elif (cmp > 0):
	        if (installedVer == "0"):
		    pkgsToInstall += 1
		    actionQueue[pkgatom]['removeidpackage'] = -1 # disable removal, not needed
	            flags += darkgreen("N")
	        else:
		    pkgsToUpdate += 1
		    flags += blue("U")
		    action = 2
	    else:
		pkgsToDowngrade += 1
	        flags += darkblue("D")
		action = -1
	    flags += "] "

	    # disable removal for packages already in removalQueue
	    if actionQueue[pkgatom]['removeidpackage'] in removalQueue:
		actionQueue[pkgatom]['removeidpackage'] = -1

	    repoinfo = red("[")+bold(packageInfo[1])+red("] ")
	    oldinfo = ''
	    if action != 0:
		oldinfo = "   ["+blue(installedVer)+"/"+red(str(installedRev))
		oldtag = "]"
		if installedTag:
		    oldtag = "/"+darkred(installedTag)+oldtag
		oldinfo += oldtag

	    print_info(darkred(" ##")+flags+repoinfo+enlightenatom(str(pkgatom))+"/"+str(pkgrev)+oldinfo)
	    dbconn.closeDB()

    if (removalQueue):
        
        # add depends to removalQueue that are not in runQueue
        clientDbconn = openClientDatabase()
        dependQueue = set()
        for idpackage in removalQueue:
            depends = clientDbconn.retrieveDepends(idpackage)
            if depends == -2:
                clientDbconn.regenerateDependsTable(output = False)
                depends = clientDbconn.retrieveDepends(idpackage)
            for depend in depends:
                dependkey = clientDbconn.retrieveCategory(depend)+"/"+clientDbconn.retrieveName(depend)
                dependslot = clientDbconn.retrieveSlot(depend)
                # match in repositories
                match = atomMatch(dependkey, matchSlot = dependslot)
                if match[0] != -1:
                    matchdbconn = openRepositoryDatabase(match[1])
                    matchatom = matchdbconn.retrieveAtom(match[0])
                    matchdbconn.closeDB()
                    if (matchatom not in actionQueue) and (depend not in removalQueue): # if the atom hasn't been pulled in, we need to remove depend
                        dependQueue.add(depend)
        for depend in dependQueue:
            removalQueue.append(depend)
        
	if (ask or pretend or verbose):
	    print_info(red(" @@ ")+blue("These are the packages that would be ")+bold("removed")+blue(" (substituted):"))

	    for idpackage in removalQueue:
	        pkgatom = clientDbconn.retrieveAtom(idpackage)
	        onDiskFreedSize += clientDbconn.retrieveOnDiskSize(idpackage)
	        installedfrom = clientDbconn.retrievePackageFromInstalledTable(idpackage)
		repoinfo = red("[")+brown("from: ")+bold(installedfrom)+red("] ")
	        print_info(red("   ## ")+"["+red("W")+"] "+repoinfo+enlightenatom(pkgatom))

	clientDbconn.closeDB()
    
    if (runQueue) or (removalQueue):
	# show download info
	print_info(red(" @@ ")+blue("Packages needing install:\t")+red(str(len(runQueue))))
	print_info(red(" @@ ")+blue("Packages needing removal:\t")+red(str(pkgsToRemove)))
	if (ask or verbose or pretend):
	    print_info(red(" @@ ")+darkgreen("Packages needing install:\t")+darkgreen(str(pkgsToInstall)))
	    print_info(red(" @@ ")+darkgreen("Packages needing reinstall:\t")+darkgreen(str(pkgsToReinstall)))
	    print_info(red(" @@ ")+blue("Packages needing update:\t\t")+blue(str(pkgsToUpdate)))
	    print_info(red(" @@ ")+red("Packages needing downgrade:\t")+red(str(pkgsToDowngrade)))
	print_info(red(" @@ ")+blue("Download size:\t\t\t")+bold(str(bytesIntoHuman(downloadSize))))
	deltaSize = onDiskUsedSize - onDiskFreedSize
	if (deltaSize > 0):
	    print_info(red(" @@ ")+blue("Used disk space:\t\t\t")+bold(str(bytesIntoHuman(deltaSize))))
	else:
	    print_info(red(" @@ ")+blue("Freed disk space:\t\t")+bold(str(bytesIntoHuman(abs(deltaSize)))))


    if (ask):
        rc = askquestion("     Would you like to run the queue ?")
        if rc == "No":
            dirscleanup()
	    return 0,0
    if (pretend):
        dirscleanup()
	return 0,0
    
    # running tasks
    totalqueue = str(len(runQueue))
    totalremovalqueue = str(len(removalQueue))
    currentqueue = 0
    currentremovalqueue = 0
    clientDbconn = openClientDatabase()
    
    for idpackage in removalQueue:
        currentremovalqueue += 1
	infoDict = {}
	infoDict['removeatom'] = clientDbconn.retrieveAtom(idpackage)
	infoDict['removecontent'] = clientDbconn.retrieveContent(idpackage)
	infoDict['removeidpackage'] = idpackage
	infoDict['diffremoval'] = False
	infoDict['removeconfig'] = True # we need to completely wipe configuration of conflicts
	etpRemovalTriggers[infoDict['removeatom']] = clientDbconn.getPackageData(idpackage)
	etpRemovalTriggers[infoDict['removeatom']]['removecontent'] = infoDict['removecontent'].copy()
	etpRemovalTriggers[infoDict['removeatom']]['trigger'] = clientDbconn.retrieveTrigger(idpackage)
	steps = []
	steps.append("preremove")
	steps.append("remove")
	steps.append("postremove")
	for step in steps:
	    rc = stepExecutor(step,infoDict,str(currentremovalqueue)+"/"+totalremovalqueue)
	    if (rc != 0):
		clientDbconn.closeDB()
                dirscleanup()
		return -1,rc
    
    for packageInfo in runQueue:
	currentqueue += 1
	idpackage = packageInfo[0]
	repository = packageInfo[1]
	# get package atom
	dbconn = openRepositoryDatabase(repository)
	pkgatom = dbconn.retrieveAtom(idpackage)

	steps = []
	# download
	if not repository.endswith(".tbz2"):
	    if (actionQueue[pkgatom]['fetch'] < 0):
	        steps.append("fetch")
	    steps.append("checksum")
	
	# differential remove list
	if (actionQueue[pkgatom]['removeidpackage'] != -1):
            # is it still available?
            if clientDbconn.isIDPackageAvailable(actionQueue[pkgatom]['removeidpackage']):
                oldcontent = clientDbconn.retrieveContent(actionQueue[pkgatom]['removeidpackage'])
                newcontent = dbconn.retrieveContent(idpackage)
                oldcontent.difference_update(newcontent)
                actionQueue[pkgatom]['removecontent'] = oldcontent
                actionQueue[pkgatom]['diffremoval'] = True
                etpRemovalTriggers[pkgatom] = clientDbconn.getPackageData(actionQueue[pkgatom]['removeidpackage'])
                etpRemovalTriggers[pkgatom]['removecontent'] = actionQueue[pkgatom]['removecontent'].copy()
                etpRemovalTriggers[pkgatom]['trigger'] = clientDbconn.retrieveTrigger(actionQueue[pkgatom]['removeidpackage'])
            else:
                actionQueue[pkgatom]['removeidpackage'] = -1

	# get data for triggerring tool
	etpInstallTriggers[pkgatom] = dbconn.getPackageData(idpackage)
        etpInstallTriggers[pkgatom]['trigger'] = dbconn.retrieveTrigger(idpackage)

	dbconn.closeDB()

	if (not onlyfetch):
	    # install
	    if (actionQueue[pkgatom]['removeidpackage'] != -1):
		steps.append("preremove")
	    steps.append("preinstall")
	    steps.append("install")
	    if (actionQueue[pkgatom]['removeidpackage'] != -1):
		steps.append("postremove")
	    steps.append("postinstall")
	    steps.append("showmessages")
	
	#print "steps for "+pkgatom+" -> "+str(steps)
        
	print_info(red(" @@ ")+bold("(")+blue(str(currentqueue))+"/"+red(totalqueue)+bold(") ")+">>> "+darkgreen(pkgatom))
	
	for step in steps:
	    rc = stepExecutor(step,actionQueue[pkgatom],str(currentqueue)+"/"+totalqueue)
	    if (rc != 0):
		clientDbconn.closeDB()
                dirscleanup()
		return -1,rc

    if (onlyfetch):
	print_info(red(" @@ ")+blue("Fetch Complete."))
    else:
	print_info(red(" @@ ")+blue("Install Complete."))

    clientDbconn.closeDB()

    dirscleanup()
    return 0,0


def removePackages(packages = [], atomsdata = [], ask = False, pretend = False, verbose = False, deps = True, deep = False, systemPackagesCheck = True, configFiles = False):
    
    # check if I am root
    if (not isRoot()):
        print_warning(red("Running with ")+bold("--pretend")+red("..."))
	pretend = True

    clientDbconn = openClientDatabase()

    foundAtoms = []
    if (atomsdata):
	for idpackage in atomsdata:
	    foundAtoms.append([clientDbconn.retrieveAtom(idpackage),(idpackage,0)])
    else:
	for package in packages:
	    foundAtoms.append([package,clientDbconn.atomMatch(package)])

    # filter packages not found
    _foundAtoms = []
    for result in foundAtoms:
	exitcode = result[1][0]
	if (exitcode != -1):
	    _foundAtoms.append(result[1])
	else:
	    print_warning(red("## ATTENTION -> package")+bold(" "+result[0]+" ")+red("is not installed."))

    foundAtoms = _foundAtoms
    
    # are packages in foundAtoms?
    if (len(foundAtoms) == 0):
	print_error(red("No packages found"))
	return 127,-1

    plainRemovalQueue = []
    
    lookForOrphanedPackages = True
    # now print the selected packages
    print_info(red(" @@ ")+blue("These are the chosen packages:"))
    totalatoms = len(foundAtoms)
    atomscounter = 0
    for atomInfo in foundAtoms:
	atomscounter += 1
	idpackage = atomInfo[0]
	systemPackage = clientDbconn.isSystemPackage(idpackage)

	# get needed info
	pkgatom = clientDbconn.retrieveAtom(idpackage)
	installedfrom = clientDbconn.retrievePackageFromInstalledTable(idpackage)

	if (systemPackage) and (systemPackagesCheck):
	    # check if the package is slotted and exist more than one installed first
	    sysresults = clientDbconn.atomMatch(dep_getkey(pkgatom), multiMatch = True)
	    slots = set()
	    if sysresults[1] == 0:
	        for x in sysresults[0]:
		    slots.add(clientDbconn.retrieveSlot(x))
		if len(slots) < 2:
	            print_warning(darkred("   # !!! ")+red("(")+brown(str(atomscounter))+"/"+blue(str(totalatoms))+red(")")+" "+enlightenatom(pkgatom)+red(" is a vital package. Removal forbidden."))
		    continue
	    else:
	        print_warning(darkred("   # !!! ")+red("(")+brown(str(atomscounter))+"/"+blue(str(totalatoms))+red(")")+" "+enlightenatom(pkgatom)+red(" is a vital package. Removal forbidden."))
	        continue
	plainRemovalQueue.append(idpackage)
	
	print_info("   # "+red("(")+brown(str(atomscounter))+"/"+blue(str(totalatoms))+red(")")+" "+enlightenatom(pkgatom)+" | Installed from: "+red(installedfrom))

    if (verbose or ask or pretend):
        print_info(red(" @@ ")+blue("Number of packages: ")+str(totalatoms))
    
    if (deps):
	question = "     Would you like to look for packages that can be removed along with the selected above?"
    else:
	question = "     Would you like to remove them now?"
	lookForOrphanedPackages = False

    if (ask):
        rc = askquestion(question)
        if rc == "No":
	    if (not deps):
	        clientDbconn.closeDB()
		return 0,0

    if (not plainRemovalQueue):
	print_error(red("Nothing to do."))
	return 127,-1

    removalQueue = []
    
    if (lookForOrphanedPackages):
	choosenRemovalQueue = []
	print_info(red(" @@ ")+blue("Calculating removal dependencies, please wait..."))
	treeview = generateDependsTree(plainRemovalQueue, deep = deep)
	treelength = len(treeview[0])
	if treelength > 1:
	    treeview = treeview[0]
	    for x in range(treelength)[::-1]:
		for y in treeview[x]:
		    choosenRemovalQueue.append(y)
	
	    if (choosenRemovalQueue):
	        print_info(red(" @@ ")+blue("These are the packages that would added to the removal queue:"))
	        totalatoms = str(len(choosenRemovalQueue))
	        atomscounter = 0
	    
	        for idpackage in choosenRemovalQueue:
	            atomscounter += 1
	            rematom = clientDbconn.retrieveAtom(idpackage)
	            installedfrom = clientDbconn.retrievePackageFromInstalledTable(idpackage)
		    repositoryInfo = bold("[")+red("from: ")+brown(installedfrom)+bold("]")
		    stratomscounter = str(atomscounter)
		    while len(stratomscounter) < len(totalatoms):
			stratomscounter = " "+stratomscounter
	            print_info("   # "+red("(")+bold(stratomscounter)+"/"+blue(str(totalatoms))+red(")")+repositoryInfo+" "+blue(rematom))
	    
                if (ask):
                    rc = askquestion("     Would you like to add these packages to the removal queue?")
                    if rc != "No":
			print_info(red(" @@ ")+blue("Removal Queue updated."))
	                for x in choosenRemovalQueue:
			    removalQueue.append(x)
		else:
	            for x in choosenRemovalQueue:
			removalQueue.append(x)
	    else:
		print

    if (ask):
	if (deps):
	    print
            rc = askquestion("     I am going to start the removal. Are you sure?")
            if rc == "No":
	        clientDbconn.closeDB()
	        return 0,0
    else:
	countdown(what = red(" @@ ")+blue("Starting removal in "),back = True)
	

    for idpackage in plainRemovalQueue:
	removalQueue.append(idpackage)
    
    currentqueue = 0
    for idpackage in removalQueue:
        currentqueue += 1
	infoDict = {}
	infoDict['removeidpackage'] = idpackage
	infoDict['removeatom'] = clientDbconn.retrieveAtom(idpackage)
	infoDict['removecontent'] = clientDbconn.retrieveContent(idpackage)
	infoDict['diffremoval'] = False
	infoDict['removeconfig'] = configFiles
	etpRemovalTriggers[infoDict['removeatom']] = clientDbconn.getPackageData(idpackage)
	etpRemovalTriggers[infoDict['removeatom']]['removecontent'] = infoDict['removecontent'].copy()
	etpRemovalTriggers[infoDict['removeatom']]['trigger'] = clientDbconn.retrieveTrigger(idpackage)
	steps = []
	steps.append("preremove")
	steps.append("remove")
	steps.append("postremove")
	for step in steps:
	    rc = stepExecutor(step,infoDict,str(currentqueue)+"/"+str(len(removalQueue)))
	    if (rc != 0):
		clientDbconn.closeDB()
		return -1,rc
    
    print_info(red(" @@ ")+blue("All done."))
    
    clientDbconn.closeDB()
    return 0,0


def dependenciesTest(quiet = False, ask = False, pretend = False):
    
    if (not quiet):
        print_info(red(" @@ ")+blue("Running dependency test..."))
    
    clientDbconn = openClientDatabase()
    # get all the installed packages
    installedPackages = clientDbconn.listAllIdpackages()
    
    depsNotFound = {}
    depsNotSatisfied = {}
    # now look
    length = str((len(installedPackages)))
    count = 0
    for xidpackage in installedPackages:
	count += 1
	atom = clientDbconn.retrieveAtom(xidpackage)
	if (not quiet):
	    print_info(darkred(" @@ ")+bold("(")+blue(str(count))+"/"+red(length)+bold(")")+darkgreen(" Checking ")+bold(atom), back = True)
	deptree, status = generateDependencyTree((xidpackage,0))

	if (status == 0):
	    # skip conflicts
	    conflicts = deptree.get(0,None)
	    if (conflicts):
	        deptree[0] = []

	    depsNotSatisfied[xidpackage] = []
	    for x in deptree:
	        for z in deptree[x]:
		    depsNotSatisfied[xidpackage].append(z)
	    if (not depsNotSatisfied[xidpackage]):
		del depsNotSatisfied[xidpackage]
	
    packagesNeeded = []
    if (depsNotSatisfied):
        if (not quiet):
            print_info(red(" @@ ")+blue("These are the packages that lack dependencies: "))
	for dict in depsNotSatisfied:
	    pkgatom = clientDbconn.retrieveAtom(dict)
	    if (not quiet):
	        print_info(darkred("   ### ")+blue(pkgatom))
	    for dep in depsNotSatisfied[dict]:
		iddep = dep[0]
		repo = dep[1]
		dbconn = openRepositoryDatabase(repo)
		depatom = dbconn.retrieveAtom(iddep)
		dbconn.closeDB()
		if (not quiet):
		    print_info(bold("       :: ")+red(depatom))
		else:
		    print pkgatom+" -> "+depatom
		packagesNeeded.append([depatom,dep])

    if (pretend):
	clientDbconn.closeDB()
	return 0, packagesNeeded

    if (packagesNeeded) and (not quiet):
        if (ask):
            rc = askquestion("     Would you like to install them?")
            if rc == "No":
		clientDbconn.closeDB()
	        return 0,packagesNeeded
	else:
	    print_info(red(" @@ ")+blue("Installing dependencies in ")+red("10 seconds")+blue("..."))
	    import time
	    time.sleep(10)
	# install them
	packages = []
	for dep in packagesNeeded:
	    packages.append(dep[0])
	
	# check for equo.pid
	packages = filterDuplicatedEntries(packages)
	applicationLockCheck("install")
	installPackages(packages, deps = False, ask = ask)
	    

    print_info(red(" @@ ")+blue("All done."))
    clientDbconn.closeDB()
    return 0,packagesNeeded

'''
    @description: execute the requested step (it is only used by the CLI client)
    @input: 	step -> name of the step to execute
    		infoDict -> dictionary containing all the needed information collected by installPackages() -> actionQueue[pkgatom]
                loopString -> used to print to xterm title bar something like "10/900 - equo"
    @output:	-1,"description" for error ; 0,True for no errors
'''
def stepExecutor(step,infoDict, loopString = None):

    clientDbconn = openClientDatabase()
    output = 0
    
    if step == "fetch":
	print_info(red("   ## ")+blue("Fetching archive: ")+red(os.path.basename(infoDict['download'])))
        xtermTitle(loopString+' Fetching archive: '+os.path.basename(infoDict['download']))
	output = fetchFileOnMirrors(infoDict['repository'],infoDict['download'],infoDict['checksum'])
	if output < 0:
	    print_error(red("Package cannot be fetched. Try to run: '")+bold("equo update")+red("' and this command again. Error "+str(output)))
    
    elif step == "checksum":
	output = matchChecksum(infoDict)
    
    elif step == "install":
        compatstring = ''
	if (etpConst['gentoo-compat']):
            compatstring = " ## w/Gentoo compatibility"
	print_info(red("   ## ")+blue("Installing package: ")+red(os.path.basename(infoDict['atom']))+compatstring)
        xtermTitle(loopString+' Installing package: '+os.path.basename(infoDict['atom'])+compatstring)
	output = installPackage(infoDict)
	if output != 0:
	    if output == 512:
	        errormsg = red("You are running out of disk space. I bet, you're probably Michele. Error 512")
	    else:
	        errormsg = red("An error occured while trying to install the package. Check if your hard disk is healthy. Error "+str(output))
	    print_error(errormsg)
    
    elif step == "remove":
	gcompat = ""
	if (etpConst['gentoo-compat']):
	    gcompat = " ## w/Gentoo compatibility"
	print_info(red("   ## ")+blue("Removing installed package: ")+red(infoDict['removeatom'])+gcompat)
        xtermTitle(loopString+' Removing installed package: '+os.path.basename(infoDict['removeatom'])+gcompat)
	output = removePackage(infoDict)
	if output != 0:
	    errormsg = red("An error occured while trying to remove the package. Check if you have enough disk space on your hard disk. Error "+str(output))
	    print_error(errormsg)
    
    elif step == "showmessages":
	# get messages
	if infoDict['messages']:
	    equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"Message from "+infoDict['atom']+" :")
	for msg in infoDict['messages']:
	    equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,msg)
	    print_warning(brown('   ## ')+msg)
	if infoDict['messages']:
	    equoLog.log(ETP_LOGPRI_INFO,ETP_LOGLEVEL_NORMAL,"End message.")
    
    elif step == "postinstall":
	# analyze atom
	pkgdata = etpInstallTriggers.get(infoDict['atom'])
	if pkgdata:
	    triggers = triggerTools.postinstall(pkgdata)
	    for trigger in triggers: # code reuse, we'll fetch triggers list on the GUI client and run each trigger by itself
		eval("triggerTools."+trigger)(pkgdata)

    elif step == "preinstall":
	# analyze atom
	pkgdata = etpInstallTriggers.get(infoDict['atom'])
	if pkgdata:
	    triggers = triggerTools.preinstall(pkgdata)
	    for trigger in triggers: # code reuse, we'll fetch triggers list on the GUI client and run each trigger by itself
		eval("triggerTools."+trigger)(pkgdata)

    elif step == "preremove":
	# analyze atom
	remdata = etpRemovalTriggers.get(infoDict['removeatom'])
	if remdata:
	    triggers = triggerTools.preremove(remdata)

	    if infoDict['diffremoval']: # diffremoval is true only when the remove action is triggered by installPackages()
		pkgdata = etpRemovalTriggers.get(infoDict['atom'])
		if pkgdata:
	            # preinstall script shouldn't doulbe run on preremove
		    itriggers = triggerTools.preinstall(pkgdata)
		    triggers.difference_update(itriggers)

	    for trigger in triggers: # code reuse, we'll fetch triggers list on the GUI client and run each trigger by itself
		eval("triggerTools."+trigger)(remdata)

    elif step == "postremove":
	# analyze atom
	remdata = etpRemovalTriggers.get(infoDict['removeatom'])
	if remdata:
	    triggers = triggerTools.postremove(remdata)
	    
	    if infoDict['diffremoval']: # diffremoval is true only when the remove action is triggered by installPackages()
		pkgdata = etpRemovalTriggers.get(infoDict['atom'])
		if pkgdata:
	            # postinstall script shouldn't doulbe run on postremove
		    itriggers = triggerTools.postinstall(pkgdata)
		    triggers.difference_update(itriggers)
	    
	    for trigger in triggers: # code reuse, we'll fetch triggers list on the GUI client and run each trigger by itself
		eval("triggerTools."+trigger)(remdata)
    
    clientDbconn.closeDB()
    
    return output


'''
    @description: prints entropy configuration information
    @input: dict (bool) -> if True, returns a dictionary with packed info. if False, just print to STDOUT
    @output:	dictionary or STDOUT
'''
def getinfo(dict = False):
    # sysinfo
    info = {}
    osinfo = os.uname()
    info['OS'] = osinfo[0]
    info['Kernel'] = osinfo[2]
    info['Architecture'] = osinfo[4]
    info['Entropy version'] = etpConst['entropyversion']
    
    # variables
    info['User protected directories'] = etpConst['configprotect']
    info['Collision Protection'] = etpConst['collisionprotect']
    info['Gentoo Compatibility'] = etpConst['gentoo-compat']
    info['Equo Log Level'] = etpConst['equologlevel']
    info['Database Log Level'] = etpConst['databaseloglevel']
    info['entropyTools Log Level'] = etpConst['entropyloglevel']
    info['remoteTools Log Level'] = etpConst['remoteloglevel']
    info['Current branch'] = etpConst['branch']
    info['Available branches'] = etpConst['branches']
    info['Entropy configuration directory'] = etpConst['confdir']
    info['Entropy work directory'] = etpConst['entropyworkdir']
    info['Entropy unpack directory'] = etpConst['entropyunpackdir']
    info['Entropy packages directory'] = etpConst['packagesbindir']
    info['Entropy logging directory'] = etpConst['logdir']
    info['Entropy Official Repository name'] = etpConst['officialrepositoryname']
    info['Entropy API'] = etpConst['etpapi']
    info['Equo pidfile'] = etpConst['pidfile']
    info['Entropy database tag'] = etpConst['databasestarttag']
    info['Repositories'] = etpRepositories
    
    # client database info
    conn = False
    try:
	clientDbconn = openClientDatabase()
	conn = True
    except:
	pass
    info['Installed database'] = conn
    if (conn):
	# print db info
	info['Removal internal protected directories'] = clientDbconn.listConfigProtectDirectories()
	info['Removal internal protected directory masks'] = clientDbconn.listConfigProtectDirectories(mask = True)
	info['Total installed packages'] = len(clientDbconn.listAllIdpackages())
	clientDbconn.closeDB()
    
    # repository databases info (if found on the system)
    info['Repository databases'] = {}
    for x in etpRepositories:
	dbfile = etpRepositories[x]['dbpath']+"/"+etpConst['etpdatabasefile']
	if os.path.isfile(dbfile):
	    # print info about this database
	    dbconn = openRepositoryDatabase(x)
	    info['Repository databases'][x] = {}
	    info['Repository databases'][x]['Installation internal protected directories'] = dbconn.listConfigProtectDirectories()
	    info['Repository databases'][x]['Installation internal protected directory masks'] = dbconn.listConfigProtectDirectories(mask = True)
	    info['Repository databases'][x]['Total available packages'] = len(dbconn.listAllIdpackages())
	    info['Repository databases'][x]['Database revision'] = getRepositoryRevision(x)
	    info['Repository databases'][x]['Database hash'] = getRepositoryDbFileHash(x)
	    dbconn.closeDB()
    
    if (dict):
	return info
    
    import types
    keys = info.keys()
    keys.sort()
    for x in keys:
	#print type(info[x])
	if type(info[x]) is types.DictType:
	    toptext = x
	    ykeys = info[x].keys()
	    ykeys.sort()
	    for y in ykeys:
		if type(info[x][y]) is types.DictType:
		    topsubtext = y
		    zkeys = info[x][y].keys()
		    zkeys.sort()
		    for z in zkeys:
			print red(toptext)+": "+blue(topsubtext)+" => "+darkgreen(z)+" => "+str(info[x][y][z])
		else:
		    print red(toptext)+": "+blue(y)+" => "+str(info[x][y])
	    #print info[x]
	else:
	    print red(x)+": "+str(info[x])
