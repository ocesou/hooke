# Copyright (C) 2008-2010 W. Trevor King <wking@drexel.edu>
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

"""Wrap :mod:`numpy.fft` to produce 1D unitary transforms and power spectra.

Define some FFT wrappers to reduce clutter.
Provides a unitary discrete FFT and a windowed version.
Based on :func:`numpy.fft.rfft`.

Main entry functions:

* :func:`unitary_rfft`
* :func:`power_spectrum`
* :func:`unitary_power_spectrum`
* :func:`avg_power_spectrum`
* :func:`unitary_avg_power_spectrum`
"""

import unittest

from numpy import log2, floor, round, ceil, abs, pi, exp, cos, sin, sqrt, \
    sinc, arctan2, array, ones, arange, linspace, zeros, \
    uint16, float, concatenate, fromfile, argmax, complex
from numpy.fft import rfft


TEST_PLOTS = False

def floor_pow_of_two(num):
    """Round `num` down to the closest exact a power of two.

    Examples
    --------

    >>> floor_pow_of_two(3)
    2
    >>> floor_pow_of_two(11)
    8
    >>> floor_pow_of_two(15)
    8
    """
    lnum = log2(num)
    if int(lnum) != lnum:
        num = 2**floor(lnum)
    return int(num)

def round_pow_of_two(num):
    """Round `num` to the closest exact a power of two on a log scale.

    Examples
    --------

    >>> round_pow_of_two(2.9) # Note rounding on *log scale*
    4
    >>> round_pow_of_two(11)
    8
    >>> round_pow_of_two(15)
    16
    """
    lnum = log2(num)
    if int(lnum) != lnum:
        num = 2**round(lnum)
    return int(num)

def ceil_pow_of_two(num):
    """Round `num` up to the closest exact a power of two.

    Examples
    --------

    >>> ceil_pow_of_two(3)
    4
    >>> ceil_pow_of_two(11)
    16
    >>> ceil_pow_of_two(15)
    16
    """
    lnum = log2(num)
    if int(lnum) != lnum:
        num = 2**ceil(lnum)
    return int(num)

def unitary_rfft(data, freq=1.0):
    """Compute the unitary Fourier transform of real data.

    Unitary = preserves power [Parseval's theorem].

    Parameters
    ----------
    data : iterable
        Real (not complex) data taken with a sampling frequency `freq`.
    freq : real
        Sampling frequency.

    Returns
    -------
    freq_axis,trans : numpy.ndarray
        Arrays ready for plotting.

    Notes
    -----
    
    If the units on your data are Volts,
    and your sampling frequency is in Hz,
    then `freq_axis` will be in Hz,
    and `trans` will be in Volts.
    """
    nsamps = floor_pow_of_two(len(data))
    # Which should satisfy the discrete form of Parseval's theorem
    #   n-1               n-1
    #   SUM |x_m|^2 = 1/n SUM |X_k|^2. 
    #   m=0               k=0
    # However, we want our FFT to satisfy the continuous Parseval eqn
    #   int_{-infty}^{infty} |x(t)|^2 dt = int_{-infty}^{infty} |X(f)|^2 df
    # which has the discrete form
    #   n-1              n-1
    #   SUM |x_m|^2 dt = SUM |X'_k|^2 df
    #   m=0              k=0
    # with X'_k = AX, this gives us
    #   n-1                     n-1
    #   SUM |x_m|^2 = A^2 df/dt SUM |X'_k|^2
    #   m=0                     k=0
    # so we see
    #   A^2 df/dt = 1/n
    #   A^2 = 1/n dt/df
    # From Numerical Recipes (http://www.fizyka.umk.pl/nrbook/bookcpdf.html),
    # Section 12.1, we see that for a sampling rate dt, the maximum frequency
    # f_c in the transformed data is the Nyquist frequency (12.1.2)
    #   f_c = 1/2dt
    # and the points are spaced out by (12.1.5)
    #   df = 1/ndt
    # so
    #   dt = 1/ndf
    #   dt/df = 1/ndf^2
    #   A^2 = 1/n^2df^2
    #   A = 1/ndf = ndt/n = dt
    # so we can convert the Numpy transformed data to match our unitary
    # continuous transformed data with (also NR 12.1.8)
    #   X'_k = dtX = X / <sampling freq>
    trans = rfft(data[0:nsamps]) / float(freq)
    freq_axis = linspace(0, freq/2, nsamps/2+1)
    return (freq_axis, trans)

