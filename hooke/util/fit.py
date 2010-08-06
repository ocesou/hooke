# Copyright (C) 2010 W. Trevor King <wking@drexel.edu>
#
# This file is part of Hooke.
#
# Hooke is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Hooke is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General
# Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Hooke.  If not, see
# <http://www.gnu.org/licenses/>.

"""Provide :class:`ModelFitter` to make arbitrary model fitting easy.
"""

from numpy import arange, ndarray
from scipy.optimize import leastsq
import scipy.optimize


class PoorFit (ValueError):
    pass

class ModelFitter (object):
    """A convenient wrapper around :func:`scipy.optimize.leastsq`.

    TODO: look into :mod:`scipy.odr` as an alternative fitting
    algorithm (minimizing the sum of squares of orthogonal distances,
    vs. minimizing y distances).

    Parameters
    ----------
    d_data : array_like
        Deflection data to be analyzed for the contact position.
    info :
        Store any extra information useful inside your overridden
        methods.
    rescale : boolean
        Rescale parameters so the scale of each is 1.0.  Also rescale
        the data so data.std() == 1.0.

    Examples
    --------

    >>> from pprint import pprint
    >>> from Queue import Queue
    >>> import numpy

    You'll want to subclass `ModelFitter`, overriding at least
    `.model` and potentially the parameter and scale guessing
    methods.

    >>> class LinearModel (ModelFitter):
    ...     '''Simple linear model.
    ...
    ...     Levenberg-Marquardt is not how you want to solve this problem
    ...     for real systems, but it's a simple test case.
    ...     '''
    ...     def model(self, params):
    ...         '''A linear model.
    ...
    ...         Notes
    ...         -----
    ...         .. math:: y = p_0 x + p_1
    ...         '''
    ...         p = params  # convenient alias
    ...         self._model_data[:] = p[0]*arange(len(self._data)) + p[1]
    ...         return self._model_data
    ...     def guess_initial_params(self, outqueue=None):
    ...         return [float(self._data[-1] - self._data[0])/len(self._data),
    ...                 self._data[0]]
    ...     def guess_scale(self, params, outqueue=None):
    ...         slope_scale = params[0]/10.
    ...         if slope_scale == 0:  # data is expected to be flat
    ...             slope_scale = float(self._data.max()-self._data.min())/len(self._data)
    ...             if slope_scale == 0:  # data is completely flat
    ...                 slope_scale = 1.
    ...         offset_scale = self._data.std()/10.0
    ...         if offset_scale == 0:  # data is completely flat
    ...             offset_scale = 1.
    ...         return [slope_scale, offset_scale]
    >>> data = 20*numpy.sin(arange(1000)) + 7.*arange(1000) - 33.0
    >>> m = LinearModel(data)
    >>> outqueue = Queue()
    >>> slope,offset = m.fit(outqueue=outqueue)
    >>> info = outqueue.get(block=False)
    >>> pprint(info)  # doctest: +ELLIPSIS, +REPORT_UDIFF
    {'active fitted parameters': array([  6.999..., -32.889...]),
     'active parameters': array([  6.999..., -32.889...]),
     'active scale': [0.699..., 202.071...],
     'convergence flag': 2,
     'covariance matrix': array([[  1.199...e-08,  -5.993...e-06],
           [ -5.993...e-06,   3.994...e-03]]),
     'data scale factor': 1.0,
     'fitted parameters': array([  6.999..., -32.889...]),
     'info': {'fjac': array([[...]]),
              'fvec': array([...]),
              'ipvt': array([1, 2]),
              'nfev': 7,
              'qtf': array([  2.851...e-07,   1.992...e-06])},
     'initial parameters': [6.992..., -33.0],
     'message': 'The relative error between two consecutive iterates is at most 0.000...',
     'rescaled': False,
     'scale': [0.699..., 202.071...]}

    We round the outputs to protect the doctest against differences in
    machine rounding during computation.  We expect the values to be close
    to the input settings (slope 7, offset -33).

    >>> print '%.3f' % slope
    7.000
    >>> print '%.3f' % offset
    -32.890

    The offset is a bit off because, the range is not a multiple of
    :math:`2\pi`.

    We could also use rescaled parameters:

    >>> m = LinearModel(data, rescale=True)
    >>> outqueue = Queue()
    >>> slope,offset = m.fit(outqueue=outqueue)
    >>> print '%.3f' % slope
    7.000
    >>> print '%.3f' % offset
    -32.890
    """
    def __init__(self, *args, **kwargs):
        self.set_data(*args, **kwargs)

    def set_data(self, data, info=None, rescale=False):
        self._data = data
        self._model_data = ndarray(shape=data.shape, dtype=data.dtype)
        self.info = info
        self._rescale = rescale
        if rescale == True:
            self._data_scale_factor = data.std()
        else:
            self._data_scale_factor = 1.0

    def model(self, params):
        p = params  # convenient alias
        self._model_data[:] = arange(len(self._data))
        raise NotImplementedError

    def guess_initial_params(self, outqueue=None):
        return []

    def guess_scale(self, params, outqueue=None):
        return None

    def residual(self, params):
        if self._rescale == True:
            params = [p*s for p,s in zip(params, self._param_scale_factors)]
        residual = self._data - self.model(params)
        if self._rescale == True or False:
            residual /= self._data_scale_factor
        return residual

    def fit(self, initial_params=None, scale=None, outqueue=None, **kwargs):
        """
        Parameters
        ----------
        initial_params : iterable or None
            Initial parameter values for residual minimization.  If
            `None`, they are estimated from the data using
            :meth:`guess_initial_params`.
        scale : iterable or None
            Parameter length scales for residual minimization.  If
            `None`, they are estimated from the data using
            :meth:`guess_scale`.
        outqueue : Queue or None
            If given, will be used to output the data and fitted model
            for user verification.
        kwargs :
            Any additional arguments are passed through to `leastsq`.
        """
        if initial_params == None:
            initial_params = self.guess_initial_params(outqueue)
        if scale == None:
            scale = self.guess_scale(initial_params, outqueue)
        assert min(scale) > 0, scale
        if self._rescale == True:
            self._param_scale_factors = scale
            active_scale = [1.0 for s in scale]
            active_params = [p/s for p,s in zip(initial_params,
                                                self._param_scale_factors)]
        else:
            active_scale = scale
            active_params = initial_params
        params,cov,info,mesg,ier = leastsq(
            func=self.residual, x0=active_params, full_output=True,
            diag=active_scale, **kwargs)
        if self._rescale == True:
            active_params = params
            if len(initial_params) == 1:  # params is a float
                params = params * self._param_scale_factors[0]
            else:
                params = [p*s for p,s in zip(params,
                                             self._param_scale_factors)]
        else:
            active_params = params
        if outqueue != None:
            outqueue.put({
                    'rescaled': self._rescale,
                    'initial parameters': initial_params,
                    'active parameters': active_params,
                    'scale': scale,
                    'active scale': active_scale,
                    'data scale factor': self._data_scale_factor,
                    'active fitted parameters': active_params,
                    'fitted parameters': params,
                    'covariance matrix': cov,
                    'info': info,
                    'message': mesg,
                    'convergence flag': ier,
                    })
        return params

