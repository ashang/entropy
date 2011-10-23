# -*- coding: utf-8 -*-
"""

    @author: Fabio Erculiani <lxnay@sabayon.org>
    @contact: lxnay@sabayon.org
    @copyright: Fabio Erculiani
    @license: GPL-2

    B{Entropy Framework object disk serializer module}.

    This module contains Entropy Python object serialization functions and
    disk dumpers.

    Serialized objects are stored to disk with proper permissions by default
    into path given by entropy.const's etpConst['dumpstoragedir'].

    Permissions are set using entropy.const's const_setup_perms and
    const_setup_file functions.

    Objects are serialized using Python's cPickle/pickle modules, thus
    they must be "pickable". Please read Python Library reference for
    more information.

"""

import sys
import os
from entropy.const import etpConst, const_setup_file
# Always use MAX pickle protocol to <=2, to allow Python 2 and 3 support
COMPAT_PICKLE_PROTOCOL = 0

if sys.hexversion >= 0x3000000:
    import pickle
else:
    try:
        import cPickle as pickle
    except ImportError:
        import pickle

pickle.HIGHEST_PROTOCOL = COMPAT_PICKLE_PROTOCOL
pickle.DEFAULT_PROTOCOL = COMPAT_PICKLE_PROTOCOL

D_EXT = etpConst['cachedumpext']
D_DIR = etpConst['dumpstoragedir']
E_GID = etpConst['entropygid']
if E_GID == None:
    E_GID = 0


def dumpobj(name, my_object, complete_path = False, ignore_exceptions = True,
    dump_dir = None, custom_permissions = None):
    """
    Dump pickable object to file

    @param name: name of the object
    @type name: string
    @param my_object: object to dump
    @type my_object: any Python "pickable" object
    @keyword complete_path: consider "name" argument as
        a complete path (this overrides the default dump
        path given by etpConst['dumpstoragedir'])
    @type complete_path: bool
    @keyword ignore_exceptions: ignore any possible exception
        (EOFError, IOError, OSError,)
    @type ignore_exceptions: bool
    @keyword dump_dir: alternative dump directory
    @type dump_dir: string
    @keyword custom_permissions: give custom permission bits
    @type custom_permissions: octal
    @return: None
    @rtype: None
    @raise EOFError: could be caused by pickle.dump, ignored if
        ignore_exceptions is True
    @raise IOError: could be caused by pickle.dump, ignored if
        ignore_exceptions is True
    @raise OSError: could be caused by pickle.dump, ignored if
        ignore_exceptions is True
    """
    if dump_dir is None:
        dump_dir = D_DIR
    if custom_permissions is None:
        custom_permissions = 0o664

    while True: # trap ctrl+C
        try:
            if complete_path:
                dmpfile = name
                c_dump_dir = os.path.dirname(name)
            else:
                _dmp_path = os.path.join(dump_dir, name)
                dmpfile = _dmp_path+D_EXT
                c_dump_dir = os.path.dirname(_dmp_path)

            my_dump_dir = c_dump_dir
            d_paths = []
            while not os.path.isdir(my_dump_dir):
                d_paths.append(my_dump_dir)
                my_dump_dir = os.path.dirname(my_dump_dir)
            if d_paths:
                d_paths = sorted(d_paths)
                for d_path in d_paths:
                    os.mkdir(d_path)
                    const_setup_file(d_path, E_GID, 0o775)

            tmp_dmpfile = dmpfile + ".tmp"
            with open(tmp_dmpfile, "wb") as dmp_f:
                if sys.hexversion >= 0x3000000:
                    pickle.dump(my_object, dmp_f,
                        protocol = COMPAT_PICKLE_PROTOCOL, fix_imports = True)
                else:
                    pickle.dump(my_object, dmp_f)
                dmp_f.flush()
            const_setup_file(tmp_dmpfile, E_GID, custom_permissions)
            os.rename(tmp_dmpfile, dmpfile)

        except RuntimeError:
            try:
                os.remove(dmpfile)
            except OSError:
                pass
        except (EOFError, IOError, OSError):
            if not ignore_exceptions:
                raise
        break

