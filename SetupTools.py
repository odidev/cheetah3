#!/usr/bin/env python
# $Id: SetupTools.py,v 1.2 2001/10/10 06:59:45 tavis_rudd Exp $
"""Some tools for extending and working with distutils

CREDITS: This module borrows code and ideas from M.A. Lemburg's excellent setup
tools for the mxBase package.

"""

__author__ = "Tavis Rudd <tavis@calrudd.com>"
__version__ = "$Revision: 1.2 $"[11:-2]


##################################################
## GLOBALS AND CONSTANTS ##

True = (1==1) 
False = (1==0) 

##################################################
## DEPENDENCIES ##

from distutils.core import setup
from distutils.core import Command
from distutils.command.install_data import install_data
from distutils.command.sdist import sdist

import os
from os import listdir
import os.path
from os.path import exists, isdir, isfile, join, splitext

import types
import glob
import string

#imports from Cheetah ...
from src.FileUtils import findFiles

##################################################
## CLASSES ##
                
class mod_install_data(install_data):
    
    """A copy of M.A Lemburg's modified version of the disutils install_data
    command that allows data files to be included directly in the installed
    Python package tree.

    Note that it expects that data_files argument to the disutils.setup()
    commmand to be a list of strings rather than a list of tuples as is the
    default.  Each of these string entries can be a real file name or a glob
    pattern representing the files to match."""

    def finalize_options(self):

        if self.install_dir is None:
            installobj = self.distribution.get_command_obj('install')
            self.install_dir = installobj.install_platlib
        install_data.finalize_options(self)

    def run (self):

        if not self.dry_run:
            self.mkpath(self.install_dir)
        data_files = self.get_inputs()
        
        for entry in data_files:
            if type(entry) != types.StringType:
                raise ValueError, 'The entries in "data_files" must be strings'
            
            entry = string.join(string.split(entry, '/'), os.sep)
            # entry is a filename or glob pattern
            if entry.startswith('recursive:'):
                entry = entry[len('recursive:'):]
                dir = entry.split()[0]
                globPatterns = entry.split()[1:]
                filenames = findFiles(dir, globPatterns)
            else:
                filenames = glob.glob(entry)
            
            for filename in filenames:
                ## generate the dstPath from the filename
                # - deal with 'package_dir' translations
                topDir, subPath = (filename.split(os.sep)[0],
                                   os.sep.join( filename.split(os.sep)[1:] )
                                   )

                package_dirDict = self.distribution.package_dir
                if package_dirDict:
                    packageDir = topDir
                    for key, val in package_dirDict.items():
                        if val == topDir:
                            packageDir = key
                            break
                else:
                    packageDir = topDir
                dstPath = os.path.join(self.install_dir, packageDir, subPath)

                ## add the file to the list of outfiles
                dstdir = os.path.split(dstPath)[0]
                if not self.dry_run:
                    self.mkpath(dstdir)
                    outfile = self.copy_file(filename, dstPath)[0]
                else:
                    outfile = dstPath
                self.outfiles.append(outfile)


class contrib(Command):
    """a setup command that will process the contributed packages.

    USAGE: setup.py contrib install
           or
           setup.py contrib sdist
           etc.
    """
    description = ""
 
    # List of option tuples: long name, short name (None if no short
    # name), and help string.
    user_options = [ ('cmd=', None,
                      "The command to run on each of the contrib packages"),
                     ('contrib_dir=', None,
                      "The directory which contains all of the contrib packages"),
                     ('contrib_packages=', None,
                      "A whitespace separated list of contrib package subdirs"),
                     
                     ]
     
    def initialize_options (self):
        self.cmd = 'install'
 
    def finalize_options (self):
        pass
    
    def run(self):
        cwd = os.getcwd()
        for p in self.contrib_packages.split():
            d = os.path.join(cwd, self.contrib_dir, p)
            os.chdir(d)
            print "Working on", d, "(", os.getcwd(), ")"
            try:
                os.system(sys.executable+' setup.py '+ self.cmd)
            except:
                print "An error occurred while installing the contributed packages."
                #os.chdir(cwd)
                raise


