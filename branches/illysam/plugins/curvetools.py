#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
curvetools.py

General library of peak detection related functions.

Copyright ???? by ?
with modifications by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

class curvetoolsCommands:

    def fit_interval_nm(self, start_index, x_vect, nm, backwards):
        '''
        Calculates the number of points to fit, given a fit interval in nm
        start_index: index of point
        plot: plot to use
        backwards: if true, finds a point backwards.
        '''

        c = 0
        i = start_index
        maxlen=len(x_vect)
        while abs(x_vect[i] - x_vect[start_index]) * (10**9) < nm:
            if i == 0 or i == maxlen-1: #we reached boundaries of vector!
                return c
            if backwards:
                i -= 1
            else:
                i += 1
            c += 1
        return c

    def pickup_contact_point(self, filename=''):
        '''
        macro to pick up the contact point by clicking
        '''

        contact_point = self._measure_N_points(N=1, message='Please click on the contact point.')[0]
        contact_point_index = contact_point.index
        self.wlccontact_point = contact_point
        self.wlccontact_index = contact_point.index
        self.wlccurrent = filename
        return contact_point, contact_point_index
