#!/usr/bin/env python

'''
commands.py

Commands and settings panel for Hooke.

Copyright 2009 by Dr. Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

from configobj import ConfigObj
import os.path
import wx

import lib.libhooke as lh

class Commands(wx.Panel):

    def __init__(self, parent):
        # Use the WANTS_CHARS style so the panel doesn't eat the Return key.
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS|wx.NO_BORDER, size=(160, 200))

        self.CommandsTree = wx.TreeCtrl(self, -1, wx.Point(0, 0), wx.Size(160, 250), wx.TR_DEFAULT_STYLE|wx.NO_BORDER|wx.TR_HIDE_ROOT)
        imglist = wx.ImageList(16, 16, True, 2)
        imglist.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, wx.Size(16, 16)))
        imglist.Add(wx.ArtProvider.GetBitmap(wx.ART_EXECUTABLE_FILE, wx.ART_OTHER, wx.Size(16, 16)))
        self.CommandsTree.AssignImageList(imglist)
        self.CommandsTree.AddRoot('Commands and Settings', 0)

        self.ExecuteButton = wx.Button(self, -1, 'Execute')

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.CommandsTree, 1, wx.EXPAND)
        sizer.Add(self.ExecuteButton, 0, wx.EXPAND)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def Initialize(self, plugins):
        selected = None
        tree_root = self.CommandsTree.GetRootItem()
        path = lh.get_file_path('hooke.ini', ['config'])
        config = ConfigObj()
        if os.path.isfile(path):
            config.filename = path
            config.reload()
            #get the selected command/plugin from the config file
            command_str = config['command']['command']
            module_str = config['command']['plugin']

            for plugin in plugins:
                filename = ''.join([plugin, '.ini'])
                path = lh.get_file_path(filename, ['plugins'])
                config = ConfigObj()
                if os.path.isfile(path):
                    config.filename = path
                    config.reload()
                    #append the ini file to the plugin
                    plugin_root = self.CommandsTree.AppendItem(tree_root, plugin, 0, data=wx.TreeItemData(config))
                else:
                    plugin_root = self.CommandsTree.AppendItem(tree_root, plugin, 0)
                #select the plugin according to the config file
                if plugin == module_str:
                    selected = plugin_root

                #add all commands to the tree
                for command in plugins[plugin]:
                    command_label = command.replace('do_', '')
                    #do not add the ini file to the command (we'll access the ini file of the plugin (ie parent) instead, see above)
                    item = self.CommandsTree.AppendItem(plugin_root, command_label, 1)
                    #select the command according to the config file
                    if plugin == module_str and command_label == command_str:
                        selected = item
                        #e = wx.MouseEvent()
                        #e.SetEventType(wx.EVT_LEFT_DOWN.typeId)
                        #e.SetEventObject(self.CommandsTree)

                        ##e.SetSelection(page)
                        #self.Parent.OnTreeCtrlCommandsLeftDown(e)
                        #wx.PostEvent(self, e)

                        #self.CommandsTree.SelectItem(item, True)

                self.CommandsTree.Expand(plugin_root)
            #make sure the selected command/plugin is visible in the tree
            if selected is not None:
                self.CommandsTree.SelectItem(selected, True)
                self.CommandsTree.EnsureVisible(selected)