def power_spectrum(data, freq=1.0):
    """Compute the power spectrum of the time series `data`.

    Parameters
    ----------
    data : iterable
        Real (not complex) data taken with a sampling frequency `freq`.
    freq : real
        Sampling frequency.

    Returns
    -------
    freq_axis,power : numpy.ndarray
        Arrays ready for plotting.

    Notes
    -----
    If the number of samples in `data` is not an integer power of two,
    the FFT ignores some of the later points.

    See Also
    --------
    unitary_power_spectrum,avg_power_spectrum
    """
    nsamps = floor_pow_of_two(len(data))
    
    freq_axis = linspace(0, freq/2, nsamps/2+1)
    # nsamps/2+1 b/c zero-freq and nyqist-freq are both fully real.
    # >>> help(numpy.fft.fftpack.rfft) for Numpy's explaination.
    # See Numerical Recipies for a details.
    trans = rfft(data[0:nsamps])
    power = trans * trans.conj() # We want the square of the amplitude.
    return (freq_axis, power)

def unitary_power_spectrum(data, freq=1.0):
    """Compute the unitary power spectrum of the time series `data`.

    See Also
    --------
    power_spectrum,unitary_avg_power_spectrum
    """
    freq_axis,power = power_spectrum(data, freq)
    # One sided power spectral density, so 2|H(f)|**2 (see NR 2nd edition 12.0.14, p498)
    #
    # numpy normalizes with 1/N on the inverse transform ifft,
    # so we should normalize the freq-space representation with 1/sqrt(N).
    # But we're using the rfft, where N points are like N/2 complex points, so 1/sqrt(N/2)
    # So the power gets normalized by that twice and we have 2/N
    #
    # On top of this, the FFT assumes a sampling freq of 1 per second,
    # and we want to preserve area under our curves.
    # If our total time T = len(data)/freq is smaller than 1,
    # our df_real = freq/len(data) is bigger that the FFT expects (dt_fft = 1/len(data)), 
    # and we need to scale the powers down to conserve area.
    # df_fft * F_fft(f) = df_real *F_real(f)
    # F_real = F_fft(f) * (1/len)/(freq/len) = F_fft(f)*freq
    # So the power gets normalized by *that* twice and we have 2/N * freq**2

    # power per unit time
    # measure x(t) for time T
    # X(f)   = int_0^T x(t) exp(-2 pi ift) dt
    # PSD(f) = 2 |X(f)|**2 / T

    # total_time = len(data)/float(freq)
    # power *= 2.0 / float(freq)**2   /   total_time
    # power *= 2.0 / freq**2   *   freq / len(data)
    power *= 2.0 / (freq * float(len(data)))

    return (freq_axis, power)

def window_hann(length):
    r"""Returns a Hann window array with length entries

    Notes
    -----
    The Hann window with length :math:`L` is defined as

    .. math:: w_i = \frac{1}{2} (1-\cos(2\pi i/L))
    """
    win = zeros((length,), dtype=float)
    for i in range(length):
        win[i] = 0.5*(1.0-cos(2.0*pi*float(i)/(length)))
    # avg value of cos over a period is 0
    # so average height of Hann window is 0.5
    return win

def avg_power_spectrum(data, freq=1.0, chunk_size=2048,
                       overlap=True, window=window_hann):
    """Compute the avgerage power spectrum of `data`.

    Parameters
    ----------
    data : iterable
        Real (not complex) data taken with a sampling frequency `freq`.
    freq : real
        Sampling frequency.
    chunk_size : int
        Number of samples per chunk.  Use a power of two.
    overlap: {True,False}
        If `True`, each chunk overlaps the previous chunk by half its
        length.  Otherwise, the chunks are end-to-end, and not
        overlapping.
    window: iterable
        Weights used to "smooth" the chunks, there is a whole science
        behind windowing, but if you're not trying to squeeze every
        drop of information out of your data, you'll be OK with the
        default Hann window.

    Returns
    -------
    freq_axis,power : numpy.ndarray
        Arrays ready for plotting.

    Notes
    -----
    The average power spectrum is computed by breaking `data` into
    chunks of length `chunk_size`.  These chunks are transformed
    individually into frequency space and then averaged together.

    See Numerical Recipes 2 section 13.4 for a good introduction to
    the theory.

    If the number of samples in `data` is not a multiple of
    `chunk_size`, we ignore the extra points.
    """
    assert chunk_size == floor_pow_of_two(chunk_size), \
        "chunk_size %d should be a power of 2" % chunk_size

    nchunks = len(data)/chunk_size # integer division = implicit floor
    if overlap:
        chunk_step = chunk_size/2
    else:
        chunk_step = chunk_size
    
    win = window(chunk_size) # generate a window of the appropriate size
    freq_axis = linspace(0, freq/2, chunk_size/2+1)
    # nsamps/2+1 b/c zero-freq and nyqist-freq are both fully real.
    # >>> help(numpy.fft.fftpack.rfft) for Numpy's explaination.
    # See Numerical Recipies for a details.
    power = zeros((chunk_size/2+1,), dtype=float)
    for i in range(nchunks):
        starti = i*chunk_step
        stopi = starti+chunk_size
        fft_chunk = rfft(data[starti:stopi]*win)
        p_chunk = fft_chunk * fft_chunk.conj() 
        power += p_chunk.astype(float)
    power /= float(nchunks)
    return (freq_axis, power)

