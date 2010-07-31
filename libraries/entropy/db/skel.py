# -*- coding: utf-8 -*-
"""

    @author: Fabio Erculiani <lxnay@sabayon.org>
    @contact: lxnay@sabayon.org
    @copyright: Fabio Erculiani
    @license: GPL-2

    B{Entropy Framework repository database prototype classes module}.
"""
import os
import shutil
import warnings

from entropy.i18n import _
from entropy.exceptions import InvalidAtom
from entropy.const import etpConst, const_cmp
from entropy.output import TextInterface, brown, bold, red, blue, purple, \
    darkred
from entropy.cache import EntropyCacher
from entropy.core import EntropyPluginStore
from entropy.core.settings.base import SystemSettings
from entropy.exceptions import RepositoryPluginError
from entropy.spm.plugins.factory import get_default_instance as get_spm
from entropy.db.exceptions import OperationalError

import entropy.tools

class EntropyRepositoryPlugin(object):
    """
    This is the base class for implementing EntropyRepository plugin hooks.
    You have to subclass this, implement not implemented methods and provide
    it to EntropyRepository class as described below.

    Every plugin hook function features this signature:
        int something_hook(entropy_repository_instance)
    Where entropy_repository_instance is the calling EntropyRepository instance.
    Every method should return a return status code which, when nonzero causes
    a RepositoryPluginError exception to be thrown.
    Every method returns 0 in the base class implementation.
    """

    def get_id(self):
        """
        Return string identifier of myself.

        @return: EntropyRepositoryPlugin identifier.
        @rtype: string
        """
        return str(self)

    def get_metadata(self):
        """
        Developers reimplementing EntropyRepositoryPlugin can provide metadata
        along with every instance.
        If you want to provide read-only metadata, this method should really
        return a copy of the metadata object, otherwise, return its direct
        reference.
        Metadata format is a map-like object (dictionary, dict()).
        By default this method does return an empty dict.
        Make sure that your metadata dictionaries around don't have keys in
        common, otherwise those will be randomly overwritten eachothers.

        @return: plugin metadata
        @rtype: dict
        """
        return {}

    def add_plugin_hook(self, entropy_repository_instance):
        """
        Called during EntropyRepository plugin addition.

        @param entropy_repository_instance: EntropyRepository instance
        @type entropy_repository_instance: EntropyRepository
        @return: execution status code, return nonzero for errors, this will
            raise a RepositoryPluginError exception.
        @rtype: int
        """
        return 0

    def remove_plugin_hook(self, entropy_repository_instance):
        """
        Called during EntropyRepository plugin removal.

        @param entropy_repository_instance: EntropyRepository instance
        @type entropy_repository_instance: EntropyRepository
        @return: execution status code, return nonzero for errors, this will
            raise a RepositoryPluginError exception.
        @rtype: int
        """
        return 0

    def commit_hook(self, entropy_repository_instance):
        """
        Called during EntropyRepository data commit.

        @param entropy_repository_instance: EntropyRepository instance
        @type entropy_repository_instance: EntropyRepository
        @return: execution status code, return nonzero for errors, this will
            raise a RepositoryPluginError exception.
        @rtype: int
        """
        return 0

    def close_repo_hook(self, entropy_repository_instance):
        """
        Called during EntropyRepository instance shutdown (closeDB).

        @param entropy_repository_instance: EntropyRepository instance
        @type entropy_repository_instance: EntropyRepository
        @return: execution status code, return nonzero for errors, this will
            raise a RepositoryPluginError exception.
        @rtype: int
        """
        return 0

    def add_package_hook(self, entropy_repository_instance, package_id,
        package_data):
        """
        Called after the addition of a package from EntropyRepository.

        @param entropy_repository_instance: EntropyRepository instance
        @type entropy_repository_instance: EntropyRepository
        @param package_id: Entropy repository package identifier
        @type package_id: int
        @param package_data: package metadata used for insertion
            (see addPackage)
        @type package_data: dict
        @return: execution status code, return nonzero for errors, this will
            raise a RepositoryPluginError exception.
        @rtype: int
        """
        return 0

    def remove_package_hook(self, entropy_repository_instance, package_id,
        from_add_package):
        """
        Called after the removal of a package from EntropyRepository.

        @param entropy_repository_instance: EntropyRepository instance
        @type entropy_repository_instance: EntropyRepository
        @param package_id: Entropy repository package identifier
        @type package_id: int
        @param from_add_package: inform whether removePackage() is called inside
            addPackage()
        @return: execution status code, return nonzero for errors, this will
            raise a RepositoryPluginError exception.
        @rtype: int
        """
        return 0

    def clear_cache_hook(self, entropy_repository_instance):
        """
        Called during EntropyRepository cache cleanup (clearCache).

        @param entropy_repository_instance: EntropyRepository instance
        @type entropy_repository_instance: EntropyRepository
        @return: execution status code, return nonzero for errors, this will
            raise a RepositoryPluginError exception.
        @rtype: int
        """
        return 0

    def initialize_repo_hook(self, entropy_repository_instance):
        """
        Called during EntropyRepository data initialization (not instance init).

        @param entropy_repository_instance: EntropyRepository instance
        @type entropy_repository_instance: EntropyRepository
        @return: execution status code, return nonzero for errors, this will
            raise a RepositoryPluginError exception.
        @rtype: int
        """
        return 0

    def accept_license_hook(self, entropy_repository_instance):
        """
        Called during EntropyRepository acceptLicense call.

        @param entropy_repository_instance: EntropyRepository instance
        @type entropy_repository_instance: EntropyRepository
        @return: execution status code, return nonzero for errors, this will
            raise a RepositoryPluginError exception.
        @rtype: int
        """
        return 0

    def treeupdates_move_action_hook(self, entropy_repository_instance,
        package_id):
        """
        Called after EntropyRepository treeupdates move action execution for
        given package_id in given EntropyRepository instance.

        @param entropy_repository_instance: EntropyRepository instance
        @type entropy_repository_instance: EntropyRepository
        @param package_id: Entropy repository package identifier
        @type package_id: int
        @return: execution status code, return nonzero for errors, this will
            raise a RepositoryPluginError exception.
        @rtype: int
        """
        return 0

    def treeupdates_slot_move_action_hook(self, entropy_repository_instance,
        package_id):
        """
        Called after EntropyRepository treeupdates slot move action
        execution for given package_id in given EntropyRepository instance.

        @param entropy_repository_instance: EntropyRepository instance
        @type entropy_repository_instance: EntropyRepository
        @param package_id: Entropy repository package identifier
        @type package_id: int
        @return: execution status code, return nonzero for errors, this will
            raise a RepositoryPluginError exception.
        @rtype: int
        """
        return 0

class EntropyRepositoryPluginStore(EntropyPluginStore):

    """
    EntropyRepository plugin interface. This is the EntropyRepository part
    aimed to handle connected plugins.
    """

    _PERMANENT_PLUGINS = {}

    def __init__(self):
        EntropyPluginStore.__init__(self)
        permanent_plugs = EntropyRepositoryPluginStore.get_permanent_plugins()
        for plug in permanent_plugs.values():
            plug.add_plugin_hook(self)

    def add_plugin(self, entropy_repository_plugin):
        """
        Overloaded from EntropyPluginStore, adds support for hooks execution.
        """
        inst = entropy_repository_plugin
        if not isinstance(inst, EntropyRepositoryPlugin):
            raise AttributeError("EntropyRepositoryPluginStore: " + \
                    "expected valid EntropyRepositoryPlugin instance")
        EntropyPluginStore.add_plugin(self, inst.get_id(), inst)
        inst.add_plugin_hook(self)

    def remove_plugin(self, plugin_id):
        """
        Overloaded from EntropyPluginStore, adds support for hooks execution.
        """
        plugins = self.get_plugins()
        plug_inst = plugins.get(plugin_id)
        if plug_inst is not None:
            plug_inst.remove_plugin_hook(self)
        return EntropyPluginStore.remove_plugin(self, plugin_id)

    @staticmethod
    def add_permanent_plugin(entropy_repository_plugin):
        """
        Add EntropyRepository permanent plugin. This plugin object will be
        used across all the instantiated EntropyRepositoryPluginStore classes.
        Each time a new instance is created, add_plugin_hook will be executed
        for all the permanent plugins.

        @param entropy_repository_plugin: EntropyRepositoryPlugin instance
        @type entropy_repository_plugin: EntropyRepositoryPlugin instance
        """
        inst = entropy_repository_plugin
        if not isinstance(inst, EntropyRepositoryPlugin):
            raise AttributeError("EntropyRepositoryPluginStore: " + \
                    "expected valid EntropyRepositoryPlugin instance")
        EntropyRepositoryPluginStore._PERMANENT_PLUGINS[inst.get_id()] = inst

    @staticmethod
    def remove_permanent_plugin(plugin_id):
        """
        Remove EntropyRepository permanent plugin. This plugin object will be
        removed across all the EntropyRepository instances around.
        Please note: due to the fact that there are no destructors around,
        the "remove_plugin_hook" callback won't be executed when calling this
        static method.

        @param plugin_id: EntropyRepositoryPlugin identifier
        @type plugin_id: string
        @raise KeyError: in case of unavailable plugin identifier
        """
        del EntropyRepositoryPluginStore._PERMANENT_PLUGINS[plugin_id]

    @staticmethod
    def get_permanent_plugins():
        """
        Return EntropyRepositoryStore installed permanent plugins.

        @return: copy of internal permanent plugins dict
        @rtype: dict
        """
        return EntropyRepositoryPluginStore._PERMANENT_PLUGINS.copy()

    def get_plugins(self):
        """
        Overloaded from EntropyPluginStore, adds support for permanent plugins.
        """
        plugins = EntropyPluginStore.get_plugins(self)
        plugins.update(EntropyRepositoryPluginStore.get_permanent_plugins())
        return plugins

    def get_plugins_metadata(self):
        """
        Return EntropyRepositoryPluginStore registered plugins metadata.

        @return: plugins metadata
        @rtype: dict
        """
        plugins = self.get_plugins()
        meta = {}
        for plugin_id in plugins:
            meta.update(plugins[plugin_id].get_metadata())
        return meta

    def get_plugin_metadata(self, plugin_id, key):
        """
        Return EntropyRepositoryPlugin metadata value referenced by "key".

        @param plugin_id. EntropyRepositoryPlugin identifier
        @type plugin_id: string
        @param key: EntropyRepositoryPlugin metadatum identifier
        @type key: string
        @return: metadatum value
        @rtype: any Python object
        @raise KeyError: if provided key or plugin_id is not available
        """
        plugins = self.get_plugins()
        return plugins[plugin_id][key]

    def set_plugin_metadata(self, plugin_id, key, value):
        """
        Set EntropyRepositoryPlugin stored metadata.

        @param plugin_id. EntropyRepositoryPlugin identifier
        @type plugin_id: string
        @param key: EntropyRepositoryPlugin metadatum identifier
        @type key: string
        @param value: value to set
        @type value: any valid Python object
        @raise KeyError: if plugin_id is not available
        """
        plugins = self.get_plugins()
        meta = plugins[plugin_id].get_metadata()
        meta[key] = value