# Example ORD code from the old fit.py
#        def dist(px,py,linex,liney):
#            distancesx=scipy.array([(px-x)**2 for x in linex])
#            minindex=numpy.argmin(distancesx)
#            print px, linex[0], linex[-1]
#            return (py-liney[minindex])**2
#
#
#        def f_wlc(params,x,T=T):
#            '''
#            wlc function for ODR fitting
#            '''
#            lambd,pii=params
#            Kb=(1.38065e-23)
#            therm=Kb*T
#            y=(therm*pii/4.0) * (((1-(x*lambd))**-2) - 1 + (4*x*lambd))
#            return y
#
#        def f_wlc_plfix(params,x,pl_value=pl_value,T=T):
#            '''
#            wlc function for ODR fitting
#            '''
#            lambd=params
#            pii=1/pl_value
#            Kb=(1.38065e-23)
#            therm=Kb*T
#            y=(therm*pii/4.0) * (((1-(x*lambd))**-2) - 1 + (4*x*lambd))
#            return y
#
#        #make the ODR fit
#        realdata=scipy.odr.RealData(xchunk_corr_up,ychunk_corr_up)
#        if pl_value:
#            model=scipy.odr.Model(f_wlc_plfix)
#            o = scipy.odr.ODR(realdata, model, p0_plfix)
#        else:
#            model=scipy.odr.Model(f_wlc)
#            o = scipy.odr.ODR(realdata, model, p0)
#
#        o.set_job(fit_type=2)
#        out=o.run()
#        fit_out=[(1/i) for i in out.beta]
#
#        #Calculate fit errors from output standard deviations.
#        #We must propagate the error because we fit the *inverse* parameters!
#        #The error = (error of the inverse)*(value**2)
#        fit_errors=[]
#        for sd,value in zip(out.sd_beta, fit_out):
#            err_real=sd*(value**2)
#            fit_errors.append(err_real)
