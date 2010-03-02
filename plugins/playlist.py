#!/usr/bin/env python

'''
playlist.py

Playlist commands for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import lib.libhooke as lh
import wxversion
wxversion.select(lh.WX_GOOD)

import glob
import os.path
import wx

from lib.playlist import Playlist

class playlistCommands(object):
    '''
    Playlist commands to generate, save and load lists of force curves
    '''

    def _plug_init(self):
        pass

    def do_genlist(self, filemask='', folder=''):
        '''
        Generates a file playlist.
        Note: genlist does not *save* the playlist, it only generates it. In order to save a playlist, use savelist.

        filemask: set the filemask to use. For example, the default value '*.*' will include all files found in the playlist.
        folder: set the folder in which the data that you want to analyze resides
        detect_mfp1d: automatically uses '*deflection*' as filemask
                      MFP-1D files come in pairs (2009-10-20deflection4483.ibw and 2009-10-20LVDT4483.ibw). For the playlist to contain
                      only file per experiment, only deflection files are included.
        '''
        detect_mfp1d = self.GetBoolFromConfig('playlist', 'genlist', 'detect_mfp1d')
        if filemask == '':
            filemask = self.GetStringFromConfig('playlist', 'genlist', 'filemask')
        if detect_mfp1d:
            filemask = '*deflection*'
        if folder == '':
            folder = self.GetStringFromConfig('playlist', 'genlist', 'folder')
        if os.path.isdir(folder):
            path = os.path.join(folder, filemask)
            #expanding correctly the input list with the glob module :)
            files = glob.glob(path)
            files.sort()
            playlist = Playlist()
            for file_to_add in files:
                playlist.add_file(file_to_add)
            if playlist.count > 0:
                playlist.name = self._GetUniquePlaylistName(os.path.basename(folder))
                playlist.reset()
                self.AddToPlaylists(playlist)
            self.AppendToOutput('Playlist generated.')
            self.AppendToOutput(playlist.get_status_string())
        else:
            self.AppendToOutput(''.join(['Cannot find folder ', folder]))

    def do_loadlist(self, filename=''):
        '''
        LOADLIST
        Loads a file playlist
        -----------
        Syntax: loadlist [playlist file]
        '''
        #TODO: check for duplicate playlists, ask the user for a unique name
        #if self.playlist_name in self.playlists:
        #activate playlist

        if filename == '':
            filename = self.GetStringFromConfig('playlist', 'loadlist', 'filename')

        #add hkp extension if necessary
        if not filename.endswith('.hkp'):
            filename = ''.join([filename, '.hkp'])
        #prefix with 'hookeDir' if just a filename or a relative path
        filename = lh.get_file_path(filename)
        if os.path.isfile(filename):
            #load playlist
            playlist_new = Playlist(filename)
            if playlist_new.count > 0:
                self.AppendToOutput('Playlist loaded.')
                self.AddToPlaylists(playlist_new)
                self.AppendToOutput(playlist_new.get_status_string())
            else:
                message = ''.join(['The file ', filename, ' does not contain any valid curve information.'])
                dialog = wx.MessageDialog(None, message, 'Info', wx.OK)
                dialog.ShowModal()
        else:
            message = ''.join(['File ', filename, ' not found.'])
            dialog = wx.MessageDialog(None, message, 'Info', wx.OK)
            dialog.ShowModal()

    def do_savelist(self, filename=''):
        '''
        SAVELIST
        Saves the current file playlist on disk.
        ------------
        Syntax: savelist [filename]
        '''

        if filename == '':
            filename = self.GetStringFromConfig('playlist', 'savelist', 'filename')

        #autocomplete filename if not specified
        if not filename.endswith('.hkp'):
            filename = filename.join(['.hkp'])

        playlist = self.GetActivePlaylist()
        try:
            playlist.save(filename)
            self.AppendToOutput('Playlist saved.')
        except:
            self.AppendToOutput('Playlist could not be saved.')


