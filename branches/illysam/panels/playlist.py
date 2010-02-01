#!/usr/bin/env python

'''
playlist.py

Playlist panel for Hooke.

Copyright 2009 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import wx

class Playlists(wx.Panel):

    def __init__(self, parent):
        # Use the WANTS_CHARS style so the panel doesn't eat the Return key.
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS|wx.NO_BORDER, size=(160, 200))

        self.PlaylistsTree = wx.TreeCtrl(self, -1, wx.Point(0, 0), wx.Size(160, 250), wx.TR_DEFAULT_STYLE | wx.NO_BORDER | wx.TR_HIDE_ROOT)
        imglist = wx.ImageList(16, 16, True, 2)
        imglist.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, wx.Size(16, 16)))
        imglist.Add(wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16, 16)))
        self.PlaylistsTree.AssignImageList(imglist)
        self.PlaylistsTree.AddRoot('Playlists', 0)
        self.PlaylistsTree.Bind(wx.EVT_RIGHT_DOWN , self.OnContextMenu)

        self.Playlists = {}

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.PlaylistsTree, 1, wx.EXPAND)
        self.SetSizer(sizer)
        sizer.Fit(self)

    def OnContextMenu(self, event):
        hit_item, hit_flags = self.PlaylistsTree.HitTest(event.GetPosition())
        if (hit_flags & wx.TREE_HITTEST_ONITEM) != 0:
            self.PlaylistsTree.SelectItem(hit_item)
            # only do this part the first time so the events are only bound once
            # Yet another alternate way to do IDs. Some prefer them up top to
            # avoid clutter, some prefer them close to the object of interest
            # for clarity.
            if not hasattr(self, 'ID_popupAdd'):
                #self.ID_popupAdd = wx.NewId()
                self.ID_popupDelete = wx.NewId()
                #self.Bind(wx.EVT_MENU, self.OnPopupAdd, id=self.ID_popupAdd)
                self.Bind(wx.EVT_MENU, self.OnPopupDelete, id=self.ID_popupDelete)
            # make a menu
            menu = wx.Menu()
            #items = [['Add', self.ID_popupAdd] , ['Delete', self.ID_popupDelete]]
            items = [['Delete', self.ID_popupDelete]]
            for item in items:
                menu.Append(item[1], item[0])
            # Popup the menu.  If an item is selected then its handler
            # will be called before PopupMenu returns.
            self.PopupMenu(menu)
            menu.Destroy()

    def OnPopupAdd(self, event):
        pass

    def OnPopupDelete(self, event):
        item = self.PlaylistsTree.GetSelection()
        playlist = self.Parent.GetActivePlaylist()
        if self.PlaylistsTree.ItemHasChildren(item):
            playlist_name = self.PlaylistsTree.GetItemText(item)
            notebook = self.Parent.plotNotebook
            index = self.Parent._GetPlaylistTab(playlist_name)
            notebook.SetSelection(index)
            notebook.DeletePage(notebook.GetSelection())
            self.Parent.DeleteFromPlaylists(playlist_name)
        else:
            if playlist is not None:
                if playlist.count == 1:
                    notebook = self.Parent.plotNotebook
                    index = self.Parent._GetPlaylistTab(playlist.name)
                    notebook.SetSelection(index)
                    notebook.DeletePage(notebook.GetSelection())
                    self.Parent.DeleteFromPlaylists(playlist.name)
                else:
                    file_name = self.PlaylistsTree.GetItemText(item)
                    playlist.delete_file(file_name)
                    self.PlaylistsTree.Delete(item)
                    self.Parent.UpdatePlaylistsTreeSelection()