class EntropyRepositoryBase(TextInterface, EntropyRepositoryPluginStore, object):
    """
    EntropyRepository interface base class.
    This is an abstact class containing abstract methods that
    subclasses need to reimplement.
    Every Entropy repository object has to inherit this class.
    """

    VIRTUAL_META_PACKAGE_CATEGORY = "virtual"

    def __init__(self, readonly, xcache, temporary, reponame, indexing):
        """
        EntropyRepositoryBase constructor.

        @param readonly: readonly bit
        @type readonly: bool
        @param xcache: xcache bit (enable on-disk cache?)
        @type xcache: bool
        @param temporary: is this repo a temporary (non persistent) one?
        @type temporary: bool
        @param reponame: name of this repository
        @type reponame: string
        @param indexing: enable metadata indexing (for faster retrieval)
        @type indexing: bool
        """
        self.readonly = readonly
        self.xcache = xcache
        self.temporary = temporary
        self.indexing = indexing
        self.dbname = reponame
        self.reponame = reponame
        self._settings = SystemSettings()
        self._cacher = EntropyCacher()
        self.__db_match_cache_key = EntropyCacher.CACHE_IDS['db_match']
        self.__cs_plugin_id = \
            etpConst['system_settings_plugins_ids']['client_plugin']

        EntropyRepositoryPluginStore.__init__(self)

    def closeDB(self):
        """
        Close repository storage communication and open disk files.
        You can still use this instance, but closed files will be reopened.
        Attention: call this method from your subclass, otherwise
        EntropyRepositoryPlugins won't be notified of a repo close.
        """
        if not self.readonly:
            self.commitChanges()

        plugins = self.get_plugins()
        for plugin_id in sorted(plugins):
            plug_inst = plugins[plugin_id]
            exec_rc = plug_inst.close_repo_hook(self)
            if exec_rc:
                raise RepositoryPluginError(
                    "[close_repo_hook] %s: status: %s" % (
                        plug_inst.get_id(), exec_rc,))

    def vacuum(self):
        """
        Repository storage cleanup and optimization function.
        """
        raise NotImplementedError()

    def commitChanges(self, force = False, no_plugins = False):
        """
        Commit actual changes and make them permanently stored.
        Attention: call this method from your subclass, otherwise
        EntropyRepositoryPlugins won't be notified.

        @keyword force: force commit, despite read-only bit being set
        @type force: bool
        @keyword no_plugins: disable EntropyRepository plugins execution
        @type no_plugins: bool
        """
        if no_plugins:
            return

        plugins = self.get_plugins()
        for plugin_id in sorted(plugins):
            plug_inst = plugins[plugin_id]
            exec_rc = plug_inst.commit_hook(self)
            if exec_rc:
                raise RepositoryPluginError("[commit_hook] %s: status: %s" % (
                    plug_inst.get_id(), exec_rc,))

    def initializeRepository(self):
        """
        This method (re)initializes the repository, dropping all its content.
        Attention: call this method from your subclass, otherwise
        EntropyRepositoryPlugins won't be notified (AT THE END).
        """
        plugins = self.get_plugins()
        for plugin_id in sorted(plugins):
            plug_inst = plugins[plugin_id]
            exec_rc = plug_inst.initialize_repo_hook(self)
            if exec_rc:
                raise RepositoryPluginError(
                    "[initialize_repo_hook] %s: status: %s" % (
                        plug_inst.get_id(), exec_rc,))

    def filterTreeUpdatesActions(self, actions):
        """
        This method should be considered internal and not suited for general
        audience. Given a raw package name/slot updates list, it returns
        the action that should be really taken because not applied.

        @param actions: list of raw treeupdates actions, for example:
            ['move x11-foo/bar app-foo/bar', 'slotmove x11-foo/bar 2 3']
        @type actions: list
        @return: list of raw treeupdates actions that should be really
            worked out
        @rtype: list
        """
        new_actions = []
        for action in actions:

            if action in new_actions: # skip dupies
                continue

            doaction = action.split()
            if doaction[0] == "slotmove":

                # slot move
                atom = doaction[1]
                from_slot = doaction[2]
                to_slot = doaction[3]
                atom_key = entropy.tools.dep_getkey(atom)
                category = atom_key.split("/")[0]
                matches, sm_rc = self.atomMatch(atom, matchSlot = from_slot,
                    multiMatch = True)
                if sm_rc == 1:
                    # nothing found in repo that matches atom
                    # this means that no packages can effectively
                    # reference to it
                    continue
                found = False
                # found atoms, check category
                for package_id in matches:
                    myslot = self.retrieveSlot(package_id)
                    mycategory = self.retrieveCategory(package_id)
                    if mycategory == category:
                        if  (myslot != to_slot) and \
                        (action not in new_actions):
                            new_actions.append(action)
                            found = True
                            break
                if found:
                    continue
                # if we get here it means found == False
                # search into dependencies
                dep_atoms = self.searchDependency(atom_key, like = True,
                    multi = True, strings = True)
                dep_atoms = [x for x in dep_atoms if x.endswith(":"+from_slot) \
                    and entropy.tools.dep_getkey(x) == atom_key]
                if dep_atoms:
                    new_actions.append(action)

            elif doaction[0] == "move":

                atom = doaction[1] # usually a key
                atom_key = entropy.tools.dep_getkey(atom)
                category = atom_key.split("/")[0]
                matches, m_rc = self.atomMatch(atom, multiMatch = True)
                if m_rc == 1:
                    # nothing found in repo that matches atom
                    # this means that no packages can effectively
                    # reference to it
                    continue
                found = False
                for package_id in matches:
                    mycategory = self.retrieveCategory(package_id)
                    if (mycategory == category) and (action \
                        not in new_actions):
                        new_actions.append(action)
                        found = True
                        break
                if found:
                    continue
                # if we get here it means found == False
                # search into dependencies
                dep_atoms = self.searchDependency(atom_key, like = True,
                    multi = True, strings = True)
                dep_atoms = [x for x in dep_atoms if \
                    entropy.tools.dep_getkey(x) == atom_key]
                if dep_atoms:
                    new_actions.append(action)

        return new_actions

    def handlePackage(self, pkg_data, forcedRevision = -1,
        formattedContent = False):
        """
        Update or add a package to repository automatically handling
        its scope and thus removal of previous versions if requested by
        the given metadata.
        pkg_data is a dict() containing all the information bound to
        a package:

            {
                'signatures':
                    {
                        'sha256': 'zzz',
                        'sha1': 'zzz',
                        'sha512': 'zzz'
                 },
                'slot': '0',
                'datecreation': '1247681752.93',
                'description': 'Standard (de)compression library',
                'useflags': set(['kernel_linux']),
                'eclasses': set(['multilib']),
                'config_protect_mask': 'string string', 'etpapi': 3,
                'mirrorlinks': [],
                'cxxflags': '-Os -march=x86-64 -pipe',
                'injected': False,
                'licensedata': {'ZLIB': u"lictext"},
                'dependencies': {},
                'chost': 'x86_64-pc-linux-gn',
                'config_protect': 'string string',
                'download': 'packages/amd64/4/sys-libs:zlib-1.2.3-r1.tbz2',
                'conflicts': set([]),
                'digest': 'fd54248ae060c287b1ec939de3e55332',
                'size': '136302',
                'category': 'sys-libs',
                'license': 'ZLIB',
                'sources': set(),
                'name': 'zlib',
                'versiontag': '',
                'changelog': u"text",
                'provide': set([]),
                'trigger': 'text',
                'counter': 22331,
                'messages': [],
                'branch': '4',
                'content': {},
                'needed': [('libc.so.6', 2)],
                'version': '1.2.3-r1',
                'keywords': set(),
                'cflags': '-Os -march=x86-64 -pipe',
                'disksize': 932206, 'spm_phases': None,
                'homepage': 'http://www.zlib.net/',
                'systempackage': True,
                'revision': 0
            }

        @param pkg_data: Entropy package metadata dict
        @type pkg_data: dict
        @keyword forcedRevision: force a specific package revision
        @type forcedRevision: int
        @keyword formattedContent: tells whether content metadata is already
            formatted for insertion
        @type formattedContent: bool
        @return: tuple composed by
            - package_id: unique Entropy Repository package identifier
            - revision: final package revision selected
            - pkg_data: new Entropy package metadata dict
        @rtype: tuple
        """
        raise NotImplementedError()

    def getPackagesToRemove(self, name, category, slot, injected):
        """
        Return a list of packages that would be removed given name, category,
        slot and injection status.

        @param name: package name
        @type name: string
        @param category: package category
        @type category: string
        @param slot: package slot
        @type slot: string
        @param injected: injection status (packages marked as injected are
            always considered not automatically removable)
        @type injected: bool

        @return: list (set) of removable packages (package_ids)
        @rtype: set
        """
        removelist = set()
        if injected:
            # read: if package has been injected, we'll skip
            # the removal of packages in the same slot,
            # usually used server side btw
            return removelist

        searchsimilar = self.searchNameCategory(
            name = name,
            category = category,
            sensitive = True
        )

        # support for expiration-based packages handling, also internally
        # called Fat Scope.
        filter_similar = False
        srv_ss_plg = etpConst['system_settings_plugins_ids']['server_plugin']
        srv_ss_fs_plg = \
            etpConst['system_settings_plugins_ids']['server_plugin_fatscope']

        srv_plug_settings = self._settings.get(srv_ss_plg)
        if srv_plug_settings is not None:
            if srv_plug_settings['server']['exp_based_scope']:
                # in case support is enabled, return an empty set
                filter_similar = True

        if filter_similar:
            # filter out packages in the same scope that are allowed to stay
            idpkgs = self._settings[srv_ss_fs_plg]['repos'].get(
                self.reponame)
            if idpkgs:
                if -1 in idpkgs:
                    del searchsimilar[:]
                else:
                    searchsimilar = [x for x in searchsimilar if x[1] \
                        not in idpkgs]

        for atom, package_id in searchsimilar:
            # get the package slot
            myslot = self.retrieveSlot(package_id)
            # we merely ignore packages with
            # negative counters, since they're the injected ones
            if self.isInjected(package_id):
                continue
            if slot == myslot:
                # remove!
                removelist.add(package_id)

        return removelist

    def addPackage(self, pkg_data, revision = -1, package_id = None,
        do_commit = True, formatted_content = False):
        """
        Add package to this Entropy repository. The main difference between
        handlePackage and this is that from here, no packages are going to be
        removed, in any case.
        For more information about pkg_data layout, please see
        I{handlePackage()}.
        Attention: call this method from your subclass (AT THE END), otherwise
        EntropyRepositoryPlugins won't be notified.

        @param pkg_data: Entropy package metadata
        @type pkg_data: dict
        @keyword revision: force a specific Entropy package revision
        @type revision: int
        @keyword package_id: add package to Entropy repository using the
            provided package identifier, this is very dangerous and could
            cause packages with the same identifier to be removed.
        @type package_id: int
        @keyword do_commit: if True, automatically commits the executed
            transaction (could cause slowness)
        @type do_commit: bool
        @keyword formatted_content: if True, determines whether the content
            metadata (usually the biggest part) in pkg_data is already
            prepared for insertion
        @type formatted_content: bool
        @return: tuple composed by
            - package_id: unique Entropy Repository package identifier
            - revision: final package revision selected
            - pkg_data: new Entropy package metadata dict
        @rtype: tuple
        """
        plugins = self.get_plugins()
        for plugin_id in sorted(plugins):
            plug_inst = plugins[plugin_id]
            exec_rc = plug_inst.add_package_hook(self, package_id, pkg_data)
            if exec_rc:
                raise RepositoryPluginError(
                    "[add_package_hook] %s: status: %s" % (
                        plug_inst.get_id(), exec_rc,))

    def removePackage(self, package_id, do_cleanup = True, do_commit = True,
        from_add_package = False):
        """
        Remove package from this Entropy repository using it's identifier
        (package_id).
        Attention: call this method from your subclass, otherwise
        EntropyRepositoryPlugins won't be notified.

        @param package_id: Entropy repository package indentifier
        @type package_id: int
        @keyword do_cleanup: if True, executes repository metadata cleanup
            at the end
        @type do_cleanup: bool
        @keyword do_commit: if True, commits the transaction (could cause
            slowness)
        @type do_commit: bool
        @keyword from_add_package: inform function that it's being called from
            inside addPackage().
        @type from_add_package: bool
        """
        plugins = self.get_plugins()
        for plugin_id in sorted(plugins):
            plug_inst = plugins[plugin_id]
            exec_rc = plug_inst.remove_package_hook(self, package_id,
                from_add_package)
            if exec_rc:
                raise RepositoryPluginError(
                    "[remove_package_hook] %s: status: %s" % (
                        plug_inst.get_id(), exec_rc,))

    def setInjected(self, package_id, do_commit = True):
        """
        Mark package as injected, injection is usually set for packages
        manually added to repository. Injected packages are not removed
        automatically even when featuring conflicting scope with other
        that are being added. If a package is injected, it means that
        maintainers have to handle it manually.

        @param package_id: package indentifier
        @type package_id: int
        @keyword do_commit: determine whether executing commit or not
        @type do_commit: bool
        """
        raise NotImplementedError()

    def setCreationDate(self, package_id, date):
        """
        Update the creation date for package. Creation date is stored in
        string based unix time format.

        @param package_id: package indentifier
        @type package_id: int
        @param date: unix time in string form
        @type date: string
        """
        raise NotImplementedError()

    def setDigest(self, package_id, digest):
        """
        Set package file md5sum for package. This information is used
        by entropy.client when downloading packages.

        @param package_id: package indentifier
        @type package_id: int
        @param digest: md5 hash for package file
        @type digest: string
        """
        raise NotImplementedError()

    def setSignatures(self, package_id, sha1, sha256, sha512, gpg = None):
        """
        Set package file extra hashes (sha1, sha256, sha512) for package.

        @param package_id: package indentifier
        @type package_id: int
        @param sha1: SHA1 hash for package file
        @type sha1: string
        @param sha256: SHA256 hash for package file
        @type sha256: string
        @param sha512: SHA512 hash for package file
        @type sha512: string
        @keyword gpg: GPG signature file content
        @type gpg: string
        """
        raise NotImplementedError()

    def setDownloadURL(self, package_id, url):
        """
        Set download URL prefix for package.

        @param package_id: package indentifier
        @type package_id: int
        @param url: URL prefix to set
        @type url: string
        """
        raise NotImplementedError()

    def setName(self, package_id, name):
        """
        Set name for package.

        @param package_id: package indentifier
        @type package_id: int
        @param name: package name
        @type name: string
        """
        raise NotImplementedError()

    def setAtom(self, package_id, atom):
        """
        Set atom string for package. "Atom" is the full, unique name of
        a package.

        @param package_id: package indentifier
        @type package_id: int
        @param atom: atom string
        @type atom: string
        """
        raise NotImplementedError()

    def setSlot(self, package_id, slot):
        """
        Set slot string for package. Please refer to Portage SLOT documentation
        for more info.

        @param package_id: package indentifier
        @type package_id: int
        @param slot: slot string
        @type slot: string
        """
        raise NotImplementedError()

    def setDependency(self, iddependency, dependency):
        """
        Set dependency string for iddependency (dependency identifier).

        @param iddependency: dependency string identifier
        @type iddependency: int
        @param dependency: dependency string
        @type dependency: string
        """
        raise NotImplementedError()

    def setCategory(self, package_id, category):
        """
        Set category name for package.

        @param package_id: package indentifier
        @type package_id: int
        @param category: category to set
        @type category: string
        """
        raise NotImplementedError()

    def setCategoryDescription(self, category, description_data):
        """
        Set description for given category name.

        @param category: category name
        @type category: string
        @param description_data: category description for several locales.
            {'en': "This is blah", 'it': "Questo e' blah", ... }
        @type description_data: dict
        """
        raise NotImplementedError()

    def setRevision(self, package_id, revision):
        """
        Set Entropy revision for package.

        @param package_id: package indentifier
        @type package_id: int
        @param revision: new revision
        @type revision: int
        """
        raise NotImplementedError()

    def removeDependencies(self, package_id):
        """
        Remove all the dependencies of package.

        @param package_id: package indentifier
        @type package_id: int
        """
        raise NotImplementedError()

    def insertDependencies(self, package_id, depdata):
        """
        Insert dependencies for package. "depdata" is a dict() with dependency
        strings as keys and dependency type as values.

        @param package_id: package indentifier
        @type package_id: int
        @param depdata: dependency dictionary
            {'app-foo/foo': dep_type_integer, ...}
        @type depdata: dict
        """
        raise NotImplementedError()

    def insertContent(self, package_id, content, already_formatted = False):
        """
        Insert content metadata for package. "content" can either be a dict()
        or a list of triples (tuples of length 3, (package_id, path, type,)).

        @param package_id: package indentifier
        @type package_id: int
        @param content: content metadata to insert.
            {'/path/to/foo': 'obj(content type)',}
            or
            [(package_id, path, type,) ...]
        @type content: dict, list
        @keyword already_formatted: if True, "content" is expected to be
            already formatted for insertion, this means that "content" must be
            a list of tuples of length 3.
        @type already_formatted: bool
        """
        raise NotImplementedError()

    def insertAutomergefiles(self, package_id, automerge_data):
        """
        Insert configuration files automerge information for package.
        "automerge_data" contains configuration files paths and their belonging
        md5 hash.
        This features allows entropy.client to "auto-merge" or "auto-remove"
        configuration files never touched by user.

        @param package_id: package indentifier
        @type package_id: int
        @param automerge_data: list of tuples of length 2.
            [('/path/to/conf/file', 'md5_checksum_string',) ... ]
        @type automerge_data: list
        """
        raise NotImplementedError()

    def insertBranchMigration(self, repository, from_branch, to_branch,
        post_migration_md5sum, post_upgrade_md5sum):
        """
        Insert Entropy Client "branch migration" scripts hash metadata.
        When upgrading from a branch to another, it can happen that repositories
        ship with scripts aiming to ease the upgrade.
        This method stores in the repository information on such scripts.

        @param repository: repository identifier
        @type repository: string
        @param from_branch: original branch
        @type from_branch: string
        @param to_branch: destination branch
        @type to_branch: string
        @param post_migration_md5sum: md5 hash related to "post-migration"
            branch script file
        @type post_migration_md5sum: string
        @param post_upgrade_md5sum: md5 hash related to "post-upgrade on new
            branch" script file
        @type post_upgrade_md5sum: string
        """
        raise NotImplementedError()

    def setBranchMigrationPostUpgradeMd5sum(self, repository, from_branch,
        to_branch, post_upgrade_md5sum):
        """
        Update "post-upgrade on new branch" script file md5 hash.
        When upgrading from a branch to another, it can happen that repositories
        ship with scripts aiming to ease the upgrade.
        This method stores in the repository information on such scripts.

        @param repository: repository identifier
        @type repository: string
        @param from_branch: original branch
        @type from_branch: string
        @param to_branch: destination branch
        @type to_branch: string
        @param post_upgrade_md5sum: md5 hash related to "post-upgrade on new
            branch" script file
        @type post_upgrade_md5sum: string
        """
        raise NotImplementedError()

    def insertSpmUid(self, package_id, spm_package_uid):
        """
        Insert Source Package Manager unique package identifier and bind it
        to Entropy package identifier given (package_id). This method is used
        by Entropy Client and differs from "_bindSpmPackageUid" because
        any other colliding package_id<->uid binding is overwritten by design.

        @param package_id: package indentifier
        @type package_id: int
        @param spm_package_uid: Source package Manager unique package identifier
        @type spm_package_uid: int
        """
        raise NotImplementedError()

    def setTrashedUid(self, spm_package_uid):
        """
        Mark given Source Package Manager unique package identifier as
        "trashed". This is a trick to allow Entropy Server to support
        multiple repositories and parallel handling of them without
        make it messing with removed packages from the underlying system.

        @param spm_package_uid: Source package Manager unique package identifier
        @type spm_package_uid: int
        """
        raise NotImplementedError()

    def setSpmUid(self, package_id, spm_package_uid, branch = None):
        """
        Update Source Package Manager unique package identifier for given
        Entropy package identifier (package_id).
        This method *only* updates a currently available binding setting a new
        "spm_package_uid"

        @param package_id: package indentifier
        @type package_id: int
        @param spm_package_uid: Source package Manager unique package identifier
        @type spm_package_uid: int
        @keyword branch: current Entropy repository branch
        @type branch: string
        """
        raise NotImplementedError()

    def contentDiff(self, package_id, dbconn, dbconn_package_id):
        """
        Return content metadata difference between two packages.

        @param package_id: package indentifier available in this repository
        @type package_id: int
        @param dbconn: other repository class instance
        @type dbconn: EntropyRepository
        @param dbconn_package_id: package identifier available in other
            repository
        @type dbconn_package_id: int
        @return: content difference
        @rtype: set
        @raise AttributeError: when self instance and dbconn are the same
        """
        raise NotImplementedError()

    def clean(self):
        """
        Run repository metadata cleanup over unused references.
        """
        raise NotImplementedError()

    def getDependency(self, iddependency):
        """
        Return dependency string for given dependency identifier.

        @param iddependency: dependency identifier
        @type iddependency: int
        @return: dependency string
        @rtype: string or None
        """
        raise NotImplementedError()

    def getFakeSpmUid(self):
        """
        Obtain auto-generated available negative Source Package Manager
        package identifier.

        @return: new negative spm uid
        @rtype: int
        """
        raise NotImplementedError()

    def getApi(self):
        """
        Get Entropy repository API.

        @return: Entropy repository API
        @rtype: int
        """
        raise NotImplementedError()

    def getPackageIds(self, atom):
        """
        Obtain repository package identifiers from atom string.

        @param atom: package atom
        @type atom: string
        @return: list of matching package_ids found
        @rtype: set
        """
        raise NotImplementedError()

    def getPackageIdFromDownload(self, download_relative_path,
        endswith = False):
        """
        Obtain repository package identifier from its relative download path
        string.

        @param download_relative_path: relative download path string returned
            by "retrieveDownloadURL" method
        @type download_relative_path: string
        @keyword endswith: search for package_id which download metadata ends
            with the one provided by download_relative_path
        @type endswith: bool
        @return: package_id in repository or -1 if not found
        @rtype: int
        """
        raise NotImplementedError()

    def getVersioningData(self, package_id):
        """
        Get package version information for provided package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: tuple of length 3 composed by (version, tag, revision,)
            belonging to package_id
        @rtype: tuple
        """
        raise NotImplementedError()

    def getStrictData(self, package_id):
        """
        Get a restricted (optimized) set of package metadata for provided
        package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: tuple of length 6 composed by
            (package key, slot, version, tag, revision, atom)
            belonging to package_id
        @rtype: tuple
        """
        raise NotImplementedError()

    def getStrictScopeData(self, package_id):
        """
        Get a restricted (optimized) set of package metadata for provided
        identifier that can be used to determine the scope of package.

        @param package_id: package indentifier
        @type package_id: int
        @return: tuple of length 3 composed by (atom, slot, revision,)
            belonging to package_id
        @rtype: tuple
        """
        raise NotImplementedError()

    def getScopeData(self, package_id):
        """
        Get a set of package metadata for provided identifier that can be
        used to determine the scope of package.

        @param package_id: package indentifier
        @type package_id: int
        @return: tuple of length 9 composed by
            (atom, category name, name, version,
                slot, tag, revision, branch, api,)
            belonging to package_id
        @rtype: tuple
        """
        raise NotImplementedError()

    def getBaseData(self, package_id):
        """
        Get a set of basic package metadata for provided package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: tuple of length 19 composed by
            (atom, name, version, tag, description, category name, CHOST,
            CFLAGS, CXXFLAGS, homepage, license, branch, download path, digest,
            slot, api, creation date, package size, revision,)
            belonging to package_id
        @rtype: tuple
        """
        raise NotImplementedError()

    def getTriggerData(self, package_id, content = True):
        """
        Get a set of basic package metadata for provided package identifier.
        This method is optimized to work with Entropy Client installation
        triggers returning only what is strictly needed.

        @param package_id: package indentifier
        @type package_id: int
        @keyword content: if True, grabs the "content" metadata too, othewise
            such dict key value will be shown as empty set().
        @type content: bool
        @return: dictionary containing package metadata

            data = {
                'atom': atom,
                'category': category,
                'name': name,
                'version': version,
                'versiontag': versiontag,
                'revision': revision,
                'branch': branch,
                'chost': chost,
                'cflags': cflags,
                'cxxflags': cxxflags,
                'etpapi': etpapi,
                'trigger': self.retrieveTrigger(package_id),
                'eclasses': self.retrieveEclasses(package_id),
                'content': pkg_content,
                'spm_phases': self.retrieveSpmPhases(package_id),
            }

        @rtype: dict or None
        """
        scope_data = self.getScopeData(package_id)
        if scope_data is None:
            return
        atom, category, name, \
        version, slot, versiontag, \
        revision, branch, etpapi = scope_data
        chost, cflags, cxxflags = self.retrieveCompileFlags(package_id)

        pkg_content = set()
        if content:
            pkg_content = self.retrieveContent(package_id)

        data = {
            'atom': atom,
            'category': category,
            'name': name,
            'version': version,
            'versiontag': versiontag,
            'revision': revision,
            'branch': branch,
            'chost': chost,
            'cflags': cflags,
            'cxxflags': cxxflags,
            'etpapi': etpapi,
            'trigger': self.retrieveTrigger(package_id),
            'eclasses': self.retrieveEclasses(package_id),
            'content': pkg_content,
            'spm_phases': self.retrieveSpmPhases(package_id),
        }
        return data

    def getPackageData(self, package_id, get_content = True,
            content_insert_formatted = False, get_changelog = True):
        """
        Reconstruct all the package metadata belonging to provided package
        identifier into a dict object.

        @param package_id: package indentifier
        @type package_id: int
        @keyword get_content:
        @type get_content: bool
        @keyword content_insert_formatted:
        @type content_insert_formatted: bool
        @keyword get_changelog:  return ChangeLog text metadatum or None
        @type get_changelog: bool
        @return: package metadata in dict() form

        >>> data = {
            'atom': atom,
            'name': name,
            'version': version,
            'versiontag':versiontag,
            'description': description,
            'category': category,
            'chost': chost,
            'cflags': cflags,
            'cxxflags': cxxflags,
            'homepage': homepage,
            'license': mylicense,
            'branch': branch,
            'download': download,
            'digest': digest,
            'slot': slot,
            'etpapi': etpapi,
            'datecreation': datecreation,
            'size': size,
            'revision': revision,
            'counter': self.retrieveSpmUid(package_id),
            'messages': [], deprecated
            'trigger': self.retrieveTrigger(package_id),
            'disksize': self.retrieveOnDiskSize(package_id),
            'changelog': self.retrieveChangelog(package_id),
            'injected': self.isInjected(package_id),
            'systempackage': self.isSystemPackage(package_id),
            'config_protect': self.retrieveProtect(package_id),
            'config_protect_mask': self.retrieveProtectMask(package_id),
            'useflags': self.retrieveUseflags(package_id),
            'keywords': self.retrieveKeywords(package_id),
            'sources': sources,
            'eclasses': self.retrieveEclasses(package_id),
            'needed': self.retrieveNeeded(package_id, extended = True),
            'provided_libs': self.retrieveProvidedLibraries(package_id),
            'provide': provide (the old provide metadata version)
            'provide_extended': self.retrieveProvide(package_id),
            'conflicts': self.retrieveConflicts(package_id),
            'licensedata': self.retrieveLicenseData(package_id),
            'content': content,
            'dependencies': dict((x, y,) for x, y in \
                self.retrieveDependencies(package_id, extended = True)),
            'mirrorlinks': [[x,self.retrieveMirrorData(x)] for x in mirrornames],
            'signatures': signatures,
            'spm_phases': self.retrieveSpmPhases(package_id),
            'spm_repository': self.retrieveSpmRepository(package_id),
            'desktop_mime': [],
            'provided_mime': [],
        }

        @rtype: dict
        """
        data = {}
        try:
            atom, name, version, versiontag, \
            description, category, chost, \
            cflags, cxxflags, homepage, \
            mylicense, branch, download, \
            digest, slot, etpapi, \
            datecreation, size, revision  = self.getBaseData(package_id)
        except TypeError:
            return None

        content = {}
        if get_content:
            content = self.retrieveContent(
                package_id, extended = True,
                formatted = True, insert_formatted = content_insert_formatted
            )

        sources = self.retrieveSources(package_id)
        mirrornames = set()
        for x in sources:
            if x.startswith("mirror://"):
                mirrornames.add(x.split("/")[2])

        sha1, sha256, sha512, gpg = self.retrieveSignatures(package_id)
        signatures = {
            'sha1': sha1,
            'sha256': sha256,
            'sha512': sha512,
            'gpg': gpg,
        }

        provide_extended = self.retrieveProvide(package_id)
        # TODO: remove this before 31-12-2011
        old_provide = set()
        for x in provide_extended:
            if isinstance(x, tuple):
                old_provide.add(x[0])
            else:
                old_provide.add(x)

        changelog = None
        if get_changelog:
            changelog = self.retrieveChangelog(package_id)

        data = {
            'atom': atom,
            'name': name,
            'version': version,
            'versiontag': versiontag,
            'description': description,
            'category': category,
            'chost': chost,
            'cflags': cflags,
            'cxxflags': cxxflags,
            'homepage': homepage,
            'license': mylicense,
            'branch': branch,
            'download': download,
            'digest': digest,
            'slot': slot,
            'etpapi': etpapi,
            'datecreation': datecreation,
            'size': size,
            'revision': revision,
            # risky to add to the sql above, still
            'counter': self.retrieveSpmUid(package_id),
            'messages': [],
            'trigger': self.retrieveTrigger(package_id),
            'disksize': self.retrieveOnDiskSize(package_id),
            'changelog': changelog,
            'injected': self.isInjected(package_id),
            'systempackage': self.isSystemPackage(package_id),
            'config_protect': self.retrieveProtect(package_id),
            'config_protect_mask': self.retrieveProtectMask(package_id),
            'useflags': self.retrieveUseflags(package_id),
            'keywords': self.retrieveKeywords(package_id),
            'sources': sources,
            'eclasses': self.retrieveEclasses(package_id),
            'needed': self.retrieveNeeded(package_id, extended = True),
            'provided_libs': self.retrieveProvidedLibraries(package_id),
            'provide': old_provide,
            'provide_extended': provide_extended,
            'conflicts': self.retrieveConflicts(package_id),
            'licensedata': self.retrieveLicenseData(package_id),
            'content': content,
            'dependencies': dict((x, y,) for x, y in \
                self.retrieveDependencies(package_id, extended = True)),
            'mirrorlinks': [[x, self.retrieveMirrorData(x)] for x in mirrornames],
            'signatures': signatures,
            'spm_phases': self.retrieveSpmPhases(package_id),
            'spm_repository': self.retrieveSpmRepository(package_id),
            'desktop_mime': self.retrieveDesktopMime(package_id),
            'provided_mime': self.retrieveProvidedMime(package_id),
        }

        return data

    def clearCache(self):
        """
        Clear repository cache.
        Attention: call this method from your subclass, otherwise
        EntropyRepositoryPlugins won't be notified.
        """
        plugins = self.get_plugins()
        for plugin_id in sorted(plugins):
            plug_inst = plugins[plugin_id]
            exec_rc = plug_inst.clear_cache_hook(self)
            if exec_rc:
                raise RepositoryPluginError(
                    "[clear_cache_hook] %s: status: %s" % (
                        plug_inst.get_id(), exec_rc,))

    def retrieveRepositoryUpdatesDigest(self, repository):
        """
        This method should be considered internal and not suited for general
        audience. Return digest (md5 hash) bound to repository package
        names/slots updates.

        @param repository: repository identifier
        @type repository: string
        @return: digest string
        @rtype: string
        """
        raise NotImplementedError()

    def runTreeUpdatesActions(self, actions):
        """
        Method not suited for general purpose usage.
        Executes package name/slot update actions passed.

        @param actions: list of raw treeupdates actions, for example:
            ['move x11-foo/bar app-foo/bar', 'slotmove x11-foo/bar 2 3']
        @type actions: list

        @return: list (set) of packages that should be repackaged
        @rtype: set
        """
        mytxt = "%s: %s, %s." % (
            bold(_("SPM")),
            blue(_("Running fixpackages")),
            red(_("it could take a while")),
        )
        self.output(
            mytxt,
            importance = 1,
            level = "warning",
            header = darkred(" * ")
        )
        try:
            spm = get_spm(self)
            spm.packages_repositories_metadata_update()
        except Exception:
            entropy.tools.print_traceback()

        spm_moves = set()
        quickpkg_atoms = set()
        for action in actions:
            command = action.split()
            mytxt = "%s: %s: %s." % (
                bold(_("ENTROPY")),
                red(_("action")),
                blue(action),
            )
            self.output(
                mytxt,
                importance = 1,
                level = "warning",
                header = darkred(" * ")
            )
            if command[0] == "move":
                spm_moves.add(action)
                quickpkg_atoms |= self._runTreeUpdatesMoveAction(command[1:],
                    quickpkg_atoms)
            elif command[0] == "slotmove":
                quickpkg_atoms |= self._runTreeUpdatesSlotmoveAction(command[1:],
                    quickpkg_atoms)

            mytxt = "%s: %s." % (
                bold(_("ENTROPY")),
                blue(_("package move actions complete")),
            )
            self.output(
                mytxt,
                importance = 1,
                level = "info",
                header = purple(" @@ ")
            )

        if spm_moves:
            try:
                self._doTreeupdatesSpmCleanup(spm_moves)
            except Exception as e:
                mytxt = "%s: %s: %s, %s." % (
                    bold(_("WARNING")),
                    red(_("Cannot run SPM cleanup, error")),
                    Exception,
                    e,
                )
                entropy.tools.print_traceback()

        mytxt = "%s: %s." % (
            bold(_("ENTROPY")),
            blue(_("package moves completed successfully")),
        )
        self.output(
            mytxt,
            importance = 1,
            level = "info",
            header = brown(" @@ ")
        )

        # discard cache
        self.clearCache()

        return quickpkg_atoms


    def _runTreeUpdatesMoveAction(self, move_command, quickpkg_queue):
        """
        Method not suited for general purpose usage.
        Executes package name move action passed.
        No need to override.

        -- move action:
        1) move package key to the new name: category + name + atom
        2) update all the dependencies in dependenciesreference to the new key
        3) run fixpackages which will update /var/db/pkg files
        4) automatically run quickpkg() to build the new binary and
           tainted binaries owning tainted iddependency and taint database

        @param move_command: raw treeupdates move action, for example:
            'move x11-foo/bar app-foo/bar'
        @type move_command: string
        @param quickpkg_queue: current package regeneration queue
        @type quickpkg_queue: list
        @return: updated package regeneration queue
        @rtype: list
        """
        dep_from = move_command[0]
        key_from = entropy.tools.dep_getkey(dep_from)
        key_to = move_command[1]
        cat_to = key_to.split("/")[0]
        name_to = key_to.split("/")[1]
        matches = self.atomMatch(dep_from, multiMatch = True)
        iddependencies = set()

        for package_id in matches[0]:

            slot = self.retrieveSlot(package_id)
            old_atom = self.retrieveAtom(package_id)
            new_atom = old_atom.replace(key_from, key_to)

            ### UPDATE DATABASE
            # update category
            self.setCategory(package_id, cat_to)
            # update name
            self.setName(package_id, name_to)
            # update atom
            self.setAtom(package_id, new_atom)

            # look for packages we need to quickpkg again
            quickpkg_queue.add(key_to+":"+slot)

            plugins = self.get_plugins()
            for plugin_id in sorted(plugins):
                plug_inst = plugins[plugin_id]
                exec_rc = plug_inst.treeupdates_move_action_hook(self,
                    package_id)
                if exec_rc:
                    raise RepositoryPluginError(
                        "[treeupdates_move_action_hook] %s: status: %s" % (
                            plug_inst.get_id(), exec_rc,))

        iddeps = self.searchDependency(key_from, like = True, multi = True)
        for iddep in iddeps:
            # update string
            mydep = self.getDependency(iddep)
            mydep_key = entropy.tools.dep_getkey(mydep)
            # avoid changing wrong atoms -> dev-python/qscintilla-python would
            # become x11-libs/qscintilla if we don't do this check
            if mydep_key != key_from:
                continue
            mydep = mydep.replace(key_from, key_to)
            # now update
            # dependstable on server is always re-generated
            self.setDependency(iddep, mydep)
            # we have to repackage also package owning this iddep
            iddependencies |= self.searchPackageIdFromDependencyId(iddep)

        self.commitChanges()
        quickpkg_queue = list(quickpkg_queue)
        for x in range(len(quickpkg_queue)):
            myatom = quickpkg_queue[x]
            myatom = myatom.replace(key_from, key_to)
            quickpkg_queue[x] = myatom
        quickpkg_queue = set(quickpkg_queue)
        for package_id_owner in iddependencies:
            myatom = self.retrieveAtom(package_id_owner)
            if myatom is None:
                # reverse deps table out of sync
                continue
            myatom = myatom.replace(key_from, key_to)
            quickpkg_queue.add(myatom)
        return quickpkg_queue


    def _runTreeUpdatesSlotmoveAction(self, slotmove_command, quickpkg_queue):
        """
        Method not suited for general purpose usage.
        Executes package slot move action passed.
        No need to override.

        -- slotmove action:
        1) move package slot
        2) update all the dependencies in dependenciesreference owning
           same matched atom + slot
        3) run fixpackages which will update /var/db/pkg files
        4) automatically run quickpkg() to build the new
           binary and tainted binaries owning tainted iddependency
           and taint database

        @param slotmove_command: raw treeupdates slot move action, for example:
            'slotmove x11-foo/bar 2 3'
        @type slotmove_command: string
        @param quickpkg_queue: current package regeneration queue
        @type quickpkg_queue: list
        @return: updated package regeneration queue
        @rtype: list
        """
        atom = slotmove_command[0]
        atomkey = entropy.tools.dep_getkey(atom)
        slot_from = slotmove_command[1]
        slot_to = slotmove_command[2]
        matches = self.atomMatch(atom, multiMatch = True)
        iddependencies = set()

        matched_package_ids = matches[0]
        for package_id in matched_package_ids:

            ### UPDATE DATABASE
            # update slot
            self.setSlot(package_id, slot_to)

            # look for packages we need to quickpkg again
            # note: quickpkg_queue is simply ignored if client_repo == True
            quickpkg_queue.add(atom+":"+slot_to)

            # only if we've found VALID matches !
            iddeps = self.searchDependency(atomkey, like = True, multi = True)
            for iddep in iddeps:
                # update string
                mydep = self.getDependency(iddep)
                mydep_key = entropy.tools.dep_getkey(mydep)
                if mydep_key != atomkey:
                    continue
                if not mydep.endswith(":"+slot_from): # probably slotted dep
                    continue
                mydep_match = self.atomMatch(mydep)
                if mydep_match not in matched_package_ids:
                    continue
                mydep = mydep.replace(":"+slot_from, ":"+slot_to)
                # now update
                # dependstable on server is always re-generated
                self.setDependency(iddep, mydep)
                # we have to repackage also package owning this iddep
                iddependencies |= self.searchPackageIdFromDependencyId(iddep)

            plugins = self.get_plugins()
            for plugin_id in sorted(plugins):
                plug_inst = plugins[plugin_id]
                exec_rc = plug_inst.treeupdates_slot_move_action_hook(self,
                    package_id)
                if exec_rc:
                    raise RepositoryPluginError(
                        "[treeupdates_slot_move_action_hook] %s: status: %s" % (
                            plug_inst.get_id(), exec_rc,))

        self.commitChanges()
        for package_id_owner in iddependencies:
            myatom = self.retrieveAtom(package_id_owner)
            if myatom is None:
                # reverse deps table out of sync
                continue
            quickpkg_queue.add(myatom)
        return quickpkg_queue

    def _doTreeupdatesSpmCleanup(self, spm_moves):
        """
        Erase dead Source Package Manager db entries.

        @todo: make more Portage independent (create proper entropy.spm
            methods for dealing with this)
        @param spm_moves: list of raw package name/slot update actions.
        @type spm_moves: list
        """
        # now erase Spm entries if necessary
        for action in spm_moves:
            command = action.split()
            if len(command) < 2:
                continue

            key = command[1]
            category, name = key.split("/", 1)
            dep_key = entropy.tools.dep_getkey(key)

            try:
                spm = get_spm(self)
            except Exception:
                entropy.tools.print_traceback()
                continue

            script_path = spm.get_installed_package_build_script_path(dep_key)
            pkg_path = os.path.dirname(os.path.dirname(script_path))
            if not os.path.isdir(pkg_path):
                # no dir,  no party!
                continue

            mydirs = [os.path.join(pkg_path, x) for x in \
                os.listdir(pkg_path) if \
                entropy.tools.dep_getkey(os.path.join(category, x)) \
                    == dep_key]
            mydirs = [x for x in mydirs if os.path.isdir(x)]

            # now move these dirs
            for mydir in mydirs:
                to_path = os.path.join(etpConst['packagestmpdir'],
                    os.path.basename(mydir))
                mytxt = "%s: %s '%s' %s '%s'" % (
                    bold(_("SPM")),
                    red(_("Moving old entry")),
                    blue(mydir),
                    red(_("to")),
                    blue(to_path),
                )
                self.output(
                    mytxt,
                    importance = 1,
                    level = "warning",
                    header = darkred(" * ")
                )
                if os.path.isdir(to_path):
                    shutil.rmtree(to_path, True)
                    try:
                        os.rmdir(to_path)
                    except OSError:
                        pass
                shutil.move(mydir, to_path)

    def listAllTreeUpdatesActions(self, no_ids_repos = False):
        """
        This method should be considered internal and not suited for general
        audience.
        List all the available "treeupdates" (package names/slots changes
            directives) actions.

        @keyword no_ids_repos: if True, it will just return a 3-length tuple
            list containing [(command, branch, unix_time,), ...]
        @type no_ids_repos: bool
        @return: list of tuples
        @rtype: list
        """
        raise NotImplementedError()

    def retrieveTreeUpdatesActions(self, repository):
        """
        This method should be considered internal and not suited for general
        audience.
        Return all the available "treeupdates (package names/slots changes
            directives) actions for provided repository.

        @param repository: repository identifier
        @type repository: string
        @return: list of raw-string commands to run
        @rtype: list
        """
        raise NotImplementedError()

    def bumpTreeUpdatesActions(self, updates):
        # mainly used to restore a previous table,
        # used by reagent in --initialize
        """
        This method should be considered internal and not suited for general
        audience.
        This method rewrites "treeupdates" metadata in repository.

        @param updates: new treeupdates metadata
        @type updates: list
        """
        raise NotImplementedError()

    def removeTreeUpdatesActions(self, repository):
        """
        This method should be considered internal and not suited for general
        audience.
        This method removes "treeupdates" metadata in repository.

        @param repository: remove treeupdates metadata for provided repository
        @type repository: string
        """
        raise NotImplementedError()

    def insertTreeUpdatesActions(self, updates, repository):
        """
        This method should be considered internal and not suited for general
        audience.
        This method insert "treeupdates" metadata in repository.

        @param updates: new treeupdates metadata
        @type updates: list
        @param repository: insert treeupdates metadata for provided repository
        @type repository: string
        """
        raise NotImplementedError()

    def setRepositoryUpdatesDigest(self, repository, digest):
        """
        This method should be considered internal and not suited for general
        audience.
        Set "treeupdates" checksum (digest) for provided repository.

        @param repository: repository identifier
        @type repository: string
        @param digest: treeupdates checksum string (md5)
        @type digest: string
        """
        raise NotImplementedError()

    def addRepositoryUpdatesActions(self, repository, actions, branch):
        """
        This method should be considered internal and not suited for general
        audience.
        Add "treeupdates" actions for repository and branch provided.

        @param repository: repository identifier
        @type repository: string
        @param actions: list of raw treeupdates action strings
        @type actions: list
        @param branch: branch metadata to bind to the provided actions
        @type branch: string
        """
        raise NotImplementedError()

    def clearPackageSets(self):
        """
        Clear Package sets (group of packages) entries in repository.
        """
        raise NotImplementedError()

    def insertPackageSets(self, sets_data):
        """
        Insert Package sets metadata into repository.

        @param sets_data: dictionary containing package set names as keys and
            list (set) of dependencies as value
        @type sets_data: dict
        """
        raise NotImplementedError()

    def retrievePackageSets(self):
        """
        Return Package sets metadata stored in repository.

        @return: dictionary containing package set names as keys and
            list (set) of dependencies as value
        @rtype: dict
        """
        raise NotImplementedError()

    def retrievePackageSet(self, setname):
        """
        Return dependencies belonging to given package set name.
        This method does not check if the given package set name is
        available and returns an empty list (set) in these cases.

        @param setname: Package set name
        @type setname: string
        @return: list (set) of dependencies belonging to given package set name
        @rtype: set
        """
        raise NotImplementedError()

    def retrieveAtom(self, package_id):
        """
        Return "atom" metadatum for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: atom string
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveBranch(self, package_id):
        """
        Return "branch" metadatum for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: branch metadatum
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveTrigger(self, package_id):
        """
        Return "trigger" script content for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: trigger script content
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveDownloadURL(self, package_id):
        """
        Return "download URL" metadatum for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: download url metadatum
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveDescription(self, package_id):
        """
        Return "description" metadatum for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: package description
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveHomepage(self, package_id):
        """
        Return "homepage" metadatum for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: package homepage
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveSpmUid(self, package_id):
        """
        Return Source Package Manager unique identifier bound to Entropy
        package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: Spm UID or -1 (if not bound, valid for injected packages)
        @rtype: int
        """
        raise NotImplementedError()

    def retrieveSize(self, package_id):
        """
        Return "size" metadatum for given package identifier.
        "size" refers to Entropy package file size in bytes.

        @param package_id: package indentifier
        @type package_id: int
        @return: size of Entropy package for given package identifier
        @rtype: int or None
        """
        raise NotImplementedError()

    def retrieveOnDiskSize(self, package_id):
        """
        Return "on disk size" metadatum for given package identifier.
        "on disk size" refers to unpacked Entropy package file size in bytes,
        which is in other words, the amount of space required on live system
        to have it installed (simplified explanation).

        @param package_id: package indentifier
        @type package_id: int
        @return: on disk size metadatum
        @rtype: int
        """
        raise NotImplementedError()

    def retrieveDigest(self, package_id):
        """
        Return "digest" metadatum for given package identifier.
        "digest" refers to Entropy package file md5 checksum bound to given
        package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: md5 checksum for given package identifier
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveSignatures(self, package_id):
        """
        Return package file extra hashes (sha1, sha256, sha512) for given
        package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: tuple of length 3, sha1, sha256, sha512 package extra
            hashes if available, otherwise the same but with None as values.
        @rtype: tuple
        """
        raise NotImplementedError()

    def retrieveName(self, package_id):
        """
        Return "name" metadatum for given package identifier.
        Attention: package name != atom, the former is just a subset of the
        latter.

        @param package_id: package indentifier
        @type package_id: int
        @return: "name" metadatum for given package identifier
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveKeySplit(self, package_id):
        """
        Return a tuple composed by package category and package name for
        given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: tuple of length 2 composed by (package_category, package_name,)
        @rtupe: tuple or None
        """
        raise NotImplementedError()

    def retrieveKeySlot(self, package_id):
        """
        Return a tuple composed by package key and slot for given package
        identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: tuple of length 2 composed by (package_key, package_slot,)
        @rtupe: tuple or None
        """
        raise NotImplementedError()

    def retrieveKeySlotAggregated(self, package_id):
        """
        Return package key and package slot string (aggregated form through
        ":", for eg.: app-foo/foo:2).
        This method has been implemented for performance reasons.

        @param package_id: package indentifier
        @type package_id: int
        @return: package key + ":" + slot string
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveKeySlotTag(self, package_id):
        """
        Return package key, slot and tag tuple for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: tuple of length 3 providing (package_key, slot, package_tag,)
        @rtype: tuple
        """
        raise NotImplementedError()

    def retrieveVersion(self, package_id):
        """
        Return package version for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: package version
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveRevision(self, package_id):
        """
        Return package Entropy-revision for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: Entropy-revision for given package indentifier
        @rtype: int or None
        """
        raise NotImplementedError()

    def retrieveCreationDate(self, package_id):
        """
        Return creation date for given package identifier.
        Creation date returned is a string representation of UNIX time format.

        @param package_id: package indentifier
        @type package_id: int
        @return: creation date for given package identifier
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveApi(self, package_id):
        """
        Return Entropy API in use when given package identifier was added.

        @param package_id: package indentifier
        @type package_id: int
        @return: Entropy API for given package identifier
        @rtype: int or None
        """
        raise NotImplementedError()

    def retrieveUseflags(self, package_id):
        """
        Return "USE flags" metadatum for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: list (set) of USE flags for given package identifier.
        @rtype: set
        """
        raise NotImplementedError()

    def retrieveEclasses(self, package_id):
        """
        Return "eclass" metadatum for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: list (set) of eclasses for given package identifier
        @rtype: set
        """
        raise NotImplementedError()

    def retrieveSpmPhases(self, package_id):
        """
        Return "Source Package Manager install phases" for given package
        identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: "Source Package Manager available install phases" string
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveSpmRepository(self, package_id):
        """
        Return Source Package Manager source repository used at compile time.

        @param package_id: package indentifier
        @type package_id: int
        @return: Source Package Manager source repository
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveDesktopMime(self, package_id):
        """
        Return file association metadata for package.

        @param package_id: package indentifier
        @type package_id: int
        @return: list of dict() containing file association information
        @rtype: list
        """
        raise NotImplementedError()

    def retrieveProvidedMime(self, package_id):
        """
        Return mime types associated to package. Mimetypes whose package
        can handle.

        @param package_id: package indentifier
        @type package_id: int
        @return: list (set) of mimetypes
        @rtype: set
        """
        raise NotImplementedError()

    def retrieveNeededRaw(self, package_id):
        """
        Return (raw format) "NEEDED" ELF metadata for libraries contained
        in given package.

        @param package_id: package indentifier
        @type package_id: int
        @return: list (set) of "NEEDED" entries contained in ELF objects
            packed into package file
        @rtype: set
        """
        raise NotImplementedError()

    def retrieveNeeded(self, package_id, extended = False, formatted = False):
        """
        Return "NEEDED" elf metadata for libraries contained in given package.

        @param package_id: package indentifier
        @type package_id: int
        @keyword extended: also return ELF class information for every
            library name
        @type extended: bool
        @keyword formatted: properly format output, returning a dictionary with
            library name as key and ELF class as value
        @type formatted: bool
        @return: "NEEDED" metadata for libraries contained in given package.
        @rtype: list or set
        """
        raise NotImplementedError()

    def retrieveProvidedLibraries(self, package_id):
        """
        Return list of library names (from NEEDED ELF metadata) provided by
        given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: list of tuples of length 2 composed by library name and ELF
            class
        @rtype: list
        """
        raise NotImplementedError()

    def retrieveConflicts(self, package_id):
        """
        Return list of conflicting dependencies for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: list (set) of conflicting package dependencies
        @rtype: set
        """
        raise NotImplementedError()

    def retrieveProvide(self, package_id):
        """
        Return list of dependencies/atoms are provided by the given package
        identifier (see Portage documentation about old-style PROVIDEs).

        @param package_id: package indentifier
        @type package_id: int
        @return: list (set) of atoms provided by package
        @rtype: set
        """
        raise NotImplementedError()

    def retrieveDependenciesList(self, package_id, exclude_deptypes = None):
        """
        Return list of dependencies, including conflicts for given package
        identifier.

        @param package_id: package indentifier
        @type package_id: int
        @keyword exclude_deptypes: exclude given dependency types from returned
            data. Please see etpConst['dependency_type_ids'] for valid values.
            Anything != int will raise AttributeError
        @type exclude_deptypes: list
        @return: list (set) of dependencies of package
        @rtype: set
        @raise AttributeError: if exclude_deptypes contains illegal values
        """
        raise NotImplementedError()

    def retrieveBuildDependencies(self, package_id, extended = False):
        """
        Return list of build time package dependencies for given package
        identifier.
        Note: this function is just a wrapper of retrieveDependencies()
        providing deptype (dependency type) = post-dependencies.

        @param package_id: package indentifier
        @type package_id: int
        @keyword extended: return in extended format
        @type extended: bool
        """
        raise NotImplementedError()

    def retrievePostDependencies(self, package_id, extended = False):
        """
        Return list of post-merge package dependencies for given package
        identifier.
        Note: this function is just a wrapper of retrieveDependencies()
        providing deptype (dependency type) = post-dependencies.

        @param package_id: package indentifier
        @type package_id: int
        @keyword extended: return in extended format
        @type extended: bool
        """
        raise NotImplementedError()

    def retrieveManualDependencies(self, package_id, extended = False):
        """
        Return manually added dependencies for given package identifier.
        Note: this function is just a wrapper of retrieveDependencies()
        providing deptype (dependency type) = manual-dependencies.

        @param package_id: package indentifier
        @type package_id: int
        @keyword extended: return in extended format
        @type extended: bool
        """
        raise NotImplementedError()

    def retrieveDependencies(self, package_id, extended = False, deptype = None,
        exclude_deptypes = None):
        """
        Return dependencies for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @keyword extended: return in extended format (list of tuples of length 2
            composed by dependency name and dependency type)
        @type extended: bool
        @keyword deptype: return only given type of dependencies
            see etpConst['dependency_type_ids']['*depend_id'] for dependency type
            identifiers
        @type deptype: bool
        @keyword exclude_deptypes: exclude given dependency types from returned
            data. Please see etpConst['dependency_type_ids'] for valid values.
            Anything != int will raise AttributeError
        @type exclude_deptypes: list
        @return: dependencies of given package
        @rtype: list or set
        @raise AttributeError: if exclude_deptypes contains illegal values
        """
        raise NotImplementedError()

    def retrieveKeywords(self, package_id):
        """
        Return package SPM keyword list for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: list (set) of keywords for given package identifier
        @rtype: set
        """
        raise NotImplementedError()

    def retrieveProtect(self, package_id):
        """
        Return CONFIG_PROTECT (configuration file protection) string
        (containing a list of space reparated paths) metadata for given
        package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: CONFIG_PROTECT string
        @rtype: string
        """
        raise NotImplementedError()

    def retrieveProtectMask(self, package_id):
        """
        Return CONFIG_PROTECT_MASK (mask for configuration file protection)
        string (containing a list of space reparated paths) metadata for given
        package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: CONFIG_PROTECT_MASK string
        @rtype: string
        """
        raise NotImplementedError()

    def retrieveSources(self, package_id, extended = False):
        """
        Return source package URLs for given package identifier.
        "source" as in source code.

        @param package_id: package indentifier
        @type package_id: int
        @keyword extended: 
        @type extended: bool
        @return: if extended is True, dict composed by source URLs as key
            and list of mirrors as value, otherwise just a list (set) of
            source package URLs.
        @rtype: dict or set
        """
        raise NotImplementedError()

    def retrieveAutomergefiles(self, package_id, get_dict = False):
        """
        Return previously merged protected configuration files list and
        their md5 hashes for given package identifier.
        This is part of the "automerge" feature which uses file md5 checksum
        to determine if a protected configuration file can be merged auto-
        matically.

        @param package_id: package indentifier
        @type package_id: int
        @keyword get_dict: return a dictionary with configuration file as key
            and md5 hash as value
        @type get_dict: bool
        @return: automerge metadata for given package identifier
        @rtype: list or set
        """
        raise NotImplementedError()

    def retrieveContent(self, package_id, extended = False,
        formatted = False, insert_formatted = False, order_by = None):
        """
        Return files contained in given package.

        @param package_id: package indentifier
        @type package_id: int
        @keyword extended: return in extended format
        @type extended: bool
        @keyword formatted: return in dict() form
        @type formatted: bool
        @keyword insert_formatted: return in list of tuples form, ready to
            be added with insertContent()
        @keyword order_by: order by string, valid values are:
            "type" (if extended is True), "file" or "package_id"
        @type order_by: string
        @return: content metadata
        @rtype: dict or list or set
        @raise AttributeError: if order_by value is invalid
        """
        raise NotImplementedError()

    def retrieveChangelog(self, package_id):
        """
        Return Source Package Manager ChangeLog for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: ChangeLog content
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveChangelogByKey(self, category, name):
        """
        Return Source Package Manager ChangeLog content for given package
        category and name.

        @param category: package category
        @type category: string
        @param name: package name
        @type name: string
        @return: ChangeLog content
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveSlot(self, package_id):
        """
        Return "slot" metadatum for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: package slot
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveTag(self, package_id):
        """
        Return "tag" metadatum for given package identifier.
        Tagging packages allows, for example, to support multiple
        different, colliding atoms in the same repository and still being
        able to exactly reference them. It's actually used to provide
        versions of external kernel modules for different kernels.

        @param package_id: package indentifier
        @type package_id: int
        @return: tag string
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveMirrorData(self, mirrorname):
        """
        Return available mirror URls for given mirror name.

        @param mirrorname: mirror name (for eg. "openoffice")
        @type mirrorname: string
        @return: list (set) of URLs providing the "openoffice" mirroring service
        @rtype: set
        """
        raise NotImplementedError()

    def retrieveCategory(self, package_id):
        """
        Return category name for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: category where package is in
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveCategoryDescription(self, category):
        """
        Return description text for given category.

        @param category: category name
        @type category: string
        @return: category description dict, locale as key, description as value
        @rtype: dict
        """
        raise NotImplementedError()

    def retrieveLicenseData(self, package_id):
        """
        Return license metadata for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: dictionary composed by license name as key and license text
            as value
        @rtype: dict
        """
        raise NotImplementedError()

    def retrieveLicenseDataKeys(self, package_id):
        """
        Return license names available for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: list (set) of license names which text is available in
            repository
        @rtype: set
        """
        raise NotImplementedError()

    def retrieveLicenseText(self, license_name):
        """
        Return license text for given license name.

        @param license_name: license name (for eg. GPL-2)
        @type license_name: string
        @return: license text
        @rtype: string (raw format) or None
        """
        raise NotImplementedError()

    def retrieveLicense(self, package_id):
        """
        Return "license" metadatum for given package identifier.

        @param package_id: package indentifier
        @type package_id: int
        @return: license string
        @rtype: string or None
        """
        raise NotImplementedError()

    def retrieveCompileFlags(self, package_id):
        """
        Return Compiler flags during building of package.
            (CHOST, CXXFLAGS, LDFLAGS)

        @param package_id: package indentifier
        @type package_id: int
        @return: tuple of length 3 composed by (CHOST, CFLAGS, CXXFLAGS)
        @rtype: tuple
        """
        raise NotImplementedError()

    def retrieveReverseDependencies(self, package_id, atoms = False,
        key_slot = False, exclude_deptypes = None):
        """
        Return reverse (or inverse) dependencies for given package.

        @param package_id: package indentifier
        @type package_id: int
        @keyword atoms: if True, method returns list of atoms
        @type atoms: bool
        @keyword key_slot: if True, method returns list of dependencies in
            key:slot form, example: [('app-foo/bar','2',), ...]
        @type key_slot: bool
        @keyword exclude_deptypes: exclude given dependency types from returned
            data. Please see etpConst['dependency_type_ids'] for valid values.
            Anything != int will raise AttributeError
        @type exclude_deptypes: iterable of ints
        @return: reverse dependency list
        @rtype: list or set
        @raise AttributeError: if exclude_deptypes contains illegal values
        """
        raise NotImplementedError()

    def retrieveUnusedPackageIds(self):
        """
        Return packages (through their identifiers) not referenced by any
        other as dependency (unused packages).

        @return: unused package_ids ordered by atom
        @rtype: list
        """
        raise NotImplementedError()

    def arePackageIdsAvailable(self, package_ids):
        """
        Return whether list of package identifiers are available.
        They must be all available to return True

        @param package_ids: list of package indentifiers
        @type package_ids: iterable
        @return: availability (True if all are available)
        @rtype: bool
        """
        raise NotImplementedError()

    def isPackageIdAvailable(self, package_id):
        """
        Return whether given package identifier is available in repository.

        @param package_id: package indentifier
        @type package_id: int
        @return: availability (True if available)
        @rtype: bool
        """
        raise NotImplementedError()

    def isFileAvailable(self, path, get_id = False):
        """
        Return whether given file path is available in repository (owned by
        one or more packages).

        @param path: path to file or directory
        @type path: string
        @keyword get_id: return list (set) of package_ids owning myfile
        @type get_id: bool
        @return: availability (True if available), when get_id is True,
            it returns a list (set) of package_ids owning myfile
        @rtype: bool or set
        """
        raise NotImplementedError()

    def resolveNeeded(self, needed, elfclass = -1, extended = False):
        """
        Resolve NEEDED ELF entry (a library name) to package_ids owning given
        needed (stressing, needed = library name)

        @param needed: library name
        @type needed: string
        @keyword elfclass: look for library name matching given ELF class
        @type elfclass: int
        @keyword extended: return a list of tuple of length 2, first element
            is package_id, second is actual library path
        @type extended: bool
        @return: list of packages owning given library
        @rtype: list or set
        """
        raise NotImplementedError()

    def isNeededAvailable(self, needed):
        """
        Return whether NEEDED ELF entry (library name) is available in
        repository.
        Returns NEEDED entry identifier

        @param needed: NEEDED ELF entry (library name)
        @type needed: string
        @return: NEEDED entry identifier or -1 if not found
        @rtype: int
        """
        raise NotImplementedError()

    def isSpmUidAvailable(self, spm_uid):
        """
        Return whether Source Package Manager package identifier is available
        in repository.

        @param spm_uid: Source Package Manager package identifier
        @type spm_uid: int
        @return: availability (True, if available)
        @rtype: bool
        """
        raise NotImplementedError()

    def isSpmUidTrashed(self, spm_uid):
        """
        Return whether Source Package Manager package identifier has been
        trashed. One is trashed when it gets removed from a repository while
        still sitting there in place on live system. This is a trick to allow
        multiple-repositories management to work fine when shitting around.

        @param spm_uid: Source Package Manager package identifier
        @type spm_uid: int
        @return: availability (True, if available)
        @rtype: bool
        """
        raise NotImplementedError()

    def isLicenseDataKeyAvailable(self, license_name):
        """
        Return whether license name is available in License database, which is
        the one containing actual license texts.

        @param license_name: license name which license text is available
        @type license_name: string
        @return: availability (True, if available)
        @rtype: bool
        """
        raise NotImplementedError()

    def isLicenseAccepted(self, license_name):
        """
        Return whether given license (through its name) has been accepted by
        user.

        @param license_name: license name
        @type license_name: string
        @return: if license name has been accepted by user
        @rtype: bool
        """
        raise NotImplementedError()

    def acceptLicense(self, license_name):
        """
        Mark license name as accepted by user.
        Only and only if user is allowed to accept them:
            - in entropy group
            - db not open in read only mode
        Attention: call this method from your subclass, otherwise
        EntropyRepositoryPlugins won't be notified.

        @param license_name: license name
        @type license_name: string
        """
        plugins = self.get_plugins()
        for plugin_id in sorted(plugins):
            plug_inst = plugins[plugin_id]
            exec_rc = plug_inst.accept_license_hook(self)
            if exec_rc:
                raise RepositoryPluginError(
                    "[accept_license_hook] %s: status: %s" % (
                        plug_inst.get_id(), exec_rc,))

    def isSystemPackage(self, package_id):
        """
        Return whether package is part of core system (though, a system
        package).

        @param package_id: package indentifier
        @type package_id: int
        @return: if True, package is part of core system
        @rtype: bool
        """
        raise NotImplementedError()

    def isInjected(self, package_id):
        """
        Return whether package has been injected into repository (means that
        will be never ever removed due to colliding scope when other
        packages will be added).

        @param package_id: package indentifier
        @type package_id: int
        @return: injection status (True if injected)
        @rtype: bool
        """
        raise NotImplementedError()

    def searchProvidedVirtualPackage(self, keyword):
        """
        Search in old-style Portage PROVIDE metadata.
        @todo: rewrite docstring :-)

        @param keyword: search term
        @type keyword: string
        @return: found PROVIDE metadata
        @rtype: list
        """
        raise NotImplementedError()

    def searchBelongs(self, bfile, like = False):
        """
        Search packages which given file path belongs to.

        @param bfile: file path to search
        @type bfile: string
        @keyword like: do not match exact case
        @type like: bool
        @return: list (set) of package identifiers owning given file
        @rtype: set
        """
        raise NotImplementedError()

    def searchEclassedPackages(self, eclass, atoms = False):
        """
        Search packages which their Source Package Manager counterpar are using
        given eclass.

        @param eclass: eclass name to search
        @type eclass: string
        @keyword atoms: return list of atoms instead of package identifiers
        @type atoms: bool
        @return: list of packages using given eclass
        @rtype: set or list
        """
        raise NotImplementedError()

    def searchTaggedPackages(self, tag, atoms = False):
        """
        Search packages which "tag" metadatum matches the given one.

        @param tag: tag name to search
        @type tag: string
        @keyword atoms: return list of atoms instead of package identifiers
        @type atoms: bool
        @return: list of packages using given tag
        @rtype: set or list
        """
        raise NotImplementedError()

    def searchRevisionedPackages(self, revision):
        """
        Search packages which "revision" metadatum matches the given one.

        @param revision: Entropy revision to search
        @type revision: string
        @return: list of packages using given tag
        @rtype: set
        """
        raise NotImplementedError()

    def searchLicense(self, keyword, just_id = False):
        """
        Search packages using given license (mylicense).

        @param keyword: license name to search
        @type keyword: string
        @keyword just_id: just return package identifiers (returning set())
        @type just_id: bool
        @return: list of packages using given license
        @rtype: set or list
        @todo: check if is_valid_string is really required
        """
        raise NotImplementedError()

    def searchSlotted(self, keyword, just_id = False):
        """
        Search packages with given slot string.

        @param keyword: slot to search
        @type keyword: string
        @keyword just_id: just return package identifiers (returning set())
        @type just_id: bool
        @return: list of packages using given slot
        @rtype: set or list
        """
        raise NotImplementedError()

    def searchKeySlot(self, key, slot):
        """
        Search package with given key and slot

        @param key: package key
        @type key: string
        @param slot: package slot
        @type slot: string
        @return: list (set) of package identifiers
        @rtype: set
        """
        raise NotImplementedError()

    def searchNeeded(self, needed, elfclass = -1, like = False):
        """
        Search packages that need given NEEDED ELF entry (library name).
        You must implement "*" wildcard support if like is True.

        @param needed: NEEDED ELF entry (shared object library name)
        @type needed: string
        @param elfclass: search NEEDEDs only with given ELF class
        @type elfclass: int
        @keyword like: do not match exact case
        @type like: bool
        @return: list (set) of package identifiers
        @rtype: set
        """
        raise NotImplementedError()

    def searchDependency(self, dep, like = False, multi = False,
        strings = False):
        """
        Search dependency name in repository.
        Returns dependency identifier (iddependency) or dependency strings
        (if strings argument is True).

        @param dep: dependency name
        @type dep: string
        @keyword like: do not match exact case
        @type like: bool
        @keyword multi: return all the matching dependency names
        @type multi: bool
        @keyword strings: return dependency names rather than dependency
            identifiers
        @type strings: bool
        @return: list of dependency identifiers (if multi is True) or
            strings (if strings is True) or dependency identifier
        @rtype: int or set
        """
        raise NotImplementedError()

    def searchPackageIdFromDependencyId(self, dependency_id):
        """
        Search package identifiers owning dependency given (in form of
        dependency identifier).

        @param dependency_id: dependency identifier
        @type dependency_id: int
        @return: list (set) of package identifiers owning given dependency
            identifier
        @rtype: set
        """
        raise NotImplementedError()

    def searchSets(self, keyword):
        """
        Search package sets in repository using given search keyword.

        @param keyword: package set name to search
        @type keyword: string
        @return: list (set) of package sets available matching given keyword
        @rtype: set
        """
        raise NotImplementedError()

    def searchProvidedMime(self, mimetype):
        """
        Search package identifiers owning given mimetype. Results are returned
        sorted by package name.

        @param mimetype: mimetype to search
        @type mimetype: string
        @return: list of package indentifiers owning given mimetype.
        @rtype: list
        """
        raise NotImplementedError()

    def searchSimilarPackages(self, keyword, atom = False):
        """
        Search similar packages (basing on package string given by mystring
        argument) using SOUNDEX algorithm.

        @param keyword: package string to search
        @type keyword: string
        @keyword atom: return full atoms instead of package names
        @type atom: bool
        @return: list of similar package names
        @rtype: set
        """
        raise NotImplementedError()

    def searchPackages(self, keyword, sensitive = False, slot = None,
            tag = None, order_by = None, just_id = False):
        """
        Search packages using given package name "keyword" argument.

        @param keyword: package string
        @type keyword: string
        @keyword sensitive: case sensitive?
        @type sensitive: bool
        @keyword slot: search matching given slot
        @type slot: string
        @keyword tag: search matching given package tag
        @type tag: string
        @keyword order_by: order results by "atom", "package_id", "branch",
            "name", "version", "versiontag", "revision", "slot"
        @type order_by: string
        @keyword just_id: just return package identifiers (returning set())
        @type just_id: bool
        @return: packages found matching given search criterias
        @rtype: set or list
        @raise AttributeError: if order_by value is invalid
        """
        raise NotImplementedError()

    def searchDescription(self, keyword, just_id = False):
        """
        Search packages using given description string as keyword.

        @param keyword: description sub-string to search
        @type keyword: string
        @keyword just_id: if True, only return a list of Entropy package
            identifiers
        @type just_id: bool
        @return: list of tuples of length 2 containing atom and package_id
            values. While if just_id is True, return a list (set) of package_ids
        @rtype: list or set
        """
        raise NotImplementedError()

    def searchHomepage(self, keyword, just_id = False):
        """
        Search packages using given homepage string as keyword.

        @param keyword: description sub-string to search
        @type keyword: string
        @keyword just_id: if True, only return a list of Entropy package
            identifiers
        @type just_id: bool
        @return: list of tuples of length 2 containing atom and package_id
            values. While if just_id is True, return a list (set) of package_ids
        @rtype: list or set
        """
        raise NotImplementedError()

    def searchName(self, keyword, sensitive = False, just_id = False):
        """
        Search packages by package name.

        @param keyword: package name to search
        @type keyword: string
        @keyword sensitive: case sensitive?
        @type sensitive: bool
        @keyword just_id: return list of package identifiers (set()) otherwise
            return a list of tuples of length 2 containing atom and package_id
            values
        @type just_id: bool
        @return: list of packages found
        @rtype: list or set
        """
        raise NotImplementedError()

    def searchCategory(self, keyword, like = False):
        """
        Search packages by category name.

        @param keyword: category name
        @type keyword: string
        @keyword like: do not match exact case
        @type like: bool
        @return: list of tuples of length 2 containing atom and package_id
            values
        @rtype: list
        """
        raise NotImplementedError()

    def searchNameCategory(self, name, category, sensitive = False,
        just_id = False):
        """
        Search packages matching given name and category strings.

        @param name: package name to search
        @type name: string
        @param category: package category to search
        @type category: string
        @keyword sensitive: case sensitive?
        @type sensitive: bool
        @keyword just_id: return list of package identifiers (set()) otherwise
            return a list of tuples of length 2 containing atom and package_id
            values
        @type just_id: bool
        @return: list of packages found
        @rtype: list or set
        """
        raise NotImplementedError()

    def isPackageScopeAvailable(self, atom, slot, revision):
        """
        Return whether given package scope is available.
        Also check if package found is masked and return masking reason
        identifier.

        @param atom: package atom string
        @type atom: string
        @param slot: package slot string
        @type slot: string
        @param revision: entropy package revision
        @type revision: int
        @return: tuple composed by (package_id or -1, idreason or 0,)
        @rtype: tuple
        """
        raise NotImplementedError()

    def isBranchMigrationAvailable(self, repository, from_branch, to_branch):
        """
        Returns whether branch migration metadata given by the provided key
        (repository, from_branch, to_branch,) is available.

        @param repository: repository identifier
        @type repository: string
        @param from_branch: original branch
        @type from_branch: string
        @param to_branch: destination branch
        @type to_branch: string
        @return: tuple composed by (1)post migration script md5sum and
            (2)post upgrade script md5sum
        @rtype: tuple
        """
        raise NotImplementedError()

    def listAllPackages(self, get_scope = False, order_by = None):
        """
        List all packages in repository.

        @keyword get_scope: return also entropy package revision
        @type get_scope: bool
        @keyword order_by: order by "atom", "idpackage", "package_id", "branch",
            "name", "version", "versiontag", "revision", "slot"
        @type order_by: string
        @return: list of tuples of length 3 (or 4 if get_scope is True),
            containing (atom, package_id, branch,) if get_scope is False and
            (package_id, atom, slot, revision,) if get_scope is True
        @rtype: list
        @raise AttributeError: if order_by value is invalid
        """
        raise NotImplementedError()

    def listPackageIdsInCategoryId(self, category_id, order_by = None):
        """
        List package identifiers available in given category identifier.

        @param category_id: cateogory identifier
        @type category_id: int
        @keyword order_by: order by "atom", "idpackage", "package_id", "branch",
            "name", "version", "versiontag", "revision", "slot"
        @type order_by: string
        @return: list (set) of available package identifiers in category.
        @rtype: set
        @raise AttributeError: if order_by value is invalid
        """
        raise NotImplementedError()

    def listAllPackageIds(self, order_by = None):
        """
        List all package identifiers available in repository.

        @keyword order_by: order by "atom", "idpackage", "package_id", "branch",
            "name", "version", "versiontag", "revision", "slot"
        @type order_by: string
        @return: list (if order_by) or set of package identifiers
        @rtype: list or set
        @raise AttributeError: if order_by value is invalid
        """

    def listAllSpmUids(self):
        """
        List all Source Package Manager unique package identifiers bindings
        with packages in repository.
        @return: list of tuples of length 2 composed by (spm_uid, package_id,)
        @rtype: list
        """
        raise NotImplementedError()

    def listAllDownloads(self, do_sort = True, full_path = False):
        """
        List all package download URLs stored in repository.

        @keyword do_sort: sort by name
        @type do_sort: bool
        @keyword full_path: return full URL (not just package file name)
        @type full_path: bool
        @return: list (or set if do_sort is True) of package download URLs
        @rtype: list or set
        """
        raise NotImplementedError()

    def listAllFiles(self, clean = False, count = False):
        """
        List all file paths owned by packaged stored in repository.

        @keyword clean: return a clean list (not duplicates)
        @type clean: bool
        @keyword count: count elements and return number
        @type count: bool
        @return: list of files available or their count
        @rtype: int or list or set
        """
        raise NotImplementedError()

    def listAllCategories(self, order_by = None):
        """
        List all categories available in repository.

        @keyword order_by: order by "category", "category_id"
        @type order_by: string
        @return: list of tuples of length 2 composed by (category_id, category,)
        @rtype: list
        @raise AttributeError: if order_by value is invalid
        """
        raise NotImplementedError()

    def listConfigProtectEntries(self, mask = False):
        """
        List CONFIG_PROTECT* entries (configuration file/directories
        protection).

        @keyword mask: return CONFIG_PROTECT_MASK metadata instead of
            CONFIG_PROTECT
        @type mask: bool
        @return: list of protected/masked directories
        @rtype: list
        """
        raise NotImplementedError()

    def switchBranch(self, package_id, tobranch):
        """
        Switch branch string in repository to new value.

        @param package_id: package identifier
        @type package_id: int
        @param tobranch: new branch value
        @type tobranch: string
        """
        raise NotImplementedError()

    def getSetting(self, setting_name):
        """
        Return stored Repository setting.
        For currently supported setting_name values look at
        EntropyRepository._SETTING_KEYS.

        @param setting_name: name of repository setting
        @type setting_name: string
        @return: setting value
        @rtype: string
        @raise KeyError: if setting_name is not valid or available
        """
        raise NotImplementedError()

    def validateDatabase(self):
        """
        Validates Entropy repository by doing basic integrity checks.

        @raise SystemDatabaseError: when repository is not reliable
        """
        raise NotImplementedError()

    def alignDatabases(self, dbconn, force = False, output_header = "  ",
        align_limit = 300):
        """
        Align packages contained in foreign repository "dbconn" and this
        instance.

        @param dbconn: foreign repository instance
        @type dbconn: entropy.db.EntropyRepository
        @keyword force: force alignment even if align_limit threshold is
            exceeded
        @type force: bool
        @keyword output_header: output header for printing purposes
        @type output_header: string
        @keyword align_limit: threshold within alignment is done if force is
            False
        @type align_limit: int
        @return: alignment status (0 = all good; 1 = dbs checksum not matching;
            -1 = nothing to do)
        @rtype: int
        """
        raise NotImplementedError()

    def importRepository(self, dumpfile, dbfile):
        """
        Import SQLite3 dump file to this database.

        @param dumpfile: SQLite3 dump file to read
        @type dumpfile: string
        @param dbfile: database file to write to
        @type dbfile: string
        @return: sqlite3 import return code
        @rtype: int
        @raise AttributeError: if given paths are invalid
        """
        raise NotImplementedError()

    def exportRepository(self, dumpfile, gentle_with_tables = True,
        exclude_tables = None):
        """
        Export running SQLite3 database to file.

        @param dumpfile: dump file object to write to
        @type dumpfile: file object (hint: open())
        @keyword gentle_with_tables: append "IF NOT EXISTS" to "CREATE TABLE"
            statements
        @type gentle_with_tables: bool
        """
        raise NotImplementedError()

    def checksum(self, do_order = False, strict = True,
        strings = True, include_signatures = False):
        """
        Get Repository metadata checksum, useful for integrity verification.
        Note: result is cached in EntropyRepository.live_cache (dict).

        @keyword do_order: order metadata collection alphabetically
        @type do_order: bool
        @keyword strict: improve checksum accuracy
        @type strict: bool
        @keyword strings: return checksum in md5 hex form
        @type strings: bool
        @keyword include_signatures: also include packages signatures (GPG,
            SHA1, SHA2, etc) into returned hash
        @type include_signatures: bool
        @return: repository checksum
        @rtype: string
        """
        raise NotImplementedError()

    def storeInstalledPackage(self, package_id, repoid, source = 0):
        """
        Note: this is used by installed packages repository (also known as
        client db).
        Add package identifier to the "installed packages table",
        which contains repository identifier from where package has been
        installed and its install request source (user, pulled in
        dependency, etc).

        @param package_id: package indentifier
        @type package_id: int
        @param repoid: repository identifier
        @type repoid: string
        @param source: source identifier (pleas see:
            etpConst['install_sources'])
        @type source: int
        """
        raise NotImplementedError()

    def getInstalledPackageRepository(self, package_id):
        """
        Note: this is used by installed packages repository (also known as
        client db).
        Return repository identifier stored inside the "installed packages
        table".

        @param package_id: package indentifier
        @type package_id: int
        @return: repository identifier
        @rtype: string or None
        """
        raise NotImplementedError()

    def dropInstalledPackageFromStore(self, package_id):
        """
        Note: this is used by installed packages repository (also known as
        client db).
        Remove installed package metadata from "installed packages table".
        Note: this just removes extra metadata information such as repository
        identifier from where package has been installed and its install
        request source (user, pulled in dependency, etc).
        This method DOES NOT remove package from repository (see
        removePackage() instead).

        @param package_id: package indentifier
        @type package_id: int
        """
        raise NotImplementedError()

    def storeSpmMetadata(self, package_id, blob):
        """
        This method stores Source Package Manager package metadata inside
        repository.

        @param package_id: package indentifier
        @type package_id: int
        @param blob: metadata blob
        @type blob: string or buffer
        """
        raise NotImplementedError()

    def retrieveSpmMetadata(self, package_id):
        """
        This method retrieves Source Package Manager package metadata stored
        inside repository.

        @param package_id: package indentifier
        @type package_id: int
        @return: stored metadata
        @rtype: buffer
        """
        raise NotImplementedError()

    def retrieveBranchMigration(self, to_branch):
        """
        This method returns branch migration metadata stored in Entropy
        Client database (installed packages database). It is used to
        determine whether to run per-repository branch migration scripts.

        @param to_branch: usually the current branch string
        @type to_branch: string
        @return: branch migration metadata contained in database
        @rtype: dict
        """
        raise NotImplementedError()

    def dropContent(self):
        """
        Drop all "content" metadata from repository, usually a memory hog.
        Content metadata contains files and directories owned by packages.
        """
        raise NotImplementedError()

    def dropChangelog(self):
        """
        Drop all packages' ChangeLogs metadata from repository, a memory hog.
        """
        raise NotImplementedError()

    def dropGpgSignatures(self):
        """
        Drop all packages' GPG signatures.
        """
        raise NotImplementedError()

    def dropAllIndexes(self):
        """
        Drop all repository metadata indexes. Not cache!
        """
        raise NotImplementedError()

    def createAllIndexes(self):
        """
        Create all the repository metadata indexes internally available.
        """
        raise NotImplementedError()

    def regenerateSpmUidMapping(self):
        """
        Regenerate Source Package Manager <-> Entropy package identifiers
        mapping.
        This method will use the Source Package Manger interface.
        """
        raise NotImplementedError()

    def clearTreeupdatesEntries(self, repository):
        """
        This method should be considered internal and not suited for general
        audience. Clear "treeupdates" metadata for given repository identifier.

        @param repository: repository identifier
        @type repository: string
        """
        raise NotImplementedError()

    def resetTreeupdatesDigests(self):
        """
        This method should be considered internal and not suited for general
        audience. Reset "treeupdates" digest metadata.
        """
        raise NotImplementedError()

    def moveSpmUidsToBranch(self, to_branch):
        """
        Note: this is not intended for general audience.
        Move "branch" metadata contained in Source Package Manager package
        identifiers binding metadata to new value given by "from_branch"
        argument.

        @param to_branch: new branch string
        @type to_branch: string
        @keyword from_branch: old branch string
        @type from_branch: string
        """
        raise NotImplementedError()

    # Update status flags, self explanatory.
    REPOSITORY_ALREADY_UPTODATE = -1
    REPOSITORY_NOT_AVAILABLE = -2
    REPOSITORY_GENERIC_ERROR = -3
    REPOSITORY_CHECKSUM_ERROR = -4
    REPOSITORY_PERMISSION_DENIED_ERROR = -5
    REPOSITORY_UPDATED_OK = 0

    @staticmethod
    def update(entropy_client, repository_id, force, gpg):
        """
        Update the content of this repository. Every subclass can implement
        its own update way.
        This method must return a status code that can be either
        EntropyRepositoryBase.REPOSITORY_ALREADY_UPTODATE or
        EntropyRepositoryBase.REPOSITORY_NOT_AVAILABLE or
        EntropyRepositoryBase.REPOSITORY_GENERIC_ERROR or
        EntropyRepositoryBase.REPOSITORY_CHECKSUM_ERROR or
        EntropyRepositoryBase.REPOSITORY_UPDATED_OK
        If your repository is not supposed to be remotely updated, just
        ignore this method.
        Otherwise, if you intend to implement this method, make sure that
        any unprivileged call raises entropy.exceptions.PermissionDenied().
        Only superuser should call this method.

        @param entropy_client: Entropy Client based object
        @type entropy_client: entropy.client.interfaces.Client
        @param repository_id: repository identifier
        @type repository_id: string
        @param force: force update anyway
        @type force: bool
        @param gpg: GPG feature enable
        @type gpg: bool
        @return: status code
        @rtype: int
        """
        raise NotImplementedError()

    @staticmethod
    def revision(repository_id):
        """
        Returns the repository local revision in int format or None, if
        no revision is available.

        @param repository_id: repository identifier
        @type repository_id: string
        @return: repository revision
        @rtype: int or None
        @raise KeyError: if repository is not available
        """
        raise NotImplementedError()

    @staticmethod
    def remote_revision(repository_id):
        """
        Returns the repository remote revision in int format or None, if
        no revision is available.

        @param repository_id: repository identifier
        @type repository_id: string
        @return: repository revision
        @rtype: int or None
        @raise KeyError: if repository is not available
        """
        raise NotImplementedError()

    def _maskFilter_live(self, package_id, reponame):

        ref = self._settings['pkg_masking_reference']
        if (package_id, reponame) in \
            self._settings['live_packagemasking']['mask_matches']:

            # do not cache this
            return -1, ref['user_live_mask']

        elif (package_id, reponame) in \
            self._settings['live_packagemasking']['unmask_matches']:

            return package_id, ref['user_live_unmask']

    def _maskFilter_user_package_mask(self, package_id, reponame, live):

        mykw = "%smask_ids" % (reponame,)
        user_package_mask_ids = self._settings.get(mykw)

        if not isinstance(user_package_mask_ids, (list, set)):
            user_package_mask_ids = set()

            for atom in self._settings['mask']:
                matches, r = self.atomMatch(atom, multiMatch = True,
                    maskFilter = False)
                if r != 0:
                    continue
                user_package_mask_ids |= set(matches)

            self._settings[mykw] = user_package_mask_ids

        if package_id in user_package_mask_ids:
            # sorry, masked
            ref = self._settings['pkg_masking_reference']
            myr = ref['user_package_mask']

            try:

                cl_data = self._settings[self.__cs_plugin_id]
                validator_cache = cl_data['masking_validation']['cache']
                validator_cache[(package_id, reponame, live)] = -1, myr

            except KeyError: # system settings client plugin not found
                pass

            return -1, myr

    def _maskFilter_user_package_unmask(self, package_id, reponame,
        live):

        # see if we can unmask by just lookin into user
        # package.unmask stuff -> self._settings['unmask']
        mykw = "%sunmask_ids" % (reponame,)
        user_package_unmask_ids = self._settings.get(mykw)

        if not isinstance(user_package_unmask_ids, (list, set)):

            user_package_unmask_ids = set()
            for atom in self._settings['unmask']:
                matches, r = self.atomMatch(atom, multiMatch = True,
                    maskFilter = False)
                if r != 0:
                    continue
                user_package_unmask_ids |= set(matches)

            self._settings[mykw] = user_package_unmask_ids

        if package_id in user_package_unmask_ids:

            ref = self._settings['pkg_masking_reference']
            myr = ref['user_package_unmask']
            try:

                cl_data = self._settings[self.__cs_plugin_id]
                validator_cache = cl_data['masking_validation']['cache']
                validator_cache[(package_id, reponame, live)] = package_id, myr

            except KeyError: # system settings client plugin not found
                pass

            return package_id, myr

    def _maskFilter_packages_db_mask(self, package_id, reponame, live):

        # check if repository packages.db.mask needs it masked
        repos_mask = {}
        client_plg_id = etpConst['system_settings_plugins_ids']['client_plugin']
        client_settings = self._settings.get(client_plg_id, {})
        if client_settings:
            repos_mask = client_settings['repositories']['mask']

        repomask = repos_mask.get(reponame)
        if isinstance(repomask, (list, set)):

            # first, seek into generic masking, all branches
            # (below) avoid issues with repository names
            mask_repo_id = "%s_ids@@:of:%s" % (reponame, reponame,)
            repomask_ids = repos_mask.get(mask_repo_id)

            if not isinstance(repomask_ids, set):
                repomask_ids = set()
                for atom in repomask:
                    matches, r = self.atomMatch(atom, multiMatch = True,
                        maskFilter = False)
                    if r != 0:
                        continue
                    repomask_ids |= set(matches)
                repos_mask[mask_repo_id] = repomask_ids

            if package_id in repomask_ids:

                ref = self._settings['pkg_masking_reference']
                myr = ref['repository_packages_db_mask']

                try:

                    plg_id = self.__cs_plugin_id
                    cl_data = self._settings[plg_id]
                    validator_cache = cl_data['masking_validation']['cache']
                    validator_cache[(package_id, reponame, live)] = -1, myr

                except KeyError: # system settings client plugin not found
                    pass

                return -1, myr

    def _maskFilter_package_license_mask(self, package_id, reponame,
        live):

        if not self._settings['license_mask']:
            return

        mylicenses = self.retrieveLicense(package_id)
        mylicenses = mylicenses.strip().split()
        lic_mask = self._settings['license_mask']
        for mylicense in mylicenses:

            if mylicense not in lic_mask:
                continue

            ref = self._settings['pkg_masking_reference']
            myr = ref['user_license_mask']
            try:

                cl_data = self._settings[self.__cs_plugin_id]
                validator_cache = cl_data['masking_validation']['cache']
                validator_cache[(package_id, reponame, live)] = -1, myr

            except KeyError: # system settings client plugin not found
                pass

            return -1, myr

    def _maskFilter_keyword_mask(self, package_id, reponame, live):

        # WORKAROUND for buggy entries
        # ** is fine then
        # TODO: remove this before 31-12-2011
        mykeywords = self.retrieveKeywords(package_id)
        if mykeywords == set([""]):
            mykeywords = set(['**'])

        mask_ref = self._settings['pkg_masking_reference']

        # firstly, check if package keywords are in etpConst['keywords']
        # (universal keywords have been merged from package.keywords)
        same_keywords = etpConst['keywords'] & mykeywords
        if same_keywords:
            myr = mask_ref['system_keyword']
            try:

                cl_data = self._settings[self.__cs_plugin_id]
                validator_cache = cl_data['masking_validation']['cache']
                validator_cache[(package_id, reponame, live)] = package_id, myr

            except KeyError: # system settings client plugin not found
                pass

            return package_id, myr

        # if we get here, it means we didn't find mykeywords
        # in etpConst['keywords']
        # we need to seek self._settings['keywords']
        # seek in repository first
        keyword_repo = self._settings['keywords']['repositories']

        for keyword in list(keyword_repo.get(reponame, {}).keys()):

            if keyword not in mykeywords:
                continue

            keyword_data = keyword_repo[reponame].get(keyword)
            if not keyword_data:
                continue

            if "*" in keyword_data:
                # all packages in this repo with keyword "keyword" are ok
                myr = mask_ref['user_repo_package_keywords_all']
                try:

                    plg_id = self.__cs_plugin_id
                    cl_data = self._settings[plg_id]
                    validator_cache = cl_data['masking_validation']['cache']
                    validator_cache[(package_id, reponame, live)] = \
                        package_id, myr

                except KeyError: # system settings client plugin not found
                    pass

                return package_id, myr

            kwd_key = "%s_ids" % (keyword,)
            keyword_data_ids = keyword_repo[reponame].get(kwd_key)
            if not isinstance(keyword_data_ids, set):

                keyword_data_ids = set()
                for atom in keyword_data:
                    matches, r = self.atomMatch(atom, multiMatch = True,
                        maskFilter = False)
                    if r != 0:
                        continue
                    keyword_data_ids |= matches

                keyword_repo[reponame][kwd_key] = keyword_data_ids

            if package_id in keyword_data_ids:

                myr = mask_ref['user_repo_package_keywords']
                try:

                    plg_id = self.__cs_plugin_id
                    cl_data = self._settings[plg_id]
                    validator_cache = cl_data['masking_validation']['cache']
                    validator_cache[(package_id, reponame, live)] = \
                        package_id, myr

                except KeyError: # system settings client plugin not found
                    pass
                return package_id, myr

        keyword_pkg = self._settings['keywords']['packages']

        # if we get here, it means we didn't find a match in repositories
        # so we scan packages, last chance
        for keyword in list(keyword_pkg.keys()):
            # use .keys() because keyword_pkg gets modified during iteration

            # first of all check if keyword is in mykeywords
            if keyword not in mykeywords:
                continue

            keyword_data = keyword_pkg.get(keyword)
            if not keyword_data:
                continue

            kwd_key = "%s_ids" % (keyword,)
            keyword_data_ids = keyword_pkg.get(reponame+kwd_key)

            if not isinstance(keyword_data_ids, (list, set)):
                keyword_data_ids = set()
                for atom in keyword_data:
                    # match atom
                    matches, r = self.atomMatch(atom, multiMatch = True,
                        maskFilter = False)
                    if r != 0:
                        continue
                    keyword_data_ids |= matches

                keyword_pkg[reponame+kwd_key] = keyword_data_ids

            if package_id in keyword_data_ids:

                # valid!
                myr = mask_ref['user_package_keywords']
                try:

                    plg_id = self.__cs_plugin_id
                    cl_data = self._settings[plg_id]
                    validator_cache = cl_data['masking_validation']['cache']
                    validator_cache[(package_id, reponame, live)] = \
                        package_id, myr

                except KeyError: # system settings client plugin not found
                    pass

                return package_id, myr


        ## if we get here, it means that pkg it keyword masked
        ## and we should look at the very last resort, per-repository
        ## package keywords
        # check if repository contains keyword unmasking data

        plg_id = self.__cs_plugin_id
        cl_data = self._settings.get(plg_id)
        if cl_data is None:
            # SystemSettings Entropy Client plugin not available
            return
        # let's see if something is available in repository config
        repo_keywords = cl_data['repositories']['repos_keywords'].get(reponame)
        if repo_keywords is None:
            # nopers, sorry!
            return

        # check universal keywords
        same_keywords = repo_keywords.get('universal') & mykeywords
        if same_keywords:
            # universal keyword matches!
            myr = mask_ref['repository_packages_db_keywords']
            validator_cache = cl_data['masking_validation']['cache']
            validator_cache[(package_id, reponame, live)] = \
                package_id, myr
            return package_id, myr

        ## if we get here, it means that even universal masking failed
        ## and we need to look at per-package settings
        repo_settings = repo_keywords.get('packages')
        if not repo_settings:
            # it's empty, not worth checking
            return

        cached_key = "packages_ids"
        keyword_data_ids = repo_keywords.get(cached_key)
        if not isinstance(keyword_data_ids, dict):
            # create cache

            keyword_data_ids = {}
            for atom, values in list(repo_settings.items()):
                matches, r = self.atomMatch(atom, multiMatch = True,
                    maskFilter = False)
                if r != 0:
                    continue
                for match in matches:
                    obj = keyword_data_ids.setdefault(match, set())
                    obj.update(values)

            repo_keywords[cached_key] = keyword_data_ids

        pkg_keywords = keyword_data_ids.get(package_id, set())
        if "**" in pkg_keywords:
            same_keywords = True
        else:
            same_keywords = pkg_keywords & etpConst['keywords']
        if same_keywords:
            # found! this pkg is not masked, yay!
            myr = mask_ref['repository_packages_db_keywords']
            validator_cache = cl_data['masking_validation']['cache']
            validator_cache[(package_id, reponame, live)] = \
                package_id, myr
            return package_id, myr

    def maskFilter(self, package_id, live = True):
        """
        Return whether given package identifier is available to user or not,
        reading package masking metadata stored in SystemSettings.

        @param package_id: package indentifier
        @type package_id: int
        @keyword live: use live masking feature
        @type live: bool
        @return: tuple composed by package_id and masking reason. If package_id
            returned package_id value == -1, it means that package is masked
            and a valid masking reason identifier is returned as second
            value of the tuple (see SystemSettings['pkg_masking_reasons'])
        @rtype: tuple
        """
        if self.reponame == etpConst['clientdbid']:
            return package_id, 0

        reponame = self.reponame[len(etpConst['dbnamerepoprefix']):]
        try:
            cl_data = self._settings[self.__cs_plugin_id]
            validator_cache = cl_data['masking_validation']['cache']
        except KeyError: # plugin does not exist
            validator_cache = {} # fake

        if validator_cache:
            cached = validator_cache.get((package_id, reponame, live))
            if cached is not None:
                return cached

        # use on-disk cache?
        cached = self.__atomMatchFetchCache(("idpackageValidator",
            package_id, live))
        if cached is not None:
            return cached

        def push_cache(package_id, live, result):
            self.__atomMatchStoreCache(("idpackageValidator", package_id, live),
                result = result)

        # non-client repos don't use validation here
        # TODO: move to Client repository class?
        client_repo = self.get_plugins_metadata().get('client_repo')
        if not client_repo:
            # server-side repositories don't make any use of package_id validator
            push_cache(package_id, live, (package_id, 0))
            return package_id, 0

        # avoid memleaks
        if len(validator_cache) > 10000:
            validator_cache.clear()

        if live:
            data = self._maskFilter_live(package_id, reponame)
            if data:
                push_cache(package_id, live, data)
                return data

        data = self._maskFilter_user_package_mask(package_id,
            reponame, live)
        if data:
            push_cache(package_id, live, data)
            return data

        data = self._maskFilter_user_package_unmask(package_id,
            reponame, live)
        if data:
            push_cache(package_id, live, data)
            return data

        data = self._maskFilter_packages_db_mask(package_id, reponame,
            live)
        if data:
            push_cache(package_id, live, data)
            return data

        data = self._maskFilter_package_license_mask(package_id,
            reponame, live)
        if data:
            push_cache(package_id, live, data)
            return data

        data = self._maskFilter_keyword_mask(package_id, reponame, live)
        if data:
            push_cache(package_id, live, data)
            return data

        # holy crap, can't validate
        myr = self._settings['pkg_masking_reference']['completely_masked']
        validator_cache[(package_id, reponame, live)] = -1, myr
        push_cache(package_id, live, data)
        return -1, myr

    def atomMatch(self, atom, matchSlot = None, multiMatch = False,
        maskFilter = True, extendedResults = False, useCache = True):
        """
        Match given atom (or dependency) in repository and return its package
        identifer and execution status.

        @param atom: atom or dependency to match in repository
        @type atom: unicode string
        @keyword matchSlot: match packages with given slot
        @type matchSlot: string
        @keyword multiMatch: match all the available packages, not just the
            best one
        @type multiMatch: bool
        @keyword maskFilter: enable package masking filter
        @type maskFilter: bool
        @keyword extendedResults: return extended results
        @type extendedResults: bool
        @keyword useCache: use on-disk cache
        @type useCache: bool
        @return: tuple of length 2 composed by (package_id or -1, command status
            (0 means found, 1 means error)) or, if extendedResults is True,
            also add versioning information to tuple.
            If multiMatch is True, a tuple composed by a set (containing package
            identifiers) and command status is returned.
        @rtype: tuple or set
        """
        if not atom:
            return -1, 1

        if useCache:
            cached = self.__atomMatchFetchCache(atom, matchSlot,
                multiMatch, maskFilter, extendedResults)
            if cached is not None:

                try:
                    cached = self.__atomMatchValidateCache(cached,
                        multiMatch, extendedResults)
                except (TypeError, ValueError, IndexError, KeyError,):
                    cached = None

            if cached is not None:
                return cached

        # "or" dependency support
        # app-foo/foo-1.2.3;app-foo/bar-1.4.3?
        if atom.endswith(etpConst['entropyordepquestion']):
            # or dependency!
            atoms = atom[:-1].split(etpConst['entropyordepsep'])
            for s_atom in atoms:
                data, rc = self.atomMatch(s_atom, matchSlot = matchSlot,
                    multiMatch = multiMatch, maskFilter = maskFilter,
                    extendedResults = extendedResults, useCache = useCache)
                if rc == 0:
                    return data, rc

        matchTag = entropy.tools.dep_gettag(atom)
        try:
            matchUse = entropy.tools.dep_getusedeps(atom)
        except InvalidAtom:
            matchUse = ()
        atomSlot = entropy.tools.dep_getslot(atom)
        matchRevision = entropy.tools.dep_get_entropy_revision(atom)
        if isinstance(matchRevision, int):
            if matchRevision < 0:
                matchRevision = None

        # use match
        scan_atom = entropy.tools.remove_usedeps(atom)
        # tag match
        scan_atom = entropy.tools.remove_tag(scan_atom)

        # slot match
        scan_atom = entropy.tools.remove_slot(scan_atom)
        if (matchSlot is None) and (atomSlot is not None):
            matchSlot = atomSlot

        # revision match
        scan_atom = entropy.tools.remove_entropy_revision(scan_atom)

        direction = ''
        justname = True
        pkgkey = ''
        pkgname = ''
        pkgcat = ''
        pkgversion = ''
        stripped_atom = ''
        found_ids = []
        default_package_ids = None

        if scan_atom:

            while True:
                # check for direction
                scan_cpv = entropy.tools.dep_getcpv(scan_atom)
                stripped_atom = scan_cpv
                if scan_atom.endswith("*"):
                    stripped_atom += "*"
                direction = scan_atom[0:-len(stripped_atom)]

                justname = entropy.tools.isjustname(stripped_atom)
                pkgkey = stripped_atom
                if justname == 0:
                    # get version
                    data = entropy.tools.catpkgsplit(scan_cpv)
                    if data is None:
                        break # badly formatted
                    wildcard = ""
                    if scan_atom.endswith("*"):
                        wildcard = "*"
                    pkgversion = data[2]+wildcard+"-"+data[3]
                    pkgkey = entropy.tools.dep_getkey(stripped_atom)

                splitkey = pkgkey.split("/")
                if (len(splitkey) == 2):
                    pkgcat, pkgname = splitkey
                else:
                    pkgcat, pkgname = "null", splitkey[0]

                break


            # IDs found in the database that match our search
            try:
                found_ids, default_package_ids = self.__generate_found_ids_match(
                    pkgkey, pkgname, pkgcat, multiMatch)
            except OperationalError:
                # we are fault tolerant, cannot crash because
                # tables are not available and validateDatabase()
                # hasn't run
                # found_ids = []
                # default_package_ids = None
                pass

        ### FILTERING
        # filter slot and tag
        if found_ids:
            found_ids = self.__filterSlotTagUse(found_ids, matchSlot,
                matchTag, matchUse, direction)
            if maskFilter:
                found_ids = self._packagesFilter(found_ids)

        ### END FILTERING

        dbpkginfo = set()
        if found_ids:
            dbpkginfo = self.__handle_found_ids_match(found_ids, direction,
                matchTag, matchRevision, justname, stripped_atom, pkgversion)

        if not dbpkginfo:
            if extendedResults:
                if multiMatch:
                    x = set()
                else:
                    x = (-1, 1, None, None, None,)
                self.__atomMatchStoreCache(
                    atom, matchSlot,
                    multiMatch, maskFilter,
                    extendedResults, result = (x, 1)
                )
                return x, 1
            else:
                if multiMatch:
                    x = set()
                else:
                    x = -1
                self.__atomMatchStoreCache(
                    atom, matchSlot,
                    multiMatch, maskFilter,
                    extendedResults, result = (x, 1)
                )
                return x, 1

        if multiMatch:
            if extendedResults:
                x = set([(x[0], 0, x[1], self.retrieveTag(x[0]), \
                    self.retrieveRevision(x[0])) for x in dbpkginfo])
                self.__atomMatchStoreCache(
                    atom, matchSlot,
                    multiMatch, maskFilter,
                    extendedResults, result = (x, 0)
                )
                return x, 0
            else:
                x = set([x[0] for x in dbpkginfo])
                self.__atomMatchStoreCache(
                    atom, matchSlot,
                    multiMatch, maskFilter,
                    extendedResults, result = (x, 0)
                )
                return x, 0

        if len(dbpkginfo) == 1:
            x = dbpkginfo.pop()
            if extendedResults:
                x = (x[0], 0, x[1], self.retrieveTag(x[0]),
                    self.retrieveRevision(x[0]),)

                self.__atomMatchStoreCache(
                    atom, matchSlot,
                    multiMatch, maskFilter,
                    extendedResults, result = (x, 0)
                )
                return x, 0
            else:
                self.__atomMatchStoreCache(
                    atom, matchSlot,
                    multiMatch, maskFilter,
                    extendedResults, result = (x[0], 0)
                )
                return x[0], 0

        # if a default_package_id is given by __generate_found_ids_match
        # we need to respect it
        # NOTE: this is only used by old-style virtual packages
        # if (len(found_ids) > 1) and (default_package_id is not None):
        #    if default_package_id in found_ids:
        #        found_ids = set([default_package_id])
        dbpkginfo = list(dbpkginfo)
        if default_package_ids is not None:
            # at this point, if default_package_ids is not None (== set())
            # we must exclude all the package_ids not available in this list
            # from dbpkginfo
            dbpkginfo = [x for x in dbpkginfo if x[0] in default_package_ids]

        pkgdata = {}
        versions = set()

        for x in dbpkginfo:
            info_tuple = (x[1], self.retrieveTag(x[0]), \
                self.retrieveRevision(x[0]))
            versions.add(info_tuple)
            pkgdata[info_tuple] = x[0]

        # if matchTag is not specified, and tagged and non-tagged packages
        # are available, prefer non-tagged ones, excluding others.
        if not matchTag:

            non_tagged_available = False
            tagged_available = False
            for ver, tag, rev in versions:
                if tag:
                    tagged_available = True
                else:
                    non_tagged_available = True
                if tagged_available and non_tagged_available:
                    break

            if tagged_available and non_tagged_available:
                # filter out tagged
                versions = set(((ver, tag, rev) for ver, tag, rev in versions \
                    if not tag))

        newer = entropy.tools.get_entropy_newer_version(list(versions))[0]
        x = pkgdata[newer]
        if extendedResults:
            x = (x, 0, newer[0], newer[1], newer[2])
            self.__atomMatchStoreCache(
                atom, matchSlot,
                multiMatch, maskFilter,
                extendedResults, result = (x, 0)
            )
            return x, 0
        else:
            self.__atomMatchStoreCache(
                atom, matchSlot,
                multiMatch, maskFilter,
                extendedResults, result = (x, 0)
            )
            return x, 0

    def __generate_found_ids_match(self, pkgkey, pkgname, pkgcat, multiMatch):

        if pkgcat == "null":
            results = self.searchName(pkgname, sensitive = True,
                just_id = True)
        else:
            results = self.searchNameCategory(name = pkgname,
                sensitive = True, category = pkgcat, just_id = True)

        old_style_virtuals = None
        # if it's a PROVIDE, search with searchProvide
        # there's no package with that name
        if (not results) and (pkgcat == self.VIRTUAL_META_PACKAGE_CATEGORY):

            # look for default old-style virtual
            virtuals = self.searchProvidedVirtualPackage(pkgkey)
            if virtuals:
                old_style_virtuals = set([x[0] for x in virtuals if x[1]])
                flat_virtuals = [x[0] for x in virtuals]
                if not old_style_virtuals:
                    old_style_virtuals = set(flat_virtuals)
                results = flat_virtuals

        if not results: # nothing found
            return set(), old_style_virtuals

        if len(results) > 1: # need to choose

            # if we are dealing with old-style virtuals, there is no need
            # to go further and search stuff using category and name since
            # we wouldn't find anything new
            if old_style_virtuals is not None:
                v_results = set()
                for package_id in results:
                    virtual_cat, virtual_name = self.retrieveKeySplit(package_id)
                    v_result = self.searchNameCategory(
                        name = virtual_name, category = virtual_cat,
                        sensitive = True, just_id = True
                    )
                    v_results.update(v_result)
                return set(v_results), old_style_virtuals

            # if it's because category differs, it's a problem
            found_cat = None
            found_id = None
            cats = set()
            for package_id in results:
                cat = self.retrieveCategory(package_id)
                cats.add(cat)
                if (cat == pkgcat) or \
                    ((pkgcat == self.VIRTUAL_META_PACKAGE_CATEGORY) and \
                        (cat == pkgcat)):
                    # in case of virtual packages only
                    # (that they're not stored as provide)
                    found_cat = cat

            # if we found something at least...
            if (not found_cat) and (len(cats) == 1) and \
                (pkgcat in (self.VIRTUAL_META_PACKAGE_CATEGORY, "null")):
                found_cat = sorted(cats)[0]

            if not found_cat:
                # got the issue
                return set(), old_style_virtuals

            # we can use found_cat
            pkgcat = found_cat

            # we need to search using the category
            if (not multiMatch) and (pkgcat == "null"):
                # we searched by name, we need to search using category
                results = self.searchNameCategory(
                    name = pkgname, category = pkgcat,
                    sensitive = True, just_id = True
                )

            # if we get here, we have found the needed IDs
            return set(results), old_style_virtuals

        ###
        ### just found one result
        ###

        package_id = results[0]
        # if pkgcat is virtual, it can be forced
        if (pkgcat == self.VIRTUAL_META_PACKAGE_CATEGORY) and \
            (old_style_virtuals is not None):
            # in case of virtual packages only
            # (that they're not stored as provide)
            pkgcat, pkgname = self.retrieveKeySplit(package_id)

        # check if category matches
        if pkgcat != "null":
            found_cat = self.retrieveCategory(package_id)
            if pkgcat == found_cat:
                return set([package_id]), old_style_virtuals
            return set(), old_style_virtuals # nope nope

        # very good, here it is
        return set([package_id]), old_style_virtuals


    def __handle_found_ids_match(self, found_ids, direction, matchTag,
            matchRevision, justname, stripped_atom, pkgversion):

        dbpkginfo = set()
        # now we have to handle direction
        if ((direction) or ((not direction) and (not justname)) or \
            ((not direction) and (not justname) \
                and stripped_atom.endswith("*"))) and found_ids:

            if (not justname) and \
                ((direction == "~") or (direction == "=") or \
                ((not direction) and (not justname)) or ((not direction) and \
                    not justname and stripped_atom.endswith("*"))):
                # any revision within the version specified
                # OR the specified version

                if ((not direction) and (not justname)):
                    direction = "="

                # remove gentoo revision (-r0 if none)
                if (direction == "="):
                    if (pkgversion.split("-")[-1] == "r0"):
                        pkgversion = entropy.tools.remove_revision(
                            pkgversion)

                if (direction == "~"):
                    pkgrevision = entropy.tools.dep_get_spm_revision(
                        pkgversion)
                    pkgversion = entropy.tools.remove_revision(pkgversion)

                for package_id in found_ids:

                    dbver = self.retrieveVersion(package_id)
                    if (direction == "~"):
                        myrev = entropy.tools.dep_get_spm_revision(
                            dbver)
                        myver = entropy.tools.remove_revision(dbver)
                        if myver == pkgversion and pkgrevision <= myrev:
                            # found
                            dbpkginfo.add((package_id, dbver))
                    else:
                        # media-libs/test-1.2* support
                        if pkgversion[-1] == "*":
                            if dbver.startswith(pkgversion[:-1]):
                                dbpkginfo.add((package_id, dbver))
                        elif (matchRevision is not None) and (pkgversion == dbver):
                            dbrev = self.retrieveRevision(package_id)
                            if dbrev == matchRevision:
                                dbpkginfo.add((package_id, dbver))
                        elif (pkgversion == dbver) and (matchRevision is None):
                            dbpkginfo.add((package_id, dbver))

            elif (direction.find(">") != -1) or (direction.find("<") != -1):

                if not justname:

                    # remove revision (-r0 if none)
                    if pkgversion.endswith("r0"):
                        # remove
                        entropy.tools.remove_revision(pkgversion)

                    for package_id in found_ids:

                        revcmp = 0
                        tagcmp = 0
                        if matchRevision is not None:
                            dbrev = self.retrieveRevision(package_id)
                            revcmp = const_cmp(matchRevision, dbrev)

                        if matchTag is not None:
                            dbtag = self.retrieveTag(package_id)
                            tagcmp = const_cmp(matchTag, dbtag)

                        dbver = self.retrieveVersion(package_id)
                        pkgcmp = entropy.tools.compare_versions(
                            pkgversion, dbver)

                        if pkgcmp is None:
                            warnings.warn("WARNING, invalid version string " + \
                            "stored in %s: %s <-> %s" % (
                                self.reponame, pkgversion, dbver,)
                            )
                            continue

                        if direction == ">":

                            if pkgcmp < 0:
                                dbpkginfo.add((package_id, dbver))
                            elif (matchRevision is not None) and pkgcmp <= 0 \
                                and revcmp < 0:
                                dbpkginfo.add((package_id, dbver))

                            elif (matchTag is not None) and tagcmp < 0:
                                dbpkginfo.add((package_id, dbver))

                        elif direction == "<":

                            if pkgcmp > 0:
                                dbpkginfo.add((package_id, dbver))
                            elif (matchRevision is not None) and pkgcmp >= 0 \
                                and revcmp > 0:
                                dbpkginfo.add((package_id, dbver))

                            elif (matchTag is not None) and tagcmp > 0:
                                dbpkginfo.add((package_id, dbver))

                        elif direction == ">=":

                            if (matchRevision is not None) and pkgcmp <= 0:
                                if pkgcmp == 0:
                                    if revcmp <= 0:
                                        dbpkginfo.add((package_id, dbver))
                                else:
                                    dbpkginfo.add((package_id, dbver))
                            elif pkgcmp <= 0 and matchRevision is None:
                                dbpkginfo.add((package_id, dbver))
                            elif (matchTag is not None) and tagcmp <= 0:
                                dbpkginfo.add((package_id, dbver))

                        elif direction == "<=":

                            if (matchRevision is not None) and pkgcmp >= 0:
                                if pkgcmp == 0:
                                    if revcmp >= 0:
                                        dbpkginfo.add((package_id, dbver))
                                else:
                                    dbpkginfo.add((package_id, dbver))
                            elif pkgcmp >= 0 and matchRevision is None:
                                dbpkginfo.add((package_id, dbver))
                            elif (matchTag is not None) and tagcmp >= 0:
                                dbpkginfo.add((package_id, dbver))

        else: # just the key

            dbpkginfo = set([(x, self.retrieveVersion(x),) for x in found_ids])

        return dbpkginfo

    def __atomMatchFetchCache(self, *args):
        if self.xcache:
            ck_sum = self.checksum(strict = False)
            hash_str = self.__atomMatch_gen_hash_str(args)
            cached = entropy.dump.loadobj("%s/%s/%s_%s" % (
                self.__db_match_cache_key, self.reponame, ck_sum,
                hash(hash_str),))
            if cached is not None:
                return cached

    def __atomMatch_gen_hash_str(self, args):
        hash_str = '|'
        for arg in args:
            hash_str += '%s|' % (arg,)
        return hash_str

    def __atomMatchStoreCache(self, *args, **kwargs):
        if self.xcache:
            ck_sum = self.checksum(strict = False)
            hash_str = self.__atomMatch_gen_hash_str(args)
            self._cacher.push("%s/%s/%s_%s" % (
                self.__db_match_cache_key, self.reponame, ck_sum, hash(hash_str),),
                kwargs.get('result'), async = False
            )

    def __atomMatchValidateCache(self, cached_obj, multiMatch, extendedResults):

        # time wasted for a reason
        data, rc = cached_obj
        if rc != 0:
            return cached_obj

        if multiMatch:
            # data must be set !
            if not isinstance(data, set):
                return None
        else:
            # data must be int !
            if not entropy.tools.isnumber(data):
                return None


        if (not extendedResults) and (not multiMatch):
            if not self.isPackageIdAvailable(data):
                return None

        elif extendedResults and (not multiMatch):
            if not self.isPackageIdAvailable(data[0]):
                return None

        elif extendedResults and multiMatch:
            package_ids = set([x[0] for x in data])
            if not self.arePackageIdsAvailable(package_ids):
                return None

        elif (not extendedResults) and multiMatch:
            # (set([x[0] for x in dbpkginfo]),0)
            if not self.arePackageIdsAvailable(data):
                return None

        return cached_obj

    def __filterSlot(self, package_id, slot):
        if slot is None:
            return package_id
        dbslot = self.retrieveSlot(package_id)
        if dbslot == slot:
            return package_id

    def __filterTag(self, package_id, tag, operators):
        if tag is None:
            return package_id

        dbtag = self.retrieveTag(package_id)
        compare = const_cmp(tag, dbtag)
        # cannot do operator compare because it breaks the tag concept
        if compare == 0:
            return package_id

    def __filterUse(self, package_id, use):
        if not use:
            return package_id
        pkguse = self.retrieveUseflags(package_id)
        disabled = set([x[1:] for x in use if x.startswith("-")])
        enabled = set([x for x in use if not x.startswith("-")])
        enabled_not_satisfied = enabled - pkguse
        # check enabled
        if enabled_not_satisfied:
            return None
        # check disabled
        disabled_not_satisfied = disabled - pkguse
        if len(disabled_not_satisfied) != len(disabled):
            return None
        return package_id

    def __filterSlotTagUse(self, found_ids, slot, tag, use, operators):

        def myfilter(package_id):

            package_id = self.__filterSlot(package_id, slot)
            if not package_id:
                return False

            package_id = self.__filterUse(package_id, use)
            if not package_id:
                return False

            package_id = self.__filterTag(package_id, tag, operators)
            if not package_id:
                return False

            return True

        return set(filter(myfilter, found_ids))

    def _packagesFilter(self, results):
        """
        Packages filter used by atomMatch, input must me found_ids,
        a list like this: [608, 1867].

        """

        # keywordsFilter ONLY FILTERS results if
        # self.reponame.startswith(etpConst['dbnamerepoprefix'])
        # => repository database is open
        if not self.reponame.startswith(etpConst['dbnamerepoprefix']):
            return results

        newresults = set()
        for package_id in results:
            package_id, reason = self.maskFilter(package_id)
            if package_id == -1:
                continue
            newresults.add(package_id)
        return newresults