def unitary_avg_power_spectrum(data, freq=1.0, chunk_size=2048,
                               overlap=True, window=window_hann):
    """Compute the unitary avgerage power spectrum of `data`.

    See Also
    --------
    avg_power_spectrum,unitary_power_spectrum
    """
    freq_axis,power = avg_power_spectrum(data, freq, chunk_size,
                                         overlap, window)
    #        2.0 / (freq * chunk_size)          |rfft()|**2 --> unitary_power_spectrum
    power *= 2.0 / (freq*float(chunk_size)) * 8/3 # see unitary_power_spectrum()            
    #                                       * 8/3  to remove power from windowing
    #  <[x(t)*w(t)]**2> = <x(t)**2 * w(t)**2> ~= <x(t)**2> * <w(t)**2>
    # where the ~= is because the frequency of x(t) >> the frequency of w(t).
    # So our calulated power has and extra <w(t)**2> in it.
    # For the Hann window, <w(t)**2> = <0.5(1 + 2cos + cos**2)> = 1/4 + 0 + 1/8 = 3/8
    # For low frequency components, where the frequency of x(t) is ~= the frequency of w(t),
    # The normalization is not perfect. ??
    # The normalization approaches perfection as chunk_size -> infinity.
    return (freq_axis, power)



class TestRFFT (unittest.TestCase):
    r"""Ensure Numpy's FFT algorithm acts as expected.

    Notes
    -----

    The expected return values are [#dft]_:

    .. math:: X_k = \sum_{m=0}^{n-1} x_m \exp^{-2\pi imk/n}

    .. [#dft] See the *Background information* section of :mod:`numpy.fft`.
    """
    def run_rfft(self, xs, Xs):
        i = complex(0,1)
        n = len(xs)
        Xa = []
        for k in range(n):
            Xa.append(sum([x*exp(-2*pi*i*m*k/n) for x,m in zip(xs,range(n))]))
            if k < len(Xs):
                assert (Xs[k]-Xa[k])/abs(Xa[k]) < 1e-6, \
                    "rfft mismatch on element %d: %g != %g, relative error %g" \
                    % (k, Xs[k], Xa[k], (Xs[k]-Xa[k])/abs(Xa[k]))
        # Which should satisfy the discrete form of Parseval's theorem
        #   n-1               n-1
        #   SUM |x_m|^2 = 1/n SUM |X_k|^2. 
        #   m=0               k=0
        timeSum = sum([abs(x)**2 for x in xs])
        freqSum = sum([abs(X)**2 for X in Xa])
        assert abs(freqSum/float(n) - timeSum)/timeSum < 1e-6, \
            "Mismatch on Parseval's, %g != 1/%d * %g" % (timeSum, n, freqSum)

    def test_rfft(self):
        xs = [1,2,3,1,2,3,1,2,3,1,2,3,1,2,3,1]
        self.run_rfft(xs, rfft(xs))

