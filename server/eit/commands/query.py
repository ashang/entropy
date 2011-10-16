# -*- coding: utf-8 -*-
"""

    @author: Fabio Erculiani <lxnay@sabayon.org>
    @contact: lxnay@sabayon.org
    @copyright: Fabio Erculiani
    @license: GPL-2

    B{Entropy Infrastructure Toolkit}.

"""
import sys
import os
import argparse

from entropy.output import blue, purple, darkgreen, bold, brown, teal, \
    darkred
from entropy.const import const_convert_to_rawstring, etpConst
from entropy.i18n import _
from entropy.security import Repository
from entropy.tools import convert_unix_time_to_human_time

from eit.commands.descriptor import EitCommandDescriptor
from eit.commands.command import EitCommand


class EitQuery(EitCommand):
    """
    Main Eit query command.
    """

    NAME = "query"
    ALIASES = ["q"]
    ALLOW_UNPRIVILEGED = True

    def __init__(self, args):
        EitCommand.__init__(self, args)
        self._nsargs = None
        self._quiet = False
        self._verbose = False
        self._repository_id = None
        from text_query import print_package_info
        self._pprint = print_package_info

    def parse(self):
        """ Overridden from EitCommand """
        descriptor = EitCommandDescriptor.obtain_descriptor(
            EitQuery.NAME)
        parser = argparse.ArgumentParser(
            description=descriptor.get_description(),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            prog="%s %s" % (sys.argv[0], EitQuery.NAME))

        subparsers = parser.add_subparsers(
            title="action", description=_("execute query"),
            help=_("available queries"))

        tags_parser = subparsers.add_parser("tags",
            help=_("search package tags"))
        tags_parser.add_argument("--quiet", "-q", action="store_true",
            default=self._quiet,
            help=_('quiet output, for scripting purposes'))
        tags_parser.add_argument("--in", metavar="<repository>",
            help=_("query into given repository only"),
            dest="inrepo", default=None)
        tags_parser.add_argument("tags", nargs='+',
                                 metavar="<tag>",
                                 help=_("tag name"))
        tags_parser.set_defaults(func=self._tags)

        needed_parser = subparsers.add_parser("needed",
            help=_("show libraries (.so) required by matched packages"))
        needed_parser.add_argument("--quiet", "-q", action="store_true",
            default=self._quiet,
            help=_('quiet output, for scripting purposes'))
        needed_parser.add_argument("inrepo", action="store_const",
                                   const=None)
        needed_parser.add_argument("packages", nargs='+',
                                 metavar="<package>",
                                 help=_("package names"))
        needed_parser.set_defaults(func=self._needed)

        revdeps_parser = subparsers.add_parser("revdeps",
            help=_("show reverse dependencies of packages"))
        revdeps_parser.add_argument("--quiet", "-q", action="store_true",
            default=self._quiet,
            help=_('quiet output, for scripting purposes'))
        revdeps_parser.add_argument("--verbose", "-v", action="store_true",
            default=self._verbose,
            help=_('verbose output, show more info'))
        revdeps_parser.add_argument("--bdeps", "-b", action="store_true",
            default=False,
            help=_('include build dependencies'))
        revdeps_parser.add_argument("inrepo", action="store_const",
                                    const=None)
        revdeps_parser.add_argument("packages", nargs='+',
                                 metavar="<package>",
                                 help=_("package names"))
        revdeps_parser.set_defaults(func=self._revdeps)

        sets_parser = subparsers.add_parser("sets",
            help=_("search through package sets"))
        sets_parser.add_argument("--quiet", "-q", action="store_true",
            default=self._quiet,
            help=_('quiet output, for scripting purposes'))
        sets_parser.add_argument("--verbose", "-v", action="store_true",
            default=self._verbose,
            help=_('verbose output, show package sets content'))
        sets_parser.add_argument("--in", metavar="<repository>",
            help=_("query into given repository only"),
            dest="inrepo", default=None)
        sets_parser.add_argument("sets", nargs='*',
                                 metavar="<set>",
                                 help=_("package set name"))
        sets_parser.set_defaults(func=self._sets)

        desc_parser = subparsers.add_parser("desc",
            help=_("search packages through their description"))
        desc_parser.add_argument("--quiet", "-q", action="store_true",
            default=self._quiet,
            help=_('quiet output, for scripting purposes'))
        desc_parser.add_argument("--verbose", "-v", action="store_true",
            default=self._verbose,
            help=_('verbose output, show more information'))
        desc_parser.add_argument("--in", metavar="<repository>",
            help=_("query into given repository only"),
            dest="inrepo", default=None)
        desc_parser.add_argument("descriptions", nargs='+',
                                 metavar="<description>",
                                 help=_("package description"))
        desc_parser.set_defaults(func=self._desc)

        try:
            nsargs = parser.parse_args(self._args)
        except IOError as err:
            sys.stderr.write("%s\n" % (err,))
            return parser.print_help, []

        self._repository_id = nsargs.inrepo
        self._quiet = nsargs.quiet
        self._verbose = getattr(nsargs, "verbose", self._verbose)
        self._nsargs = nsargs
        return self._call_unlocked, [nsargs.func, self._repository_id]

    def _tags(self, entropy_server):
        """
        Eit query tags code.
        """
        repository_ids = []
        if self._repository_id is None:
            repository_ids += entropy_server.repositories()
        else:
            repository_ids.append(self._repository_id)

        exit_st = 0
        for repository_id in repository_ids:
            repo = entropy_server.open_repository(repository_id)
            key_sorter = lambda x: repo.retrieveAtom(x[1])
            for tag in self._nsargs.tags:
                tagged_pkgs = repo.searchTaggedPackages(
                    tag, atoms = True)
                results = sorted(tagged_pkgs, key = key_sorter)
                for atom, pkg_id in results:
                    if self._quiet:
                        entropy_server.output(atom,
                            level="generic")
                    else:
                        self._pprint(pkg_id, entropy_server,
                                     repo, quiet = False)

                if (not results) and (not self._quiet):
                    entropy_server.output(
                        "%s: %s" % (
                            purple(_("Nothing found for")),
                            teal(tag)
                            ),
                        importance=1, level="warning")
                if not results:
                    exit_st = 1

        return exit_st

    def _needed(self, entropy_server):
        """
        Eit query needed code.
        """
        repository_ids = []
        if self._repository_id is None:
            repository_ids += entropy_server.repositories()
        else:
            repository_ids.append(self._repository_id)

        exit_st = 0
        for package in self._nsargs.packages:
            pkg_id, repo_id = entropy_server.atom_match(package)
            if pkg_id == -1:
                if not self._quiet:
                    entropy_server.output(
                        "%s: %s" % (
                            purple(_("Not matched")), teal(package)),
                        level="warning", importance=1)
                exit_st = 1
                continue
            repo = entropy_server.open_repository(repo_id)

            atom = repo.retrieveAtom(pkg_id)
            neededs = repo.retrieveNeeded(pkg_id)
            for needed in neededs:
                if self._quiet:
                    entropy_server.output(needed, level="generic")
                else:
                    entropy_server.output(needed)

            if not self._quiet:
                entropy_server.output(
                    "[%s] %s: %s %s" % (
                        purple(repo_id),
                        darkgreen(atom),
                        bold(str(len(neededs))),
                        teal(_("libraries found"))))

        return exit_st

    def _revdeps(self, entropy_server):
        """
        Eit query revdeps code.
        """
        excluded_dep_types = None
        if not self._nsargs.bdeps:
            excluded_dep_types = [
                etpConst['dependency_type_ids']['bdepend_id']
                ]

        exit_st = 0
        for package in self._nsargs.packages:
            pkg_id, repo_id = entropy_server.atom_match(package)
            if pkg_id == -1:
                if not self._quiet:
                    entropy_server.output(
                        "%s: %s" % (
                            purple(_("Not matched")), teal(package)),
                        level="warning", importance=1)
                exit_st = 1
                continue
            repo = entropy_server.open_repository(repo_id)

            key_sorter = lambda x: repo.retrieveAtom(x)
            results = repo.retrieveReverseDependencies(pkg_id,
                exclude_deptypes = excluded_dep_types)
            for pkg_id in sorted(results, key = key_sorter):
                self._pprint(pkg_id, entropy_server, repo,
                    installed_search = True, strict_output = self._quiet,
                    extended = self._verbose, quiet = self._quiet)

            if not self._quiet:
                atom = repo.retrieveAtom(pkg_id)
                entropy_server.output(
                    "[%s] %s: %s %s" % (
                        purple(repo_id),
                        darkgreen(atom),
                        bold(str(len(results))),
                        teal(_("revdep(s) found"))))

        return exit_st

    def _sets(self, entropy_server):
        """
        Eit query sets code.
        """
        repository_ids = []
        if self._repository_id is None:
            repository_ids += entropy_server.repositories()
        else:
            repository_ids.append(self._repository_id)
        repository_ids = tuple(repository_ids)
        sets = entropy_server.Sets()

        match_num = 0
        exit_st = 0
        if not self._nsargs.sets:
            self._nsargs.sets.append("*")
        for item in self._nsargs.sets:
            results = sets.search(item, match_repo=repository_ids)
            key_sorter = lambda x: x[1]
            for repo, set_name, set_data in sorted(results,
                                                   key=key_sorter):
                match_num += 1
                found = True
                if not self._quiet:
                    entropy_server.output(
                        "%s%s" % (brown(etpConst['packagesetprefix']),
                                  darkgreen(set_name),))
                    if self._verbose:
                        elements = sorted(set_data)
                        for element in elements:
                            entropy_server.output(
                                teal(element),
                                header="  ")
                else:
                    entropy_server.output(
                        "%s%s" % (etpConst['packagesetprefix'],
                                  set_name,), level="generic")
                    if self._verbose:
                        for element in sorted(set_data):
                            entropy_server.output(
                                element, level="generic")

            if not self._quiet:
                entropy_server.output(
                    "[%s] %s %s" % (
                        darkgreen(item),
                        bold(str(match_num)),
                        teal(_("sets found"))))

        return 0

    def _desc(self, entropy_server):
        """
        Eit query desc code.
        """
        repository_ids = []
        if self._repository_id is None:
            repository_ids += entropy_server.repositories()
        else:
            repository_ids.append(self._repository_id)

        for repository_id in repository_ids:
            repo = entropy_server.open_repository(repository_id)
            key_sorter = lambda x: repo.retrieveAtom(x)
            for desc in self._nsargs.descriptions:
                pkg_ids = repo.searchDescription(desc, just_id = True)
                for pkg_id in sorted(pkg_ids, key = key_sorter):
                    if self._quiet:
                        entropy_server.output(
                            repo.retrieveAtom(pkg_id), level="generic")
                    else:
                        self._pprint(pkg_id, entropy_server, repo,
                                     extended = self._verbose,
                                     strict_output = False,
                                     quiet = False)

                if not self._quiet:
                    entropy_server.output(
                        "[%s] %s %s" % (
                            darkgreen(desc),
                            bold(str(len(pkg_ids))),
                            teal(_("packages found"))))

        return 0


EitCommandDescriptor.register(
    EitCommandDescriptor(
        EitQuery,
        EitQuery.NAME,
        _('miscellaneous package metadata queries'))
    )
