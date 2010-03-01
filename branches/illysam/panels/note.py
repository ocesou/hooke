#!/usr/bin/env python

'''
note.py

Note panel for Hooke.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''
import wx

class Note(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS|wx.NO_BORDER, size=(160, 200))

        self.Editor = wx.TextCtrl(self, style=wx.TE_MULTILINE)

        self.UpdateButton = wx.Button(self, -1, 'Update note')

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.Editor, 1, wx.EXPAND)
        sizer.Add(self.UpdateButton, 0, wx.EXPAND)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)