class TestUnitaryRFFT (unittest.TestCase):
    """Verify `unitary_rfft`.
    """
    def run_unitary_rfft_parsevals(self, xs, freq, freqs, Xs):
        """Check the discretized integral form of Parseval's theorem

        Notes
        -----

        Which is:

        .. math:: \sum_{m=0}^{n-1} |x_m|^2 dt = \sum_{k=0}^{n-1} |X_k|^2 df
        """
        dt = 1.0/freq
        df = freqs[1]-freqs[0]
        assert (df - 1/(len(xs)*dt))/df < 1e-6, \
            "Mismatch in spacing, %g != 1/(%d*%g)" % (df, len(xs), dt)
        Xa = list(Xs)
        for k in range(len(Xs)-1,1,-1):
            Xa.append(Xa[k])
        assert len(xs) == len(Xa), "Length mismatch %d != %d" % (len(xs), len(Xa))
        lhs = sum([abs(x)**2 for x in xs]) * dt
        rhs = sum([abs(X)**2 for X in Xa]) * df
        assert abs(lhs - rhs)/lhs < 1e-4, "Mismatch on Parseval's, %g != %g" \
            % (lhs, rhs)
    
    def test_unitary_rfft_parsevals(self):
        "Test unitary rfft on Parseval's theorem"
        xs = [1,2,3,1,2,3,1,2,3,1,2,3,1,2,3,1]
        dt = pi
        freqs,Xs = unitary_rfft(xs, 1.0/dt)
        self.run_unitary_rfft_parsevals(xs, 1.0/dt, freqs, Xs)
    
    def rect(self, t):
        r"""Rectangle function.

        Notes
        -----

        .. math::

            \rect(t) = \begin{cases}
               1& \text{if $|t| < 0.5$}, \\
               0& \text{if $|t| \ge 0.5$}.
                       \end{cases}
        """
        if abs(t) < 0.5:
            return 1
        else:
            return 0
    
    def run_unitary_rfft_rect(self, a=1.0, time_shift=5.0, samp_freq=25.6,
                              samples=256):
        r"""Test `unitary_rttf` on known function `rect(at)`.

        Notes
        -----

        Analytic result:

        .. math:: \rfft(\rect(at)) = 1/|a|\cdot\sinc(f/a)
        """
        samp_freq = float(samp_freq)
        a = float(a)
    
        x = zeros((samples,), dtype=float)
        dt = 1.0/samp_freq
        for i in range(samples):
            t = i*dt
            x[i] = self.rect(a*(t-time_shift))
        freq_axis, X = unitary_rfft(x, samp_freq)
        #_test_unitary_rfft_parsevals(x, samp_freq, freq_axis, X)
    
        # remove the phase due to our time shift
        j = complex(0.0,1.0) # sqrt(-1)
        for i in range(len(freq_axis)):
            f = freq_axis[i]
            inverse_phase_shift = exp(j*2.0*pi*time_shift*f)
            X[i] *= inverse_phase_shift
    
        expected = zeros((len(freq_axis),), dtype=float)
        # normalized sinc(x) = sin(pi x)/(pi x)
        # so sinc(0.5) = sin(pi/2)/(pi/2) = 2/pi
        assert sinc(0.5) == 2.0/pi, "abnormal sinc()"
        for i in range(len(freq_axis)):
            f = freq_axis[i]
            expected[i] = 1.0/abs(a) * sinc(f/a)
    
        if TEST_PLOTS:
            pylab.figure()
            pylab.subplot(211)
            pylab.plot(arange(0, dt*samples, dt), x)
            pylab.title('time series')
            pylab.subplot(212)
            pylab.plot(freq_axis, X.real, 'r.')
            pylab.plot(freq_axis, X.imag, 'g.')
            pylab.plot(freq_axis, expected, 'b-')
            pylab.title('freq series')
    
    def test_unitary_rfft_rect(self):
        "Test unitary FFTs on variously shaped rectangular functions."
        self.run_unitary_rfft_rect(a=0.5)
        self.run_unitary_rfft_rect(a=2.0)
        self.run_unitary_rfft_rect(a=0.7, samp_freq=50, samples=512)
        self.run_unitary_rfft_rect(a=3.0, samp_freq=60, samples=1024)
    
    def gaussian(self, a, t):
        r"""Gaussian function.

        Notes
        -----

        .. math:: \gaussian(a,t) = \exp^{-at^2}
        """
        return exp(-a * t**2)
    
    def run_unitary_rfft_gaussian(self, a=1.0, time_shift=5.0, samp_freq=25.6,
                                  samples=256):
        r"""Test `unitary_rttf` on known function `gaussian(a,t)`.

        Notes
        -----

        Analytic result:

        .. math::

            \rfft(\gaussian(a,t)) = \sqrt{\pi/a} \cdot \gaussian(1/a,\pi f)
        """
        samp_freq = float(samp_freq)
        a = float(a)
    
        x = zeros((samples,), dtype=float)
        dt = 1.0/samp_freq
        for i in range(samples):
            t = i*dt
            x[i] = self.gaussian(a, (t-time_shift))
        freq_axis, X = unitary_rfft(x, samp_freq)
        #_test_unitary_rfft_parsevals(x, samp_freq, freq_axis, X)
    
        # remove the phase due to our time shift
        j = complex(0.0,1.0) # sqrt(-1)
        for i in range(len(freq_axis)):
            f = freq_axis[i]
            inverse_phase_shift = exp(j*2.0*pi*time_shift*f)
            X[i] *= inverse_phase_shift
    
        expected = zeros((len(freq_axis),), dtype=float)
        for i in range(len(freq_axis)):
            f = freq_axis[i]
            expected[i] = sqrt(pi/a) * self.gaussian(1.0/a, pi*f) # see Wikipedia, or do the integral yourself.
    
        if TEST_PLOTS:
            pylab.figure()
            pylab.subplot(211)
            pylab.plot(arange(0, dt*samples, dt), x)
            pylab.title('time series')
            pylab.subplot(212)
            pylab.plot(freq_axis, X.real, 'r.')
            pylab.plot(freq_axis, X.imag, 'g.')
            pylab.plot(freq_axis, expected, 'b-')
            pylab.title('freq series')
    
    def test_unitary_rfft_gaussian(self):
        "Test unitary FFTs on variously shaped gaussian functions."
        self.run_unitary_rfft_gaussian(a=0.5)
        self.run_unitary_rfft_gaussian(a=2.0)
        self.run_unitary_rfft_gaussian(a=0.7, samp_freq=50, samples=512)
        self.run_unitary_rfft_gaussian(a=3.0, samp_freq=60, samples=1024)

