"""
mfbas module.  Contains the ModflowBas class. Note that the user can access
the ModflowBas class as `hataripy.modflow.ModflowBas`.

Additional information for this MODFLOW package can be found at the `Online
MODFLOW Guide
<http://water.usgs.gov/ogw/modflow/MODFLOW-2005-Guide/index.html?bas6.htm>`_.

"""

import re
import sys
import numpy as np
from ..pakbase import Package
from ..utils import Util3d, check, get_neighbors


class ModflowBas(Package):
    """
    MODFLOW Basic Package Class.

    Parameters
    ----------
    model : model object
        The model object (of type :class:`hataripy.modflow.mf.Modflow`) to which
        this package will be added.
    ibound : array of ints, optional
        The ibound array (the default is 1).
    strt : array of floats, optional
        An array of starting heads (the default is 1.0).
    ifrefm : bool, optional
        Indication if data should be read using free format (the default is
        True).
    ixsec : bool, optional
        Indication of whether model is cross sectional or not (the default is
        False).
    ichflg : bool, optional
        Flag indicating that flows between constant head cells should be
        calculated (the default is False).
    stoper : float
        percent discrepancy that is compared to the budget percent discrepancy
        continue when the solver convergence criteria are not met.  Execution
        will unless the budget percent discrepancy is greater than stoper
        (default is None). MODFLOW-2005 only
    hnoflo : float
        Head value assigned to inactive cells (default is -999.99).
    extension : str, optional
        File extension (default is 'bas').
    unitnumber : int, optional
        FORTRAN unit number for this package (default is None).
    filenames : str or list of str
        Filenames to use for the package. If filenames=None the package name
        will be created using the model name and package extension. If a single
        string is passed the package name will be set to the string.
        Default is None.

    Attributes
    ----------
    heading : str
        Text string written to top of package input file.
    options : list of str
        Can be either or a combination of XSECTION, CHTOCH or FREE.
    ifrefm : bool
        Indicates whether or not packages will be written as free format.

    Methods
    -------

    See Also
    --------

    Notes
    -----

    Examples
    --------

    >>> import hataripy
    >>> m = hataripy.modflow.Modflow()
    >>> bas = hataripy.modflow.ModflowBas(m)

    """

    @staticmethod
    def ftype():
        return 'BAS6'

    @staticmethod
    def defaultunit():
        return 13

    def __init__(self, model, ibound=1, strt=1.0, ifrefm=True, ixsec=False,
                 ichflg=False, stoper=None, hnoflo=-999.99, extension='bas',
                 unitnumber=None, filenames=None):
        """
        Package constructor.

        """

        if unitnumber is None:
            unitnumber = ModflowBas.defaultunit()

        # set filenames
        if filenames is None:
            filenames = [None]
        elif isinstance(filenames, str):
            filenames = [filenames]

        # Fill namefile items
        name = [ModflowBas.ftype()]
        units = [unitnumber]
        extra = ['']

        # set package name
        fname = [filenames[0]]

        # Call ancestor's init to set self.parent, extension, name and unit number
        Package.__init__(self, model, extension=extension, name=name,
                         unit_number=units, extra=extra, filenames=fname)

        self.url = 'bas6.htm'

        nrow, ncol, nlay, nper = self.parent.nrow_ncol_nlay_nper
        self.ibound = Util3d(model, (nlay, nrow, ncol), np.int32, ibound,
                             name='ibound', locat=self.unit_number[0])
        self.strt = Util3d(model, (nlay, nrow, ncol), np.float32, strt,
                           name='strt', locat=self.unit_number[0])
        self.heading = '# {} package for '.format(self.name[0]) + \
                       ' {}, '.format(model.version_types[model.version]) + \
                       'generated by hataripy.'
        self.options = ''
        self.ixsec = ixsec
        self.ichflg = ichflg
        self.stoper = stoper

        # self.ifrefm = ifrefm
        # model.array_free_format = ifrefm
        model.free_format_input = ifrefm

        self.hnoflo = hnoflo
        self.parent.add_package(self)
        return

    @property
    def ifrefm(self):
        return self.parent.free_format_input

    def __setattr__(self, key, value):
        if key == "ifrefm":
            self.parent.free_format_input = value
        else:
            super(ModflowBas, self).__setattr__(key, value)

    def check(self, f=None, verbose=True, level=1):
        """
        Check package data for common errors.

        Parameters
        ----------
        f : str or file handle
            String defining file name or file handle for summary file
            of check method output. If a sting is passed a file handle
            is created. If f is None, check method does not write
            results to a summary file. (default is None)
        verbose : bool
            Boolean flag used to determine if check method results are
            written to the screen
        level : int
            Check method analysis level. If level=0, summary checks are
            performed. If level=1, full checks are performed.

        Returns
        -------
        None

        Examples
        --------

        >>> import hataripy
        >>> m = hataripy.modflow.Modflow.load('model.nam')
        >>> m.bas6.check()

        """
        chk = check(self, f=f, verbose=verbose, level=level)

        neighbors = get_neighbors(self.ibound.array)
        neighbors[
            np.isnan(neighbors)] = 0  # set neighbors at edges to 0 (inactive)
        chk.values(self.ibound.array,
                   (self.ibound.array > 0) & np.all(neighbors < 1, axis=0),
                   'isolated cells in ibound array', 'Warning')
        chk.values(self.ibound.array, np.isnan(self.ibound.array),
                   error_name='Not a number', error_type='Error')
        chk.summarize()
        return chk

    def write_file(self, check=True):
        """
        Write the package file.

        Parameters
        ----------
        check : boolean
            Check package data for common errors. (default True)

        Returns
        -------
        None

        """
        # allows turning off package checks when writing files at model level
        if check:
            self.check(f='{}.chk'.format(self.name[0]),
                       verbose=self.parent.verbose, level=1)
        # Open file for writing
        f_bas = open(self.fn_path, 'w')
        # First line: heading
        # f_bas.write('%s\n' % self.heading)
        f_bas.write('{0:s}\n'.format(self.heading))
        # Second line: format specifier
        opts = []
        if self.ixsec:
            opts.append('XSECTION')
        if self.ichflg:
            opts.append('CHTOCH')
        if self.ifrefm:
            opts.append('FREE')
        if self.stoper is not None:
            opts.append('STOPERROR {0}'.format(self.stoper))
        self.options = ' '.join(opts)
        f_bas.write(self.options + '\n')
        # IBOUND array
        f_bas.write(self.ibound.get_file_entry())
        # Head in inactive cells
        str_hnoflo = str(self.hnoflo).rjust(10)
        if not self.ifrefm and len(str_hnoflo) > 10:
            # write fixed-width no more than 10 characters
            str_hnoflo = '{0:10.4G}'.format(self.hnoflo)
            assert len(str_hnoflo) <= 10, str_hnoflo
        f_bas.write(str_hnoflo + '\n')
        # Starting heads array
        f_bas.write(self.strt.get_file_entry())
        # Close file
        f_bas.close()

    @staticmethod
    def load(f, model, ext_unit_dict=None, check=True, **kwargs):
        """
        Load an existing package.

        Parameters
        ----------
        f : filename or file handle
            File to load.
        model : model object
            The model object (of type :class:`hataripy.modflow.mf.Modflow`) to
            which this package will be added.
        ext_unit_dict : dictionary, optional
            If the arrays in the file are specified using EXTERNAL,
            or older style array control records, then `f` should be a file
            handle.  In this case ext_unit_dict is required, which can be
            constructed using the function
            :class:`hataripy.utils.mfreadnam.parsenamefile`.
        check : boolean
            Check package data for common errors. (default True)
        kwargs : dictionary
            Keyword arguments that are passed to load.
            Possible keyword arguments are nlay, nrow, and ncol.
            If not provided, then the model must contain a discretization
            package with correct values for these parameters.

        Returns
        -------
        bas : ModflowBas object
            ModflowBas object (of type :class:`hataripy.modflow.ModflowBas`)

        Examples
        --------

        >>> import hataripy
        >>> m = hataripy.modflow.Modflow()
        >>> bas = hataripy.modflow.ModflowBas.load('test.bas', m, nlay=1, nrow=10,
        >>>                                     ncol=10)

        """

        if model.verbose:
            sys.stdout.write('loading bas6 package file...\n')

        # parse keywords
        if 'nlay' in kwargs:
            nlay = kwargs.pop('nlay')
        else:
            nlay = None
        if 'nrow' in kwargs:
            nrow = kwargs.pop('nrow')
        else:
            nrow = None
        if 'ncol' in kwargs:
            ncol = kwargs.pop('ncol')
        else:
            ncol = None

        # open the file if not already open
        if not hasattr(f, 'read'):
            filename = f
            f = open(filename, 'r')
        # dataset 0 -- header
        while True:
            line = f.readline()
            if line[0] != '#':
                break
        # dataset 1 -- options
        # only accept alphanumeric characters, as well as '+', '-' and '.'
        line = re.sub(r'[^A-Z0-9\.\-\+]', ' ', line.upper())
        opts = line.strip().split()
        ixsec = 'XSECTION' in opts
        ichflg = 'CHTOCH' in opts
        ifrefm = 'FREE' in opts
        iprinttime = 'PRINTTIME' in opts
        ishowp = 'SHOWPROGRESS' in opts
        if 'STOPERROR' in opts:
            i = opts.index('STOPERROR')
            stoper = np.float32(opts[i + 1])
        else:
            stoper = None
        # get nlay,nrow,ncol if not passed
        if nlay is None and nrow is None and ncol is None:
            nrow, ncol, nlay, nper = model.get_nrow_ncol_nlay_nper()

        # dataset 2 -- ibound
        ibound = Util3d.load(f, model, (nlay, nrow, ncol), np.int32, 'ibound',
                             ext_unit_dict)

        # dataset 3 -- hnoflo
        line = f.readline()
        hnoflo = np.float32(line.strip().split()[0])

        # dataset 4 -- strt
        strt = Util3d.load(f, model, (nlay, nrow, ncol), np.float32, 'strt',
                           ext_unit_dict)
        f.close()

        # set package unit number
        unitnumber = None
        filenames = [None]
        if ext_unit_dict is not None:
            unitnumber, filenames[0] = \
                model.get_ext_dict_attr(ext_unit_dict,
                                        filetype=ModflowBas.ftype())

        # create bas object and return
        bas = ModflowBas(model, ibound=ibound, strt=strt,
                         ixsec=ixsec, ifrefm=ifrefm, ichflg=ichflg,
                         stoper=stoper, hnoflo=hnoflo,
                         unitnumber=unitnumber, filenames=filenames)
        if check:
            bas.check(f='{}.chk'.format(bas.name[0]),
                      verbose=bas.parent.verbose, level=0)
        return bas