def serialize(myobj, ser_f, do_seek = True):
    """
    Serialize object to ser_f (file)

    @param myobj: Python object to serialize
    @type myobj: any Python picklable object
    @param ser_f: file object to write to
    @type ser_f: file object
    @keyword do_seek: move file cursor back to the beginning
        of ser_f
    @type do_seek: bool
    @return: file object where data has been written
    @rtype: file object
    @raise RuntimeError: caused by pickle.dump in case of
        system errors
    @raise EOFError: caused by pickle.dump in case of
        race conditions on multi-processing or multi-threading
    @raise IOError: caused by pickle.dump in case of
        race conditions on multi-processing or multi-threading
    @raise pickle.PicklingError: when object cannot be recreated
    """
    if sys.hexversion >= 0x3000000:
        pickle.dump(myobj, ser_f, protocol = COMPAT_PICKLE_PROTOCOL,
            fix_imports = True)
    else:
        pickle.dump(myobj, ser_f)
    ser_f.flush()
    if do_seek:
        ser_f.seek(0)
    return ser_f

def unserialize(serial_f):
    """
    Unserialize file to object (file)

    @param serial_f: file object which data will be read from
    @type serial_f: file object
    @return: rebuilt object
    @rtype: any Python pickable object
    @raise pickle.UnpicklingError: when object cannot be recreated
    """
    if sys.hexversion >= 0x3000000:
        return pickle.load(serial_f, fix_imports = True,
            encoding = 'raw_unicode_escape')
    else:
        return pickle.load(serial_f)

def unserialize_string(mystring):
    """
    Unserialize pickle string to object

    @param mystring: data stream in string form to reconstruct
    @type mystring: string
    @return: reconstructed object
    @rtype: any Python pickable object
    @raise pickle.UnpicklingError: when object cannot be recreated
    """
    if sys.hexversion >= 0x3000000:
        return pickle.loads(mystring, fix_imports = True,
            encoding = 'raw_unicode_escape')
    else:
        return pickle.loads(mystring)

def serialize_string(myobj):
    """
    Serialize object to string

    @param myobj: object to serialize
    @type myobj: any Python picklable object
    @return: serialized string
    @rtype: string
    @raise pickle.PicklingError: when object cannot be recreated
    """
    if sys.hexversion >= 0x3000000:
        return pickle.dumps(myobj, protocol = COMPAT_PICKLE_PROTOCOL,
            fix_imports = True, encoding = 'raw_unicode_escape')
    else:
        return pickle.dumps(myobj)

def loadobj(name, complete_path = False, dump_dir = None):
    """
    Load object from a file
    @param name: name of the object to load
    @type name: string
    @keyword complete_path: determine whether name argument
        is a complete disk path to serialized object
    @type complete_path: bool
    @keyword dump_dir: alternative dump directory
    @type dump_dir: string
    @return: object or None
    @rtype: any Python pickable object or None
    """
    if dump_dir is None:
        dump_dir = D_DIR

    while True:
        if complete_path:
            dmpfile = name
        else:
            dump_path = os.path.join(dump_dir, name)
            dmpfile = dump_path+D_EXT

        if os.path.isfile(dmpfile) and os.access(dmpfile, os.R_OK):
            try:
                with open(dmpfile, "rb") as dmp_f:
                    obj = None
                    try:
                        if sys.hexversion >= 0x3000000:
                            obj = pickle.load(dmp_f, fix_imports = True,
                                encoding = 'raw_unicode_escape')
                        else:
                            obj = pickle.load(dmp_f)
                    except (ValueError, EOFError, IOError,
                        OSError, pickle.UnpicklingError, TypeError,
                        AttributeError, ImportError, SystemError,):
                        pass
                    return obj
            except (IOError, OSError,):
                pass
        break

def getobjmtime(name, dump_dir = None):
    """
    Get dumped object mtime

    @param name: object name
    @type name: string
    @keyword dump_dir: alternative dump directory
    @type dump_dir: string
    @return: mtime of the file containing the serialized object or 0
        if not found
    @rtype: int
    """
    if dump_dir is None:
        dump_dir = D_DIR
    mtime = 0
    dump_path = os.path.join(dump_dir, name+D_EXT)
    if os.path.isfile(dump_path) and os.access(dump_path, os.R_OK):
        mtime = os.path.getmtime(dump_path)
    return int(mtime)

def removeobj(name, dump_dir = None):
    """
    Remove cached object referenced by its object name

    @param name: object name
    @type name: string
    @keyword dump_dir: alternative dump directory
    @type dump_dir: string
    @return: bool representing whether object has been
        removed or not
    @rtype: bool
    @raise OSError: in case of troubles with os.remove()
    """
    if dump_dir is None:
        dump_dir = D_DIR
    filepath = dump_dir+"/"+name+D_EXT
    if os.path.isfile(filepath) and os.access(filepath, os.W_OK):
        os.remove(filepath)
        return True
    return False