#!/usr/bin/env python

'''
export.py

Export commands for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import lib.libhooke as lh
import wxversion
wxversion.select(lh.WX_GOOD)

import copy
import os.path
import time
import wx

class exportCommands(object):
    '''
    Export force curves, fits and results in different formats
    '''

    def _plug_init(self):
        pass

    def do_fits(self):
        '''
        Exports all fitting results (if available) in a columnar ASCII format.
        '''
        ext = self.GetStringFromConfig('export', 'fits', 'ext')
        folder = self.GetStringFromConfig('export', 'fits', 'folder')
        prefix = self.GetStringFromConfig('export', 'fits', 'prefix')
        separator = self.GetStringFromConfig('export', 'fits', 'separator')
        #TODO: add list for Tab, Space, Comma, Other
        #add string for Other

        active_file = self.GetActiveFile()
        plot = self.GetDisplayedPlot()

        #add empty columns before adding new results if necessary
        if plot is not None:
            for results_str, results in plot.results.items():
                for curve in results.results:
                    output = []
                    header_str = ''
                    if curve.visible:
                        header_str += curve.label + '_x (' + curve.units.x + ')' + separator + curve.label + '_y (' + curve.units.y + ')'
                        output.append(header_str)
                        for index, row in enumerate(curve.x):
                            output.append(separator.join([str(curve.x[index]), str(curve.y[index])]))
                    if output:
                        #TODO: add option to replace or add the new file extension
                        #add option to rename file from default.000 to default_000
                        filename = os.path.basename(active_file.filename)
                        filename = ''.join([prefix, filename, '_', curve.label, '.', ext])
                        filename = os.path.join(folder, filename)
                        output_file = open(filename, 'w')
                        output_file.write('\n'.join(output))
                        output_file.close

    def do_force_curve(self):
        '''
        TXT
        Saves the current curve as a text file
        Columns are, in order:
        X1 , Y1 , X2 , Y2 , X3 , Y3 ...

        -------------
        Syntax: txt [filename] {plot to export}
        '''

        ext = self.GetStringFromConfig('export', 'force_curve', 'ext')
        folder = self.GetStringFromConfig('export', 'force_curve', 'folder')
        prefix = self.GetStringFromConfig('export', 'force_curve', 'prefix')
        separator = self.GetStringFromConfig('export', 'force_curve', 'separator')
        #TODO: add list for Tab, Space, Comma, Other
        #add string for Other

        active_file = self.GetActiveFile()
        #create the header from the raw plot (i.e. only the force curve)
        plot = self.GetDisplayedPlotRaw()

        output = []
        header_str = ''
        for index, curve in enumerate(plot.curves):
            #TODO: only add labels for original curves (i.e. excluding anything added after the fact)
            header_str += curve.label + '_x (' + curve.units.x + ')' + separator + curve.label + '_y (' + curve.units.y + ')'
            if index < len(plot.curves) - 1:
                header_str += separator
        output.append(header_str)

        #export the displayed plot
        plot = self.GetDisplayedPlot()
        extension = plot.curves[lh.EXTENSION]
        retraction = plot.curves[lh.RETRACTION]
        for index, row in enumerate(extension.x):
            output.append(separator.join([str(extension.x[index]), str(extension.y[index]), str(retraction.x[index]), str(retraction.y[index])]))

        if output:
            #TODO: add option to replace or add the new file extension
            #add option to rename file from default.000 to default_000
            filename = os.path.basename(active_file.filename)
            filename = ''.join([prefix, filename, '.', ext])
            filename = os.path.join(folder, filename)
            output_file = open(filename, 'w')
            output_file.write('\n'.join(output))
            output_file.close

    def do_notes(self):
        '''
        Exports the note for all the files in a playlist.
        '''
        filename = self.GetStringFromConfig('export', 'notes', 'filename')
        folder = self.GetStringFromConfig('export', 'notes', 'folder')
        prefix = self.GetStringFromConfig('export', 'notes', 'prefix')
        use_playlist_filename = self.GetBoolFromConfig('export', 'notes', 'use_playlist_filename')
        
        playlist = self.GetActivePlaylist()
        output_str = ''
        for current_file in playlist.files:
            output_str = ''.join([output_str, current_file.filename, '  |  ', current_file.note, '\n'])
        if output_str:
            output_str = ''.join(['Notes taken at ', time.asctime(), '\n', playlist.filename, '\n', output_str])
            if use_playlist_filename:
                path, filename = os.path.split(playlist.filename)
                filename = lh.remove_extension(filename)
            filename = ''.join([prefix, filename, '.txt'])
            filename = os.path.join(folder, filename)
            output_file = open(filename, 'w')
            output_file.write(output_str)
            output_file.close
        else:
            dialog = wx.MessageDialog(None, 'No notes found, file not saved.', 'Info', wx.OK)
            dialog.ShowModal()

    def do_overlay(self):
        '''
        Exports all retraction files in a playlist with the same scale.
        The files can then be overlaid in a graphing program to see which
        ones have the same shape.
        Use this export command only on filtered lists as it takes a long time
        to complete even with a small number of curves.
        '''
        playlist = self.GetActivePlaylist()

        filename_prefix = self.GetStringFromConfig('export', 'overlay', 'prefix')

        differences_x = []
        differences_y = []
        number_of_curves = playlist.count
        message_str = ''.join([str(number_of_curves), ' files to load.\n\n'])
        progress_dialog = wx.ProgressDialog('Loading', message_str, maximum=number_of_curves, parent=self, style=wx.PD_APP_MODAL|wx.PD_SMOOTH|wx.PD_AUTO_HIDE)
        for index, current_file in enumerate(playlist.files):
            current_file.identify(self.drivers)
            plot = current_file.plot

            plot.raw_curves = copy.deepcopy(plot.curves)
            #apply all active plotmanipulators and add the 'manipulated' data
            for plotmanipulator in self.plotmanipulators:
                if self.GetBoolFromConfig('core', 'plotmanipulators', plotmanipulator.name):
                    plot = plotmanipulator.method(plot, current_file)
            #add corrected curves to plot
            plot.corrected_curves = copy.deepcopy(plot.curves)

            curve = current_file.plot.corrected_curves[lh.RETRACTION]
            differences_x.append(curve.x[0] - curve.x[-1])
            differences_y.append(curve.x[0] - curve.y[-1])
            progress_dialog.Update(index, ''.join([message_str, 'Loading ', str(index + 1), '/', str(number_of_curves)]))
        progress_dialog.Destroy()

        max_x = max(differences_x)
        max_y = max(differences_y)
        message_str = ''.join([str(number_of_curves), ' files to export.\n\n'])
        for index, current_file in enumerate(playlist.files):
            curve = current_file.plot.corrected_curves[lh.RETRACTION]
            first_x = curve.x[0]
            first_y = curve.y[0]
            new_x = [x - first_x for x in curve.x]
            new_y = [y - first_y for y in curve.y]
            new_x.append(-max_x)
            new_y.append(-max_y)
            output_str = ''
            for row_index, row in enumerate(new_x):
                output_str += ''.join([str(new_x[row_index]), ', ', str(new_y[row_index]), '\n'])

            if output_str:
                filename = ''.join([filename_prefix, current_file.name])
                filename = current_file.filename.replace(current_file.name, filename)
                output_file = open(filename, 'w')
                output_file.write(output_str)
                output_file.close
        progress_dialog.Destroy()

    def do_results(self, append=None, filename='', separator=''):
        '''
        Exports all visible fit results in a playlist into a delimited text file
        append: set append to True if you want to append to an existing results file
        filename: the filename and path of the results file
        separator: the separator between columns
        '''
        if not append:
            append = self.GetStringFromConfig('export', 'results', 'append')
        if filename == '':
            filename = self.GetStringFromConfig('export', 'results', 'filename')
        if separator == '':
            separator = self.GetStringFromConfig('export', 'results', 'separator')

        playlist = self.GetActivePlaylist()
        output_str = ''
        header_str = ''
        for current_file in playlist.files:
            if len(current_file.plot.results) > 0:
                for key in current_file.plot.results.keys():
                    #if there are different types of fit results in the playlist, the header might have to change
                    #here, we generate a temporary header and compare it to the current header
                    #if they are different, the tempeorary header is used
                    #we get the header from the fit and add the 'filename' column
                    temporary_header_str = ''.join([current_file.plot.results[key].get_header_as_str(), separator, 'Filename'])
                    if temporary_header_str != header_str:
                        header_str = ''.join([current_file.plot.results[key].get_header_as_str(), separator, 'Filename'])
                        output_str = ''.join([output_str, header_str, '\n'])
                    for index, result in enumerate(current_file.plot.results[key].results):
                        if result.visible:
                            #similar to above, we get the result from the fit and add the filename
                            line_str = current_file.plot.results[key].get_result_as_string(index)
                            line_str = ''.join([line_str, separator, current_file.filename])
                            output_str = ''.join([output_str, line_str, '\n'])
        if output_str:
            output_str = ''.join(['Analysis started ', time.asctime(), '\n', output_str])

            if append and os.path.isfile(filename):
                output_file = open(filename,'a')
            else:
                output_file = open(filename, 'w')
                output_file.write(output_str)
                output_file.close
        else:
            dialog = wx.MessageDialog(None, 'No results found, file not saved.', 'Info', wx.OK)
            dialog.ShowModal()
