#!/usr/bin/env python

'''
perspectives.py

Perspectives panel for deletion.

Copyright 2010 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

from os import remove
import wx

import lib.libhooke as lh

class Perspectives(wx.Dialog):

    def __init__(self, parent, ID, title):
        wx.Dialog.__init__(self, parent, ID, title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        # contents
        sizer_vertical = wx.BoxSizer(wx.VERTICAL)

        message_str = "\nPlease check the perspectives\n\nyou want to delete and click 'Delete'.\n"
        text = wx.StaticText(self, -1, message_str, wx.DefaultPosition, style=wx.ALIGN_CENTRE)
        sizer_vertical.Add(text, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        perspectives_list = [item[0] for item in self.Parent._perspectives.items() if item[0] != 'Default']
        perspectives_list.sort()
        listbox = wx.CheckListBox(self, -1, wx.DefaultPosition, wx.Size(175, 200), perspectives_list)
        self.Bind(wx.EVT_CHECKLISTBOX, self.EvtCheckListBox, listbox)
        listbox.SetSelection(0)
        sizer_vertical.Add(listbox, 1, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.listbox = listbox

        horizontal_line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        sizer_vertical.Add(horizontal_line, 0, wx.GROW, 5)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)

        button_delete = wx.Button(self, wx.ID_DELETE)
        self.Bind(wx.EVT_BUTTON, self.OnButtonDelete, button_delete)
        button_delete.SetDefault()
        sizer_buttons.Add(button_delete, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        button_close = wx.Button(self, wx.ID_CLOSE)
        self.Bind(wx.EVT_BUTTON, self.OnButtonClose, button_close)
        sizer_buttons.Add(button_close, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        sizer_vertical.Add(sizer_buttons, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)

        self.SetSizer(sizer_vertical)
        sizer_vertical.Fit(self)

    def EvtCheckListBox(self, event):
        index = event.GetSelection()
        self.listbox.SetSelection(index)    # so that (un)checking also selects (moves the highlight)

    def OnButtonClose(self, event):
        self.EndModal(wx.ID_CLOSE)

    def OnButtonDelete(self, event):
        items = self.listbox.GetItems()
        selected_perspective = self.Parent.config['perspectives']['active']
        for index in reversed(self.listbox.GetChecked()):
            self.listbox.Delete(index)
            if items[index] == selected_perspective:
                self.Parent.config['perspectives']['active'] = 'Default'

            filename = lh.get_file_path(items[index] + '.txt', ['perspectives'])
            remove(filename)