class TestUnitaryPowerSpectrum (unittest.TestCase):
    def run_unitary_power_spectrum_sin(self, sin_freq=10, samp_freq=512,
                                       samples=1024):
        x = zeros((samples,), dtype=float)
        samp_freq = float(samp_freq)
        for i in range(samples):
            x[i] = sin(2.0 * pi * (i/samp_freq) * sin_freq)
        freq_axis, power = unitary_power_spectrum(x, samp_freq)
        imax = argmax(power)
    
        expected = zeros((len(freq_axis),), dtype=float)
        df = samp_freq/float(samples) # df = 1/T, where T = total_time
        i = int(sin_freq/df)
        # average power per unit time is 
        #  P = <x(t)**2>
        # average value of sin(t)**2 = 0.5    (b/c sin**2+cos**2 == 1)
        # so average value of (int sin(t)**2 dt) per unit time is 0.5
        #  P = 0.5
        # we spread that power over a frequency bin of width df, sp
        #  P(f0) = 0.5/df
        # where f0 is the sin's frequency
        #
        # or:
        # FFT of sin(2*pi*t*f0) gives
        #  X(f) = 0.5 i (delta(f-f0) - delta(f-f0)),
        # (area under x(t) = 0, area under X(f) = 0)
        # so one sided power spectral density (PSD) per unit time is
        #  P(f) = 2 |X(f)|**2 / T
        #       = 2 * |0.5 delta(f-f0)|**2 / T
        #       = 0.5 * |delta(f-f0)|**2 / T
        # but we're discrete and want the integral of the 'delta' to be 1, 
        # so 'delta'*df = 1  --> 'delta' = 1/df, and
        #  P(f) = 0.5 / (df**2 * T)
        #       = 0.5 / df                (T = 1/df)
        expected[i] = 0.5 / df
    
        print "The power should be a peak at %g Hz of %g (%g, %g)" % \
            (sin_freq, expected[i], freq_axis[imax], power[imax])
        Pexp = 0
        P    = 0
        for i in range(len(freq_axis)):
            Pexp += expected[i] *df
            P    += power[i] * df
        print " The total power should be %g (%g)" % (Pexp, P)
    
        if TEST_PLOTS:
            pylab.figure()
            pylab.subplot(211)
            pylab.plot(arange(0, samples/samp_freq, 1.0/samp_freq), x, 'b-')
            pylab.title('time series')
            pylab.subplot(212)
            pylab.plot(freq_axis, power, 'r.')
            pylab.plot(freq_axis, expected, 'b-')
            pylab.title('%g samples of sin at %g Hz' % (samples, sin_freq))
    
    def test_unitary_power_spectrum_sin(self):
        "Test unitary power spectrums on variously shaped sin functions"
        self.run_unitary_power_spectrum_sin(sin_freq=5, samp_freq=512, samples=1024)
        self.run_unitary_power_spectrum_sin(sin_freq=5, samp_freq=512, samples=2048)
        self.run_unitary_power_spectrum_sin(sin_freq=5, samp_freq=512, samples=4098)
        self.run_unitary_power_spectrum_sin(sin_freq=7, samp_freq=512, samples=1024)
        self.run_unitary_power_spectrum_sin(sin_freq=5, samp_freq=1024, samples=2048)
        # finally, with some irrational numbers, to check that I'm not getting lucky
        self.run_unitary_power_spectrum_sin(sin_freq=pi, samp_freq=100*exp(1), samples=1024)
        # test with non-integer number of periods
        self.run_unitary_power_spectrum_sin(sin_freq=5, samp_freq=512, samples=256)
    
    def run_unitary_power_spectrum_delta(self, amp=1, samp_freq=1,
                                         samples=256):
        """TODO
        """
        x = zeros((samples,), dtype=float)
        samp_freq = float(samp_freq)
        x[0] = amp
        freq_axis, power = unitary_power_spectrum(x, samp_freq)
    
        # power = <x(t)**2> = (amp)**2 * dt/T
        # we spread that power over the entire freq_axis [0,fN], so
        #  P(f)  = (amp)**2 dt / (T fN)
        # where
        #  dt = 1/samp_freq        (sample period)
        #  T  = samples/samp_freq  (total time of data aquisition)
        #  fN = 0.5 samp_freq      (Nyquist frequency)
        # so
        #  P(f) = amp**2 / (samp_freq * samples/samp_freq * 0.5 samp_freq)
        #       = 2 amp**2 / (samp_freq*samples)
        expected_amp = 2.0 * amp**2 / (samp_freq * samples)
        expected = ones((len(freq_axis),), dtype=float) * expected_amp
    
        print "The power should be flat at y = %g (%g)" % (expected_amp, power[0])
        
        if TEST_PLOTS:
            pylab.figure()
            pylab.subplot(211)
            pylab.plot(arange(0, samples/samp_freq, 1.0/samp_freq), x, 'b-')
            pylab.title('time series')
            pylab.subplot(212)
            pylab.plot(freq_axis, power, 'r.')
            pylab.plot(freq_axis, expected, 'b-')
            pylab.title('%g samples of delta amp %g' % (samples, amp))
    
    def _test_unitary_power_spectrum_delta(self):
        "Test unitary power spectrums on various delta functions"
        _test_unitary_power_spectrum_delta(amp=1, samp_freq=1.0, samples=1024)
        _test_unitary_power_spectrum_delta(amp=1, samp_freq=1.0, samples=2048)
        _test_unitary_power_spectrum_delta(amp=1, samp_freq=0.5, samples=2048)# expected = 2*computed
        _test_unitary_power_spectrum_delta(amp=1, samp_freq=2.0, samples=2048)# expected = 0.5*computed
        _test_unitary_power_spectrum_delta(amp=3, samp_freq=1.0, samples=1024)
        _test_unitary_power_spectrum_delta(amp=pi, samp_freq=exp(1), samples=1024)
    
    def gaussian(self, area, mean, std, t):
        "Integral over all time = area (i.e. normalized for area=1)"
        return area/(std*sqrt(2.0*pi)) * exp(-0.5*((t-mean)/std)**2)
        
    def run_unitary_power_spectrum_gaussian(self, area=2.5, mean=5, std=1,
                                            samp_freq=10.24 ,samples=512):
        """TODO.
        """
        x = zeros((samples,), dtype=float)
        mean = float(mean)
        for i in range(samples):
            t = i/float(samp_freq)
            x[i] = self.gaussian(area, mean, std, t)
        freq_axis, power = unitary_power_spectrum(x, samp_freq)
    
        # generate the predicted curve
        # by comparing our self.gaussian() form to _gaussian(),
        # we see that the Fourier transform of x(t) has parameters:
        #  std'  = 1/(2 pi std)    (references declaring std' = 1/std are converting to angular frequency, not frequency like we are)
        #  area' = area/[std sqrt(2*pi)]   (plugging into FT of _gaussian() above)
        #  mean' = 0               (changing the mean in the time-domain just changes the phase in the freq-domain)
        # So our power spectral density per unit time is given by
        #  P(f) = 2 |X(f)|**2 / T
        # Where
        #  T  = samples/samp_freq  (total time of data aquisition)
        mean = 0.0
        area = area /(std*sqrt(2.0*pi))
        std = 1.0/(2.0*pi*std)
        expected = zeros((len(freq_axis),), dtype=float)
        df = float(samp_freq)/samples # 1/total_time ( = freq_axis[1]-freq_axis[0] = freq_axis[1])
        for i in range(len(freq_axis)):
            f = i*df
            gaus = self.gaussian(area, mean, std, f)
            expected[i] = 2.0 * gaus**2 * samp_freq/samples
        print "The power should be a half-gaussian, ",
        print "with a peak at 0 Hz with amplitude %g (%g)" % (expected[0], power[0])
    
        if TEST_PLOTS:
            pylab.figure()
            pylab.subplot(211)
            pylab.plot(arange(0, samples/samp_freq, 1.0/samp_freq), x, 'b-')
            pylab.title('time series')
            pylab.subplot(212)
            pylab.plot(freq_axis, power, 'r.')
            pylab.plot(freq_axis, expected, 'b-')
            pylab.title('freq series')
    
    def test_unitary_power_spectrum_gaussian(self):
        "Test unitary power spectrums on various gaussian functions"
        for area in [1,pi]:
            for std in [1,sqrt(2)]:
                for samp_freq in [10.0, exp(1)]:
                    for samples in [1024,2048]:
                        self.run_unitary_power_spectrum_gaussian(
                            area=area, std=std, samp_freq=samp_freq,
                            samples=samples)

