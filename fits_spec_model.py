import numpy as np
import astropy.io.fits as pyfits
from .plotter import Spectrum
from .util import printmsg

class FITSSpecModel(object):
    def __init__(self, filename):
        self.fits_file = pyfits.open(filename)

        self.en_low = np.array(self.fits_file['ENERGIES'].data['ENERG_LO'])
        self.en_high = np.array(self.fits_file['ENERGIES'].data['ENERG_HI'])
        self.energy = 0.5*(self.en_low + self.en_high)

        self.params = tuple(self.fits_file['PARAMETERS'].data['NAME'])
        self.param_num_vals = tuple(self.fits_file['PARAMETERS'].data['NUMBVALS'])
        self.param_tab_vals = tuple(self.fits_file['PARAMETERS'].data['VALUE'])

        param_initial = tuple(self.fits_file['PARAMETERS'].data['INITIAL'])
        self.values = {}
        for p,v in zip(self.params, param_initial):
            self.values[p] = v

    def __del__(self):
        self.fits_file.close()

    def find_energy(self, en):
        return np.argwhere(np.logical_and(self.en_low<=en, self.en_high>en))[0,0]

    def find_spec_num(self, **kwargs):
        values = dict(self.values)
        for p, v in kwargs.items():
            values[p] = v

        printmsg(1, values)

        # find the nearest tabulated value for each parameter
        param_num = [np.argmin(np.abs(tabvals - values[p])) for p, tabvals in zip(self.params, self.param_tab_vals)]

        spec_num = 0
        for n, pnum in enumerate(param_num):
            block_size = np.prod(self.param_num_vals[n+1:]) if n < (len(param_num) - 1) else 1
            spec_num += pnum * block_size

        return spec_num

    def spectrum(self, energy=None, **kwargs):
        spec_num = self.find_spec_num(**kwargs)

        en = self.energy
        spec = np.array(self.fits_file['SPECTRA'].data['INTPSPEC'][spec_num])

        if energy is not None:
            imin = self.find_energy(energy[0])
            imax = self.find_energy(energy[1])
            en = en[imin:imax]
            spec = spec[imin:imax]

        return Spectrum(en, spec, xscale='log', xlabel='Energy / keV', yscale='log', ylabel='Count Rate')