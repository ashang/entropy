# -*- coding: utf-8 -*-
"""

    @author: Fabio Erculiani <lxnay@sabayon.org>
    @contact: lxnay@sabayon.org
    @copyright: Fabio Erculiani
    @license: GPL-2

    B{Entropy Infrastructure Toolkit}.

"""
import sys
import argparse

from entropy.i18n import _
from entropy.const import etpUi

from eit.commands.descriptor import EitCommandDescriptor
from eit.commands.command import EitCommand


class EitGraph(EitCommand):
    """
    Main Eit graph command.
    """

    NAME = "graph"
    ALIASES = []

    def __init__(self, args):
        EitCommand.__init__(self, args)
        self._packages = []
        self._complete = False
        # Import text_query from equo libraries
        from text_query import graph_packages
        self._graph_func = graph_packages
        self._quiet = False

    def parse(self):
        descriptor = EitCommandDescriptor.obtain_descriptor(
            EitGraph.NAME)
        parser = argparse.ArgumentParser(
            description=descriptor.get_description(),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            prog="%s %s" % (sys.argv[0], EitGraph.NAME))

        parser.add_argument("packages", nargs='+', metavar="<package>",
                            help=_("package name"))
        parser.add_argument("--complete", action="store_true",
           default=self._complete,
           help=_('show system packages, build deps, circular deps'))
        parser.add_argument("--quiet", action="store_true",
           default=self._quiet,
           help=_('quiet output, for scripting purposes'))

        try:
            nsargs = parser.parse_args(self._args)
        except IOError:
            return parser.print_help, []

        self._quiet = nsargs.quiet
        # support for code using etpUi (text_query)
        etpUi['quiet'] = self._quiet
        self._packages += nsargs.packages
        self._complete = nsargs.complete
        return self._call_unlocked, [self._graph, None]

    def _graph(self, entropy_server):
        """
        Actual Eit graph code.
        """
        return self._graph_func(
            self._packages, entropy_server,
            complete = self._complete,
            repository_ids = entropy_server.repositories())


EitCommandDescriptor.register(
    EitCommandDescriptor(
        EitGraph,
        EitGraph.NAME,
        _('show dependency graph for packages'))
    )