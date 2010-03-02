#!/usr/bin/env python

'''
results.py

Result and Results classes for Hooke.

Copyright 2009 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

from numpy import nan

import prettyformat
import lib.curve

DEFAULT_COLOR = 'green'
DEFAULT_DECIMAL = 2
DEFAULT_STYLE = 'scatter'

class Result(lib.curve.Curve):
    def __init__(self):
        lib.curve.Curve.__init__(self)
        self.color = DEFAULT_COLOR
        self.result = {}
        self.style = DEFAULT_STYLE

class Results(object):
    def __init__(self):
        self.columns = []
        self.decimals = {}
        self.has_multipliers = False
        self.multipliers = {}
        self.results = []
        self.separator='\t'
        self.units = {}

    def get_pretty_value(self, column, value):
        if self.has_multipliers and self.has_results():
            multiplier = self.multipliers[column]
            decimals = self.decimals[column]
            return prettyformat.pretty_format(value, '', decimals, multiplier, True)
        return str(value)

    def has_results(self):
        return len(self.results) > 0

    def get_header_as_list(self):
        header_list = []
        if self.has_results():
            if not self.has_multipliers:
                self.set_multipliers()
            for column in self.columns:
                unit_str = ''.join([prettyformat.get_prefix(self.multipliers[column]), self.units[column]])
                header_str = ''.join([column, ' [', unit_str, ']'])
                header_list.append(header_str)
        return header_list

    def get_header_as_str(self, separator=None):
        if separator is None:
            separator = self.separator
        return separator.join(map(str, self.get_header_as_list()))

    def get_result_as_list(self, index=0):
        if index >= 0 and index < len(self.results):
            result_list = []
            if self.has_results():
                if not self.has_multipliers:
                    self.set_multipliers()
                for column in self.columns:
                    result_str = prettyformat.pretty_format(self.results[index].result[column], '', self.decimals[column], self.multipliers[column], True)
                    result_list.append(result_str)
            return result_list
        else:
            return None

    def get_result_as_string(self, index=0):
        results_list = self.get_result_as_list(index)
        if results_list is not None:
            return self.separator.join(map(str, results_list))
        else:
            return ''

    def set_decimal(self, column, decimal=DEFAULT_DECIMAL):
        if self.decimals.has_key(column):
            self.decimals[column] = decimal

    def set_decimals(self, decimals=DEFAULT_DECIMAL):
        if decimals < 0:
            #set default value if necessary
            decimals = DEFAULT_DECIMAL
        for column in self.columns:
            self.decimals[column] = decimals

    def set_multipliers(self, index=0):
        if self.has_results():
            for column in self.columns:
                #result will contain the results dictionary at 'index'
                result = self.results[index].result
                #in position 0 of the result we find the value
                self.multipliers[column] = prettyformat.get_multiplier(result[column])
            self.has_multipliers = True
        else:
            self.has_multipliers = False

    def update(self):
        pass


class ResultsFJC(Results):
    def __init__(self):
        Results.__init__(self)
        self.columns = ['Contour length', 'sigma contour length', 'Kuhn length', 'sigma Kuhn length', 'Rupture force', 'Slope', 'Loading rate']
        self.units['Contour length'] = 'm'
        self.units['sigma contour length'] = 'm'
        self.units['Kuhn length'] = 'm'
        self.units['sigma Kuhn length'] = 'm'
        self.units['Rupture force'] = 'N'
        self.units['Slope'] = 'N/m'
        self.units['Loading rate'] = 'N/s'
        self.set_decimals(2)

    def set_multipliers(self, index=0):
        if self.has_results():
            for column in self.columns:
                #result will contain the results dictionary at 'index'
                result = self.results[index].result
                #in position 0 of the result we find the value
                if column == 'sigma contour length':
                    self.multipliers[column] = self.multipliers['Contour length']
                elif column == 'sigma Kuhn length':
                    self.multipliers[column] = self.multipliers['Kuhn length']
                else:
                    self.multipliers[column] = prettyformat.get_multiplier(result[column])
            self.has_multipliers = True
        else:
            self.has_multipliers = False

class ResultsMultiDistance(Results):
    def __init__(self):
        Results.__init__(self)
        self.columns = ['Distance']
        self.units['Distance'] = 'm'
        self.set_decimals(2)

    def update(self):
        if (self.results) > 0:
            for result in self.results:
                if result.visible:
                    reference_peak = result.x
                    break

            for result in self.results:
                if result.visible:
                    result.result['Distance'] = reference_peak - result.x
                    reference_peak = result.x
                else:
                    result.result['Distance'] = nan


class ResultsWLC(Results):
    def __init__(self):
        Results.__init__(self)
        self.columns = ['Contour length', 'sigma contour length', 'Persistence length', 'sigma persistence length', 'Rupture force', 'Slope', 'Loading rate']
        self.units['Contour length'] = 'm'
        self.units['sigma contour length'] = 'm'
        self.units['Persistence length'] = 'm'
        self.units['sigma persistence length'] = 'm'
        self.units['Rupture force'] = 'N'
        self.units['Slope'] = 'N/m'
        self.units['Loading rate'] = 'N/s'
        self.set_decimals(2)

    def set_multipliers(self, index=0):
        if self.has_results():
            for column in self.columns:
                #result will contain the results dictionary at 'index'
                result = self.results[index].result
                #in position 0 of the result we find the value
                if column == 'sigma contour length':
                    self.multipliers[column] = self.multipliers['Contour length']
                elif column == 'sigma persistence length':
                    self.multipliers[column] = self.multipliers['Persistence length']
                else:
                    self.multipliers[column] = prettyformat.get_multiplier(result[column])
            self.has_multipliers = True
        else:
            self.has_multipliers = False