class sdist_docs(sdist):
    
    """A setup command that will rebuild Users Guide at the same time as
    creating a source distribution.

    It relies on the main tex-file being called users_guide.tex and the tex file
    being in a form that Python's mkhowto script accepts."""
    
    def run(self):
        try:
            from main_package.Version import version
            
            currentDir = os.getcwd()
            os.chdir(os.path.join(currentDir,'docs','src'))
            fp = open('users_guide.tex','r')
            originalTexCode = fp.read()
            fp.close()
            
            newTexCode = re.sub(r'(?<=\\release\{)[0-9\.a-zA-Z]*',str(version), originalTexCode)
            
            fp = open('users_guide.tex','w')
            fp.write(newTexCode)
            fp.close()
            
            os.system('make -f Makefile')
            os.chdir(currentDir)
        except:
            print "The sdist_docs command couldn't rebuild the Users Guide"
            os.chdir(currentDir)
            
        sdist.run(self)


class uninstall(Command):

    description = "uninstall the package files and directories"

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass
        
    def run(self):

        # Execute build
        self.announce('determining installation files')
        self.announce('(re)building package')
        savevalue = self.distribution.dry_run
        self.distribution.dry_run = 0
        self.run_command('build')

        # Execute install in dry-run mode
        self.announce('dry-run package install')
        self.distribution.dry_run = 1
        self.run_command('install')
        self.distribution.dry_run = savevalue
        build = self.get_finalized_command('build')
        install = self.get_finalized_command('install')

        # Remove all installed files
        self.announce("removing files")
        dirs = {}
        filenames = install.get_outputs()
        for filename in filenames:
            if not os.path.isabs(filename):
                raise DistutilsError,\
                      'filename %s from .get_output() not absolute' % \
                      filename

            if os.path.isfile(filename):
                self.announce("removing %s" % filename)
                if not self.dry_run:
                    try:
                        os.remove(filename)
                    except OSError, details:
                        self.warn("Could not remove file: %s" % details)
                    dir = os.path.split(filename)[0]
                    if not dirs.has_key(dir):
                        dirs[dir] = 1
                    if os.path.splitext(filename)[1] == '.py':
                        # Remove byte-code files as well
                        try:
                            os.remove(filename + 'c')
                        except OSError:
                            pass
                        try:
                            os.remove(filename + 'o')
                        except OSError:
                            pass

            elif os.path.isdir(filename):
                # This functionality is currently not being used by distutils
                if not dirs.has_key(dir):
                    dirs[filename] = 1

            elif not os.path.splitext(filename)[1] in ('.pyo', '.pyc'):
                self.announce("skipping removal of %s (not found)" %
                              filename)

        # Remove the installation directories
        self.announce("removing directories")
        dirs = dirs.keys()
        dirs.sort(); dirs.reverse() # sort descending
        for dir in dirs:
            self.announce("removing directory %s" % dir)
            if not self.dry_run:
                try:
                    os.rmdir(dir)
                except OSError, details:
                    self.warn("could not remove directory: %s" % details)


##################################################
## FUNCTIONS ##

def run_setup(configurations):

    """ Run distutils setup.

        The parameters passed to setup() are extracted from the list of modules,
        classes or instances given in configurations.

        Names with leading underscore are removed from the parameters.
        Parameters which are not strings, lists, tuples, or dicts are removed as
        well.  Configurations which occur later in the configurations list
        override settings of configurations earlier in the list.

    """
    # Build parameter dictionary
    kws = {}
    for configuration in configurations:
        kws.update(vars(configuration))
    for name, value in kws.items():
        if name[:1] == '_' or \
           type(value) not in (types.StringType,
                               types.ListType,
                               types.TupleType,
                               types.DictType,
                               ):
            del kws[name]

    # Add setup extensions
    cmdclasses = {'install_data': mod_install_data,
                  'uninstall':uninstall,
                  'contrib':contrib,
                  'sdist_docs':sdist_docs,
                  }

    kws['cmdclass'] = cmdclasses

    # Invoke distutils setup
    apply(setup, (), kws)
