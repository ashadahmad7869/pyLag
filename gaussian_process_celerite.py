"""
pylag.gaussian_process

Provides pyLag functionality for fitting light curves using gaussian processes

Classes
-------


v1.0 09/03/2017 - D.R. Wilkins
"""
import numpy as np


from .lightcurve import *
from .gaussian_process import *
import celerite
from celerite import terms
from scipy.optimize import minimize


class GPLightCurve_Celerite(GPLightCurve):
    def __init__(self, filename=None, t=[], r=[], e=[], lc=None, zero_nan=True, kernel=None, kernel_pars=(1.0/np.sqrt(2.0), 1E-5), run_fit=True, use_errors=True, noise_kernel=False, lognorm=False, remove_gaps=True, remove_nan=False):
        if lc is not None:
            t = lc.time
            r = lc.rate
            e = lc.error
        LightCurve.__init__(self, filename, t, r, e, interp_gaps=False, zero_nan=zero_nan, trim=False)

        # need to remove the gaps from the light curve
        # (only store the non-zero time bins)
        if remove_gaps:
            self.remove_gaps(to_self=True)
        elif remove_nan:
            self.remove_nan(to_self=True)

        self.mean_rate = self.mean()
        self.var = np.var(self.rate)

        if kernel is not None:
            self.kernel = kernel
        else:
            Q, w0 = kernel_pars
            S0 = self.var / (w0 * Q)
            bounds = dict(log_S0=(-15, 15), log_Q=(-15, 15), log_omega0=(-15, 15))
            self.kernel = terms.SHOTerm(log_S0=np.log(S0), log_Q=np.log(Q), log_omega0=np.log(w0), bounds=bounds)
            self.kernel.freeze_parameter("log_Q")
            if noise_kernel:
                noise_level = np.sqrt(self.mean_rate * self.dt) / (self.mean_rate * self.dt)
                self.kernel += WhiteKernel(noise_level=noise_level, noise_level_bounds=(1e-10, 2*noise_level))

            print(self.kernel)

        self.gp = celerite.GP(self.kernel, mean=self.mean_rate)
        if use_errors:
            self.gp.compute(self.time, self.error)
        else:
            self.gp.compute(self.time)

        self.lognorm = lognorm
        if self.lognorm:
            self.error = self.error / self.rate
            self.rate = np.log(self.rate)

        if run_fit:
            self.fit()

    def fit(self):
        initial_params = self.gp.get_parameter_vector()
        bounds = self.gp.get_parameter_bounds()

        def gp_minus_log_likelihood(params, y, gp):
            gp.set_parameter_vector(params)
            return -gp.log_likelihood(y)

        r = minimize(gp_minus_log_likelihood, initial_params, method="L-BFGS-B", bounds=bounds, args=(self.rate, self.gp))
        self.gp.set_parameter_vector(r.x)
        print(r)

    def predict(self, t=None):
        if t is None:
            t = np.arange(self.time.min(), self.time.max(), np.min(np.diff(self.time)))

        r, var = self.gp.predict(self.rate, t, return_var=True)
        e = np.sqrt(var)
        if self.lognorm:
            r = np.exp(r)
            e = r * e
        return LightCurve(t=t, r=r, e=e)

    def sample(self, n_samples=1, t=None):
        if t is None:
            t = np.arange(self.time.min(), self.time.max(), np.min(np.diff(self.time)))
        r = self.gp.sample_conditional(self.rate, t, n_samples)
        e = np.zeros(t.shape)
        if n_samples == 1:
            if self.lognorm:
                return LightCurve(t=t, r=np.exp(r[0]), e=e)
            else:
                return LightCurve(t=t, r=r[0], e=e)
        else:
            if self.lognorm:
                return [LightCurve(t=t, r=np.exp(r[n, :]), e=e) for n in range(n_samples)]
            else:
                return [LightCurve(t=t, r=r[n,:], e=e) for n in range(n_samples)]