class TestUnitaryAvgPowerSpectrum (unittest.TestCase):
    def run_unitary_avg_power_spectrum_sin(self, sin_freq=10, samp_freq=512,
                                           samples=1024, chunk_size=512,
                                           overlap=True, window=window_hann):
        """TODO
        """
        x = zeros((samples,), dtype=float)
        samp_freq = float(samp_freq)
        for i in range(samples):
            x[i] = sin(2.0 * pi * (i/samp_freq) * sin_freq)
        freq_axis, power = unitary_avg_power_spectrum(x, samp_freq, chunk_size,
                                                      overlap, window)
        imax = argmax(power)
    
        expected = zeros((len(freq_axis),), dtype=float)
        df = samp_freq/float(chunk_size) # df = 1/T, where T = total_time
        i = int(sin_freq/df)
        expected[i] = 0.5 / df # see _test_unitary_power_spectrum_sin()
    
        print "The power should be a peak at %g Hz of %g (%g, %g)" % \
            (sin_freq, expected[i], freq_axis[imax], power[imax])
        Pexp = 0
        P    = 0
        for i in range(len(freq_axis)):
            Pexp += expected[i] * df
            P    += power[i] * df
        print " The total power should be %g (%g)" % (Pexp, P)
    
        if TEST_PLOTS:
            pylab.figure()
            pylab.subplot(211)
            pylab.plot(arange(0, samples/samp_freq, 1.0/samp_freq), x, 'b-')
            pylab.title('time series')
            pylab.subplot(212)
            pylab.plot(freq_axis, power, 'r.')
            pylab.plot(freq_axis, expected, 'b-')
            pylab.title('%g samples of sin at %g Hz' % (samples, sin_freq))
    
    def test_unitary_avg_power_spectrum_sin(self):
        "Test unitary avg power spectrums on variously shaped sin functions."
        self.run_unitary_avg_power_spectrum_sin(sin_freq=5, samp_freq=512, samples=1024)
        self.run_unitary_avg_power_spectrum_sin(sin_freq=5, samp_freq=512, samples=2048)
        self.run_unitary_avg_power_spectrum_sin(sin_freq=5, samp_freq=512, samples=4098)
        self.run_unitary_avg_power_spectrum_sin(sin_freq=17, samp_freq=512, samples=1024)
        self.run_unitary_avg_power_spectrum_sin(sin_freq=5, samp_freq=1024, samples=2048)
        # test long wavelenth sin, so be closer to window frequency
        self.run_unitary_avg_power_spectrum_sin(sin_freq=1, samp_freq=1024, samples=2048)
        # finally, with some irrational numbers, to check that I'm not getting lucky
        self.run_unitary_avg_power_spectrum_sin(sin_freq=pi, samp_freq=100*exp(1), samples=1024)
