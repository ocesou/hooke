#!/usr/bin/env python

'''
results.py

Fitting results panel for Hooke.

Copyright 2009 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import sys
import wx
from wx.lib.mixins.listctrl import CheckListCtrlMixin

class CheckListCtrl(wx.ListCtrl, CheckListCtrlMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT)
        CheckListCtrlMixin.__init__(self)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

    def OnItemActivated(self, evt):
        self.ToggleItem(evt.m_itemIndex)


class Results(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.results_list = CheckListCtrl(self)
        sizer = wx.BoxSizer()
        sizer.Add(self.results_list, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.results_list)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected, self.results_list)

    def _GetWidthInPixels(self, text):
        #TODO:
        #Returns the width of a string in pixels
        #Unfortunately, it does not work terribly well (although it should).
        #Thus, we have to add a bit afterwards.
        #Annoys the heck out of me (illysam).
        font = self.results_list.GetFont()
        dc = wx.WindowDC(self.results_list)
        dc.SetFont(font)
        width, height = dc.GetTextExtent(text)
        return width

    def ClearResults(self):
        self.results_list.ClearAll()

    def DisplayResults(self, results):
        self.ClearResults()
        header = results.get_header_as_list()
        self.results_list.InsertColumn(0, 'Show')
        for index, column in enumerate(header):
            self.results_list.InsertColumn(index + 1, column, wx.LIST_FORMAT_RIGHT)

        for result in results.results:
            done = False
            for index, column in enumerate(results.columns):
                value_str = results.get_pretty_value(column, result.result[column])
                if not done:
                    index_col = self.results_list.InsertStringItem(sys.maxint, '')
                    done = True
                column_width = len(self.results_list.GetColumn(index + 1).GetText())
                value_str = value_str.center(column_width)
                self.results_list.SetStringItem(index_col, index + 1, value_str)

        for index, result in enumerate(results.results):
            if result.visible:
                #if we use 'CheckItem' then 'UpdatePlot' is called (ie repeated updates)
                self.results_list.SetItemImage(index, 1)
        for index in range(self.results_list.GetColumnCount()):
            column_text = self.results_list.GetColumn(index).GetText()
            column_width = self._GetWidthInPixels(column_text)
            self.results_list.SetColumnWidth(index, column_width + 15)

    def OnItemSelected(self, evt):
        pass

    def OnItemDeselected(self, evt):
        pass
