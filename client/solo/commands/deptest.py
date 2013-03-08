# -*- coding: utf-8 -*-
"""

    @author: Fabio Erculiani <lxnay@sabayon.org>
    @contact: lxnay@sabayon.org
    @copyright: Fabio Erculiani
    @license: GPL-2

    B{Entropy Command Line Client}.

"""
import functools
import sys
import argparse
import time

from entropy.i18n import _
from entropy.output import darkred, blue, darkgreen

from solo.commands.descriptor import SoloCommandDescriptor
from solo.commands.install import SoloInstall

class SoloDeptest(SoloInstall):
    """
    Main Solo Deptest command.
    """

    NAME = "deptest"
    ALIASES = ["dt"]
    ALLOW_UNPRIVILEGED = False

    INTRODUCTION = """\
Test system integrity by checking installed packages dependencies.
"""
    SEE_ALSO = "equo-libtest(1)"

    def __init__(self, args):
        SoloInstall.__init__(self, args)
        self._ask = False
        self._quiet = False
        self._pretend = False

    def man(self):
        """
        Overridden from SoloCommand.
        """
        return self._man()

    def _get_parser(self):
        """
        Overridden from SoloCommand.
        """
        descriptor = SoloCommandDescriptor.obtain_descriptor(
            SoloDeptest.NAME)
        parser = argparse.ArgumentParser(
            description=descriptor.get_description(),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            prog="%s %s" % (sys.argv[0], SoloDeptest.NAME))

        parser.add_argument("--ask", "-a", action="store_true",
                            default=self._ask,
                            help=_("ask before making any changes"))
        parser.add_argument("--quiet", "-q", action="store_true",
                            default=self._quiet,
                            help=_("show less details (useful for scripting)"))
        parser.add_argument("--pretend", "-p", action="store_true",
                            default=self._pretend,
                            help=_("just show what would be done"))

        return parser

    def parse(self):
        """
        Parse command
        """
        parser = self._get_parser()
        try:
            nsargs = parser.parse_args(self._args)
        except IOError as err:
            sys.stderr.write("%s\n" % (err,))
            return functools.partial(self.print_help, parser), []

        self._ask = nsargs.ask
        self._quiet = nsargs.quiet
        self._pretend = nsargs.pretend

        return self._call_locked, [self._test]

    def bashcomp(self, last_arg):
        """
        Overridden from SoloCommand.
        """
        entropy_client = self._entropy_bashcomp()
        repos = entropy_client.repositories()
        outcome = ["--force", "--ask", "-a",
                   "--quiet", "-q", "--pretend", "-p"]
        outcome += repos
        return self._bashcomp(sys.stdout, last_arg, outcome)

    def _test(self, entropy_client):
        """
        Command implementation.
        """
        entropy_client.output(
            "%s..." % (blue(_("Running dependency test")),),
            header=darkred(" @@ "))

        deps_not_matched = entropy_client.dependencies_test()
        if not deps_not_matched:
            entropy_client.output("")
            return 0

        crying_atoms = {}
        found_deps = set()
        inst_repo = entropy_client.installed_repository()
        for dep in deps_not_matched:

            r_dep_id = inst_repo.searchDependency(dep)
            if r_dep_id == -1:
                continue

            r_package_ids = inst_repo.searchPackageIdFromDependencyId(
                r_dep_id)
            for r_pkg_id in r_package_ids:
                r_atom = inst_repo.retrieveAtom(r_pkg_id)
                if r_atom:
                    obj = crying_atoms.setdefault(dep, set())
                    obj.add(r_atom)

            # filter through atom_match
            match = entropy_client.atom_match(dep)
            if match[0] != -1:
                found_deps.add(dep)
                continue

            # filter through searchDependency
            dep_id = inst_repo.searchDependency(dep)
            if dep_id == -1:
                continue

            c_package_ids = inst_repo.searchPackageIdFromDependencyId(
                dep_id)
            for c_package_id in c_package_ids:

                if not inst_repo.isPackageIdAvailable(c_package_id):
                    continue

                key_slot = inst_repo.retrieveKeySlotAggregated(
                    c_package_id)
                match = entropy_client.atom_match(key_slot)

                cmpstat = 0
                if match[0] != -1:
                    cmpstat = entropy_client.get_package_action(match)
                if cmpstat != 0:
                    found_deps.add(key_slot)
                    continue

        entropy_client.output(
            "%s:" % (blue(_("These are the dependencies not found")),),
            header=darkred(" @@ "))

        for atom in deps_not_matched:
            entropy_client.output(
                darkred(atom),
                header="   # ")

            if atom in crying_atoms:
                entropy_client.output(
                    "%s:" % (darkred(_("Needed by")),),
                    header=blue("      # "))

                for x in crying_atoms[atom]:
                    entropy_client.output(
                        darkgreen(x),
                        header=blue("      # "))

        if self._ask:
            rc = entropy_client.ask_question(
                "     %s"  % (
                    _("Would you like to install the packages ?"),)
                )
            if rc == _("No"):
                return 1

        else:
            mytxt = "%s %s %s" % (
                blue(_("Installing available packages in")),
                darkred(_("10 seconds")),
                blue("..."),
            )
            entropy_client.output(mytxt, header=darkred(" @@ "))
            time.sleep(10)

        return self._install_action(
            entropy_client, True, True,
            self._pretend, self._ask,
            False, self._quiet, False,
            False, False, False, False, False,
            False, 1, sorted(found_deps))


SoloCommandDescriptor.register(
    SoloCommandDescriptor(
        SoloDeptest,
        SoloDeptest.NAME,
        _("look for unsatisfied dependencies"))
    )
