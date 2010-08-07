# Copyright (C) 2008-2010 Fabrizio Benedetti
#                         Massimo Sandal <devicerandom@gmail.com>
#                         Rolf Schmidt <rschmidt@alcor.concordia.ca>
#                         W. Trevor King <wking@drexel.edu>
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

"""Defines :class:`GUI` providing a wxWidgets interface to Hooke.

"""

WX_GOOD=['2.8']

import wxversion
wxversion.select(WX_GOOD)

import copy
import logging
import os
import os.path
import platform
import shutil
import time

import wx.html
import wx.aui as aui
import wx.lib.evtmgr as evtmgr
# wxPropertyGrid is included in wxPython >= 2.9.1, see
#   http://wxpropgrid.sourceforge.net/cgi-bin/index?page=download
# until then, we'll avoid it because of the *nix build problems.
#import wx.propgrid as wxpg

from ...command import CommandExit, Exit, Success, Failure, Command, Argument
from ...config import Setting
from ...interaction import Request, BooleanRequest, ReloadUserInterfaceConfig
from ...ui import UserInterface, CommandMessage
from .dialog.selection import Selection as SelectionDialog
from .dialog.save_file import select_save_file
from . import menu as menu
from . import navbar as navbar
from . import panel as panel
from .panel.propertyeditor import props_from_argument, props_from_setting
from . import statusbar as statusbar


class HookeFrame (wx.Frame):
    """The main Hooke-interface window.    
    """
    def __init__(self, gui, commands, inqueue, outqueue, *args, **kwargs):
        super(HookeFrame, self).__init__(*args, **kwargs)
        self.log = logging.getLogger('hooke')
        self.gui = gui
        self.commands = commands
        self.inqueue = inqueue
        self.outqueue = outqueue
        self._perspectives = {}  # {name: perspective_str}
        self._c = {}

        self.SetIcon(wx.Icon(self.gui.config['icon image'], wx.BITMAP_TYPE_ICO))

        # setup frame manager
        self._c['manager'] = aui.AuiManager()
        self._c['manager'].SetManagedWindow(self)

        # set the gradient and drag styles
        self._c['manager'].GetArtProvider().SetMetric(
            aui.AUI_DOCKART_GRADIENT_TYPE, aui.AUI_GRADIENT_NONE)
        self._c['manager'].SetFlags(
            self._c['manager'].GetFlags() ^ aui.AUI_MGR_TRANSPARENT_DRAG)

        # Min size for the frame itself isn't completely done.  See
        # the end of FrameManager::Update() for the test code. For
        # now, just hard code a frame minimum size.
        #self.SetMinSize(wx.Size(500, 500))

        self._setup_panels()
        self._setup_toolbars()
        self._c['manager'].Update()  # commit pending changes

        # Create the menubar after the panes so that the default
        # perspective is created with all panes open
        panels = [p for p in self._c.values() if isinstance(p, panel.Panel)]
        self._c['menu bar'] = menu.HookeMenuBar(
            parent=self,
            panels=panels,
            callbacks={
                'close': self._on_close,
                'about': self._on_about,
                'view_panel': self._on_panel_visibility,
                'save_perspective': self._on_save_perspective,
                'delete_perspective': self._on_delete_perspective,
                'select_perspective': self._on_select_perspective,
                })
        self.SetMenuBar(self._c['menu bar'])

        self._c['status bar'] = statusbar.StatusBar(
            parent=self,
            style=wx.ST_SIZEGRIP)
        self.SetStatusBar(self._c['status bar'])

        self._setup_perspectives()
        self._bind_events()

        self.execute_command(
                command=self._command_by_name('load playlist'),
                args={'input':'test/data/test'},#vclamp_picoforce/playlist'},
                )
        self.execute_command(
                command=self._command_by_name('load playlist'),
                args={'input':'test/data/vclamp_picoforce/playlist'},
                )
        self.execute_command(
                command=self._command_by_name('polymer fit'),
                args={'block':1, 'bounds':[918, 1103]},
                )
        return # TODO: cleanup
        self.playlists = self._c['playlist'].Playlists
        self._displayed_plot = None
        #load default list, if possible
        self.do_loadlist(self.GetStringFromConfig('core', 'preferences', 'playlists'))


    # GUI maintenance

    def _setup_panels(self):
        client_size = self.GetClientSize()
        for p,style in [
#            ('folders', wx.GenericDirCtrl(
#                    parent=self,
#                    dir=self.gui.config['folders-workdir'],
#                    size=(200, 250),
#                    style=wx.DIRCTRL_SHOW_FILTERS,
#                    filter=self.gui.config['folders-filters'],
#                    defaultFilter=self.gui.config['folders-filter-index']), 'left'),
            (panel.PANELS['playlist'](
                    callbacks={
                        'delete_playlist':self._on_user_delete_playlist,
                        '_delete_playlist':self._on_delete_playlist,
                        'delete_curve':self._on_user_delete_curve,
                        '_delete_curve':self._on_delete_curve,
                        '_on_set_selected_playlist':self._on_set_selected_playlist,
                        '_on_set_selected_curve':self._on_set_selected_curve,
                        },
                    parent=self,
                    style=wx.WANTS_CHARS|wx.NO_BORDER,
                    # WANTS_CHARS so the panel doesn't eat the Return key.
#                    size=(160, 200),
                    ), 'left'),
            (panel.PANELS['note'](
                    callbacks = {
                        '_on_update':self._on_update_note,
                        },
                    parent=self,
                    style=wx.WANTS_CHARS|wx.NO_BORDER,
#                    size=(160, 200),
                    ), 'left'),
#            ('notebook', Notebook(
#                    parent=self,
#                    pos=wx.Point(client_size.x, client_size.y),
#                    size=wx.Size(430, 200),
#                    style=aui.AUI_NB_DEFAULT_STYLE
#                    | aui.AUI_NB_TAB_EXTERNAL_MOVE | wx.NO_BORDER), 'center'),
            (panel.PANELS['commands'](
                    commands=self.commands,
                    selected=self.gui.config['selected command'],
                    callbacks={
                        'execute': self.execute_command,
                        'select_plugin': self.select_plugin,
                        'select_command': self.select_command,
#                        'selection_changed': self.panelProperties.select(self, method, command),  #SelectedTreeItem = selected_item,
                        },
                    parent=self,
                    style=wx.WANTS_CHARS|wx.NO_BORDER,
                    # WANTS_CHARS so the panel doesn't eat the Return key.
#                    size=(160, 200),
                    ), 'right'),
            (panel.PANELS['propertyeditor'](
                    callbacks={},
                    parent=self,
                    style=wx.WANTS_CHARS,
                    # WANTS_CHARS so the panel doesn't eat the Return key.
                    ), 'center'),
#            ('assistant', wx.TextCtrl(
#                    parent=self,
#                    pos=wx.Point(0, 0),
#                    size=wx.Size(150, 90),
#                    style=wx.NO_BORDER|wx.TE_MULTILINE), 'right'),
            (panel.PANELS['plot'](
                    callbacks={
                        '_set_status_text': self._on_plot_status_text,
                        },
                    parent=self,
                    style=wx.WANTS_CHARS|wx.NO_BORDER,
                    # WANTS_CHARS so the panel doesn't eat the Return key.
#                    size=(160, 200),
                    ), 'center'),
            (panel.PANELS['output'](
                    parent=self,
                    pos=wx.Point(0, 0),
                    size=wx.Size(150, 90),
                    style=wx.TE_READONLY|wx.NO_BORDER|wx.TE_MULTILINE),
             'bottom'),
#            ('results', panel.results.Results(self), 'bottom'),
            ]:
            self._add_panel(p, style)
        #self._c['assistant'].SetEditable(False)

    def _add_panel(self, panel, style):
        self._c[panel.name] = panel
        m_name = panel.managed_name
        info = aui.AuiPaneInfo().Name(m_name).Caption(m_name)
        info.PaneBorder(False).CloseButton(True).MaximizeButton(False)
        if style == 'top':
            info.Top()
        elif style == 'center':
            info.CenterPane()
        elif style == 'left':
            info.Left()
        elif style == 'right':
            info.Right()
        else:
            assert style == 'bottom', style
            info.Bottom()
        self._c['manager'].AddPane(panel, info)

    def _setup_toolbars(self):
        self._c['navigation bar'] = navbar.NavBar(
            callbacks={
                'next': self._next_curve,
                'previous': self._previous_curve,
                },
            parent=self,
            style=wx.TB_FLAT | wx.TB_NODIVIDER)
        self._c['manager'].AddPane(
            self._c['navigation bar'],
            aui.AuiPaneInfo().Name('Navigation').Caption('Navigation'
                ).ToolbarPane().Top().Layer(1).Row(1).LeftDockable(False
                ).RightDockable(False))

    def _bind_events(self):
        # TODO: figure out if we can use the eventManager for menu
        # ranges and events of 'self' without raising an assertion
        # fail error.
        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)
        self.Bind(wx.EVT_SIZE, self._on_size)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(aui.EVT_AUI_PANE_CLOSE, self.OnPaneClose)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self._on_notebook_page_close)

        return # TODO: cleanup
        treeCtrl = self._c['folders'].GetTreeCtrl()
        treeCtrl.Bind(wx.EVT_LEFT_DCLICK, self._on_dir_ctrl_left_double_click)
        
        #property editor
        self.panelProperties.pg.Bind(wxpg.EVT_PG_CHANGED, self.OnPropGridChanged)
        #results panel
        self.panelResults.results_list.OnCheckItem = self.OnResultsCheck

    def _on_about(self, *args):
        dialog = wx.MessageDialog(
            parent=self,
            message=self.gui._splash_text(extra_info={
                    'get-details':'click "Help -> License"'},
                                          wrap=False),
            caption='About Hooke',
            style=wx.OK|wx.ICON_INFORMATION)
        dialog.ShowModal()
        dialog.Destroy()

    def _on_close(self, *args):
        self.log.info('closing GUI framework')
        # apply changes
        self.gui.config['main height'] = str(self.GetSize().GetHeight())
        self.gui.config['main left'] = str(self.GetPosition()[0])
        self.gui.config['main top'] = str(self.GetPosition()[1])
        self.gui.config['main width'] = str(self.GetSize().GetWidth())
        # push changes back to Hooke.config?
        self._c['manager'].UnInit()
        del self._c['manager']
        self.Destroy()



    # Panel utility functions

    def _file_name(self, name):
        """Cleanup names according to configured preferences.
        """
        if self.gui.config['hide extensions'] == True:
            name,ext = os.path.splitext(name)
        return name



    # Command handling

    def _command_by_name(self, name):
        cs = [c for c in self.commands if c.name == name]
        if len(cs) == 0:
            raise KeyError(name)
        elif len(cs) > 1:
            raise Exception('Multiple commands named "%s"' % name)
        return cs[0]

    def execute_command(self, _class=None, method=None,
                        command=None, args=None):
        if args == None:
            args = {}
        if ('property editor' in self._c
            and self.gui.config['selected command'] == command):
            for name,value in self._c['property editor'].get_values().items():
                arg = self._c['property editor']._argument_from_label.get(
                    name, None)
                if arg == None:
                    continue
                elif arg.count == 1:
                    args[arg.name] = value
                    continue
                # deal with counted arguments
                if arg.name not in args:
                    args[arg.name] = {}
                index = int(name[len(arg.name):])
                args[arg.name][index] = value
            for arg in command.arguments:
                if arg.count != 1 and arg.name in args:
                    keys = sorted(args[arg.name].keys())
                    assert keys == range(arg.count), keys
                    args[arg.name] = [args[arg.name][i]
                                      for i in range(arg.count)]
        self.log.debug('executing %s with %s' % (command.name, args))
        self.inqueue.put(CommandMessage(command, args))
        results = []
        while True:
            msg = self.outqueue.get()
            results.append(msg)
            if isinstance(msg, Exit):
                self._on_close()
                break
            elif isinstance(msg, CommandExit):
                # TODO: display command complete
                break
            elif isinstance(msg, ReloadUserInterfaceConfig):
                self.gui.reload_config(msg.config)
                continue
            elif isinstance(msg, Request):
                h = handler.HANDLERS[msg.type]
                h.run(self, msg)  # TODO: pause for response?
                continue
        pp = getattr(
            self, '_postprocess_%s' % command.name.replace(' ', '_'),
            self._postprocess_text)
        pp(command=command, args=args, results=results)
        return results

    def _handle_request(self, msg):
        """Repeatedly try to get a response to `msg`.
        """
        if prompt == None:
            raise NotImplementedError('_%s_request_prompt' % msg.type)
        prompt_string = prompt(msg)
        parser = getattr(self, '_%s_request_parser' % msg.type, None)
        if parser == None:
            raise NotImplementedError('_%s_request_parser' % msg.type)
        error = None
        while True:
            if error != None:
                self.cmd.stdout.write(''.join([
                        error.__class__.__name__, ': ', str(error), '\n']))
            self.cmd.stdout.write(prompt_string)
            value = parser(msg, self.cmd.stdin.readline())
            try:
                response = msg.response(value)
                break
            except ValueError, error:
                continue
        self.inqueue.put(response)



    # Command-specific postprocessing

    def _postprocess_text(self, command, args={}, results=[]):
        """Print the string representation of the results to the Results window.

        This is similar to :class:`~hooke.ui.commandline.DoCommand`'s
        approach, except that :class:`~hooke.ui.commandline.DoCommand`
        doesn't print some internally handled messages
        (e.g. :class:`~hooke.interaction.ReloadUserInterfaceConfig`).
        """
        for result in results:
            if isinstance(result, CommandExit):
                self._c['output'].write(result.__class__.__name__+'\n')
            self._c['output'].write(str(result).rstrip()+'\n')

    def _postprocess_load_playlist(self, command, args={}, results=None):
        """Update `self` to show the playlist.
        """
        if not isinstance(results[-1], Success):
            self._postprocess_text(command, results=results)
            return
        assert len(results) == 2, results
        playlist = results[0]
        self._c['playlist']._c['tree'].add_playlist(playlist)

    def _postprocess_get_playlist(self, command, args={}, results=[]):
        if not isinstance(results[-1], Success):
            self._postprocess_text(command, results=results)
            return
        assert len(results) == 2, results
        playlist = results[0]
        self._c['playlist']._c['tree'].update_playlist(playlist)

    def _postprocess_get_curve(self, command, args={}, results=[]):
        """Update `self` to show the curve.
        """
        if not isinstance(results[-1], Success):
            self._postprocess_text(command, results=results)
            return
        assert len(results) == 2, results
        curve = results[0]
        if args.get('curve', None) == None:
            # the command defaults to the current curve of the current playlist
            results = self.execute_command(
                command=self._command_by_name('get playlist'))
            playlist = results[0]
        else:
            raise NotImplementedError()
        if 'note' in self._c:
            self._c['note'].set_text(curve.info['note'])
        if 'playlist' in self._c:
            self._c['playlist']._c['tree'].set_selected_curve(
                playlist, curve)
        if 'plot' in self._c:
            self._c['plot'].set_curve(curve, config=self.gui.config)

    def _postprocess_next_curve(self, command, args={}, results=[]):
        """No-op.  Only call 'next curve' via `self._next_curve()`.
        """
        pass

    def _postprocess_previous_curve(self, command, args={}, results=[]):
        """No-op.  Only call 'previous curve' via `self._previous_curve()`.
        """
        pass

    def _postprocess_zero_block_surface_contact_point(
        self, command, args={}, results=[]):
        """Update the curve, since the available columns may have changed.
        """
        if isinstance(results[-1], Success):
            self.execute_command(
                command=self._command_by_name('get curve'))
 
    def _postprocess_add_block_force_array(
        self, command, args={}, results=[]):
        """Update the curve, since the available columns may have changed.
        """
        if isinstance(results[-1], Success):
            self.execute_command(
                command=self._command_by_name('get curve'))



    # TODO: cruft

    def _GetActiveFileIndex(self):
        lib.playlist.Playlist = self.GetActivePlaylist()
        #get the selected item from the tree
        selected_item = self._c['playlist']._c['tree'].GetSelection()
        #test if a playlist or a curve was double-clicked
        if self._c['playlist']._c['tree'].ItemHasChildren(selected_item):
            return -1
        else:
            count = 0
            selected_item = self._c['playlist']._c['tree'].GetPrevSibling(selected_item)
            while selected_item.IsOk():
                count += 1
                selected_item = self._c['playlist']._c['tree'].GetPrevSibling(selected_item)
            return count

    def _GetPlaylistTab(self, name):
        for index, page in enumerate(self._c['notebook']._tabs._pages):
            if page.caption == name:
                return index
        return -1

    def select_plugin(self, _class=None, method=None, plugin=None):
        pass

    def AddPlaylistFromFiles(self, files=[], name='Untitled'):
        if files:
            playlist = lib.playlist.Playlist(self, self.drivers)
            for item in files:
                playlist.add_curve(item)
        if playlist.count > 0:
            playlist.name = self._GetUniquePlaylistName(name)
            playlist.reset()
            self.AddTayliss(playlist)

    def AppliesPlotmanipulator(self, name):
        '''
        Returns True if the plotmanipulator 'name' is applied, False otherwise
        name does not contain 'plotmanip_', just the name of the plotmanipulator (e.g. 'flatten')
        '''
        return self.GetBoolFromConfig('core', 'plotmanipulators', name)

    def ApplyPlotmanipulators(self, plot, plot_file):
        '''
        Apply all active plotmanipulators.
        '''
        if plot is not None and plot_file is not None:
            manipulated_plot = copy.deepcopy(plot)
            for plotmanipulator in self.plotmanipulators:
                if self.GetBoolFromConfig('core', 'plotmanipulators', plotmanipulator.name):
                    manipulated_plot = plotmanipulator.method(manipulated_plot, plot_file)
            return manipulated_plot

    def GetActiveFigure(self):
        playlist_name = self.GetActivePlaylistName()
        figure = self.playlists[playlist_name].figure
        if figure is not None:
            return figure
        return None

    def GetActiveFile(self):
        playlist = self.GetActivePlaylist()
        if playlist is not None:
            return playlist.get_active_file()
        return None

    def GetActivePlot(self):
        playlist = self.GetActivePlaylist()
        if playlist is not None:
            return playlist.get_active_file().plot
        return None

    def GetDisplayedPlot(self):
        plot = copy.deepcopy(self.displayed_plot)
        #plot.curves = []
        #plot.curves = copy.deepcopy(plot.curves)
        return plot

    def GetDisplayedPlotCorrected(self):
        plot = copy.deepcopy(self.displayed_plot)
        plot.curves = []
        plot.curves = copy.deepcopy(plot.corrected_curves)
        return plot

    def GetDisplayedPlotRaw(self):
        plot = copy.deepcopy(self.displayed_plot)
        plot.curves = []
        plot.curves = copy.deepcopy(plot.raw_curves)
        return plot

    def GetDockArt(self):
        return self._c['manager'].GetArtProvider()

    def GetPlotmanipulator(self, name):
        '''
        Returns a plot manipulator function from its name
        '''
        for plotmanipulator in self.plotmanipulators:
            if plotmanipulator.name == name:
                return plotmanipulator
        return None

    def HasPlotmanipulator(self, name):
        '''
        returns True if the plotmanipulator 'name' is loaded, False otherwise
        '''
        for plotmanipulator in self.plotmanipulators:
            if plotmanipulator.command == name:
                return True
        return False


    def _on_dir_ctrl_left_double_click(self, event):
        file_path = self.panelFolders.GetPath()
        if os.path.isfile(file_path):
            if file_path.endswith('.hkp'):
                self.do_loadlist(file_path)
        event.Skip()

    def _on_erase_background(self, event):
        event.Skip()

    def _on_notebook_page_close(self, event):
        ctrl = event.GetEventObject()
        playlist_name = ctrl.GetPageText(ctrl._curpage)
        self.DeleteFromPlaylists(playlist_name)

    def OnPaneClose(self, event):
        event.Skip()

    def OnPropGridChanged (self, event):
        prop = event.GetProperty()
        if prop:
            item_section = self.panelProperties.SelectedTreeItem
            item_plugin = self._c['commands']._c['tree'].GetItemParent(item_section)
            plugin = self._c['commands']._c['tree'].GetItemText(item_plugin)
            config = self.gui.config[plugin]
            property_section = self._c['commands']._c['tree'].GetItemText(item_section)
            property_key = prop.GetName()
            property_value = prop.GetDisplayedString()

            config[property_section][property_key]['value'] = property_value

    def OnResultsCheck(self, index, flag):
        results = self.GetActivePlot().results
        if results.has_key(self.results_str):
            results[self.results_str].results[index].visible = flag
            results[self.results_str].update()
            self.UpdatePlot()


    def _on_size(self, event):
        event.Skip()

    def UpdatePlaylistsTreeSelection(self):
        playlist = self.GetActivePlaylist()
        if playlist is not None:
            if playlist.index >= 0:
                self._c['status bar'].set_playlist(playlist)
                self.UpdateNote()
                self.UpdatePlot()

    def _on_curve_select(self, playlist, curve):
        #create the plot tab and add playlist to the dictionary
        plotPanel = panel.plot.PlotPanel(self, ID_FirstPlot + len(self.playlists))
        notebook_tab = self._c['notebook'].AddPage(plotPanel, playlist.name, True)
        #tab_index = self._c['notebook'].GetSelection()
        playlist.figure = plotPanel.get_figure()
        self.playlists[playlist.name] = playlist
        #self.playlists[playlist.name] = [playlist, figure]
        self._c['status bar'].set_playlist(playlist)
        self.UpdateNote()
        self.UpdatePlot()


    def _on_playlist_left_doubleclick(self):
        index = self._c['notebook'].GetSelection()
        current_playlist = self._c['notebook'].GetPageText(index)
        if current_playlist != playlist_name:
            index = self._GetPlaylistTab(playlist_name)
            self._c['notebook'].SetSelection(index)
        self._c['status bar'].set_playlist(playlist)
        self.UpdateNote()
        self.UpdatePlot()

    def _on_playlist_delete(self, playlist):
        notebook = self.Parent.plotNotebook
        index = self.Parent._GetPlaylistTab(playlist.name)
        notebook.SetSelection(index)
        notebook.DeletePage(notebook.GetSelection())
        self.Parent.DeleteFromPlaylists(playlist_name)



    # Command panel interface

    def select_command(self, _class, method, command):
        #self.select_plugin(plugin=command.plugin)
        if 'assistant' in self._c:
            self._c['assitant'].ChangeValue(command.help)
        self._c['property editor'].clear()
        self._c['property editor']._argument_from_label = {}
        for argument in command.arguments:
            if argument.name == 'help':
                continue

            results = self.execute_command(
                command=self._command_by_name('playlists'))
            if not isinstance(results[-1], Success):
                self._postprocess_text(command, results=results)
                playlists = []
            else:
                playlists = results[0]

            results = self.execute_command(
                command=self._command_by_name('playlist curves'))
            if not isinstance(results[-1], Success):
                self._postprocess_text(command, results=results)
                curves = []
            else:
                curves = results[0]

            ret = props_from_argument(
                argument, curves=curves, playlists=playlists)
            if ret == None:
                continue  # property intentionally not handled (yet)
            for label,p in ret:
                self._c['property editor'].append_property(p)
                self._c['property editor']._argument_from_label[label] = (
                    argument)

        self.gui.config['selected command'] = command  # TODO: push to engine



    # Note panel interface

    def _on_update_note(self, _class, method, text):
        """Sets the note for the active curve.
        """
        self.execute_command(
            command=self._command_by_name('set note'),
            args={'note':text})



    # Playlist panel interface

    def _on_user_delete_playlist(self, _class, method, playlist):
        pass

    def _on_delete_playlist(self, _class, method, playlist):
        if hasattr(playlist, 'path') and playlist.path != None:
            os.remove(playlist.path)

    def _on_user_delete_curve(self, _class, method, playlist, curve):
        pass

    def _on_delete_curve(self, _class, method, playlist, curve):
        os.remove(curve.path)

    def _on_set_selected_playlist(self, _class, method, playlist):
        """Call the `jump to playlist` command.
        """
        results = self.execute_command(
            command=self._command_by_name('playlists'))
        if not isinstance(results[-1], Success):
            return
        assert len(results) == 2, results
        playlists = results[0]
        matching = [p for p in playlists if p.name == playlist.name]
        assert len(matching) == 1, matching
        index = playlists.index(matching[0])
        results = self.execute_command(
            command=self._command_by_name('jump to playlist'),
            args={'index':index})

    def _on_set_selected_curve(self, _class, method, playlist, curve):
        """Call the `jump to curve` command.
        """
        self._on_set_selected_playlist(_class, method, playlist)
        index = playlist.index(curve)
        results = self.execute_command(
            command=self._command_by_name('jump to curve'),
            args={'index':index})
        if not isinstance(results[-1], Success):
            return
        #results = self.execute_command(
        #    command=self._command_by_name('get playlist'))
        #if not isinstance(results[-1], Success):
        #    return
        self.execute_command(
            command=self._command_by_name('get curve'))



    # Plot panel interface

    def _on_plot_status_text(self, _class, method, text):
        if 'status bar' in self._c:
            self._c['status bar'].set_plot_text(text)



    # Navbar interface

    def _next_curve(self, *args):
        """Call the `next curve` command.
        """
        results = self.execute_command(
            command=self._command_by_name('next curve'))
        if isinstance(results[-1], Success):
            self.execute_command(
                command=self._command_by_name('get curve'))

    def _previous_curve(self, *args):
        """Call the `previous curve` command.
        """
        results = self.execute_command(
            command=self._command_by_name('previous curve'))
        if isinstance(results[-1], Success):
            self.execute_command(
                command=self._command_by_name('get curve'))



    # Panel display handling

    def _on_panel_visibility(self, _class, method, panel_name, visible):
        pane = self._c['manager'].GetPane(panel_name)
        pane.Show(visible)
        #if we don't do the following, the Folders pane does not resize properly on hide/show
        if pane.caption == 'Folders' and pane.IsShown() and pane.IsDocked():
            #folders_size = pane.GetSize()
            self.panelFolders.Fit()
        self._c['manager'].Update()

    def _setup_perspectives(self):
        """Add perspectives to menubar and _perspectives.
        """
        self._perspectives = {
            'Default': self._c['manager'].SavePerspective(),
            }
        path = self.gui.config['perspective path']
        if os.path.isdir(path):
            files = sorted(os.listdir(path))
            for fname in files:
                name, extension = os.path.splitext(fname)
                if extension != self.gui.config['perspective extension']:
                    continue
                fpath = os.path.join(path, fname)
                if not os.path.isfile(fpath):
                    continue
                perspective = None
                with open(fpath, 'rU') as f:
                    perspective = f.readline()
                if perspective:
                    self._perspectives[name] = perspective

        selected_perspective = self.gui.config['active perspective']
        if not self._perspectives.has_key(selected_perspective):
            self.gui.config['active perspective'] = 'Default'  # TODO: push to engine's Hooke

        self._restore_perspective(selected_perspective, force=True)
        self._update_perspective_menu()

    def _update_perspective_menu(self):
        self._c['menu bar']._c['perspective'].update(
            sorted(self._perspectives.keys()),
            self.gui.config['active perspective'])

    def _save_perspective(self, perspective, perspective_dir, name,
                          extension=None):
        path = os.path.join(perspective_dir, name)
        if extension != None:
            path += extension
        if not os.path.isdir(perspective_dir):
            os.makedirs(perspective_dir)
        with open(path, 'w') as f:
            f.write(perspective)
        self._perspectives[name] = perspective
        self._restore_perspective(name)
        self._update_perspective_menu()

    def _delete_perspectives(self, perspective_dir, names,
                             extension=None):
        self.log.debug('remove perspectives %s from %s'
                       % (names, perspective_dir))
        for name in names:
            path = os.path.join(perspective_dir, name)
            if extension != None:
                path += extension
            os.remove(path)
            del(self._perspectives[name])
        self._update_perspective_menu()
        if self.gui.config['active perspective'] in names:
            self._restore_perspective('Default')
        # TODO: does this bug still apply?
        # Unfortunately, there is a bug in wxWidgets for win32 (Ticket #3258
        #   http://trac.wxwidgets.org/ticket/3258 
        # ) that makes the radio item indicator in the menu disappear.
        # The code should be fine once this issue is fixed.

    def _restore_perspective(self, name, force=False):
        if name != self.gui.config['active perspective'] or force == True:
            self.log.debug('restore perspective %s' % name)
            self.gui.config['active perspective'] = name  # TODO: push to engine's Hooke
            self._c['manager'].LoadPerspective(self._perspectives[name])
            self._c['manager'].Update()
            for pane in self._c['manager'].GetAllPanes():
                view = self._c['menu bar']._c['view']
                if pane.name in view._c.keys():
                    view._c[pane.name].Check(pane.window.IsShown())

    def _on_save_perspective(self, *args):
        perspective = self._c['manager'].SavePerspective()
        name = self.gui.config['active perspective']
        if name == 'Default':
            name = 'New perspective'
        name = select_save_file(
            directory=self.gui.config['perspective path'],
            name=name,
            extension=self.gui.config['perspective extension'],
            parent=self,
            message='Enter a name for the new perspective:',
            caption='Save perspective')
        if name == None:
            return
        self._save_perspective(
            perspective, self.gui.config['perspective path'], name=name,
            extension=self.gui.config['perspective extension'])

    def _on_delete_perspective(self, *args, **kwargs):
        options = sorted([p for p in self._perspectives.keys()
                          if p != 'Default'])
        dialog = SelectionDialog(
            options=options,
            message="\nPlease check the perspectives\n\nyou want to delete and click 'Delete'.\n",
            button_id=wx.ID_DELETE,
            selection_style='multiple',
            parent=self,
            title='Delete perspective(s)',
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dialog.CenterOnScreen()
        dialog.ShowModal()
        if dialog.canceled == True:
            return
        names = [options[i] for i in dialog.selected]
        dialog.Destroy()
        self._delete_perspectives(
            self.gui.config['perspective path'], names=names,
            extension=self.gui.config['perspective extension'])

    def _on_select_perspective(self, _class, method, name):
        self._restore_perspective(name)



class HookeApp (wx.App):
    """A :class:`wx.App` wrapper around :class:`HookeFrame`.

    Tosses up a splash screen and then loads :class:`HookeFrame` in
    its own window.
    """
    def __init__(self, gui, commands, inqueue, outqueue, *args, **kwargs):
        self.gui = gui
        self.commands = commands
        self.inqueue = inqueue
        self.outqueue = outqueue
        super(HookeApp, self).__init__(*args, **kwargs)

    def OnInit(self):
        self.SetAppName('Hooke')
        self.SetVendorName('')
        self._setup_splash_screen()

        height = self.gui.config['main height']
        width = self.gui.config['main width']
        top = self.gui.config['main top']
        left = self.gui.config['main left']

        # Sometimes, the ini file gets confused and sets 'left' and
        # 'top' to large negative numbers.  Here we catch and fix
        # this.  Keep small negative numbers, the user might want
        # those.
        if left < -width:
            left = 0
        if top < -height:
            top = 0

        self._c = {
            'frame': HookeFrame(
                self.gui, self.commands, self.inqueue, self.outqueue,
                parent=None, title='Hooke',
                pos=(left, top), size=(width, height),
                style=wx.DEFAULT_FRAME_STYLE|wx.SUNKEN_BORDER|wx.CLIP_CHILDREN),
            }
        self._c['frame'].Show(True)
        self.SetTopWindow(self._c['frame'])
        return True

    def _setup_splash_screen(self):
        if self.gui.config['show splash screen'] == True:
            path = self.gui.config['splash screen image']
            if os.path.isfile(path):
                duration = self.gui.config['splash screen duration']
                wx.SplashScreen(
                    bitmap=wx.Image(path).ConvertToBitmap(),
                    splashStyle=wx.SPLASH_CENTRE_ON_SCREEN|wx.SPLASH_TIMEOUT,
                    milliseconds=duration,
                    parent=None)
                wx.Yield()
                # For some reason splashDuration and sleep do not
                # correspond to each other at least not on Windows.
                # Maybe it's because duration is in milliseconds and
                # sleep in seconds.  Thus we need to increase the
                # sleep time a bit. A factor of 1.2 seems to work.
                sleepFactor = 1.2
                time.sleep(sleepFactor * duration / 1000)


class GUI (UserInterface):
    """wxWindows graphical user interface.
    """
    def __init__(self):
        super(GUI, self).__init__(name='gui')

    def default_settings(self):
        """Return a list of :class:`hooke.config.Setting`\s for any
        configurable UI settings.

        The suggested section setting is::

            Setting(section=self.setting_section, help=self.__doc__)
        """
        return [
            Setting(section=self.setting_section, help=self.__doc__),
            Setting(section=self.setting_section, option='icon image',
                    value=os.path.join('doc', 'img', 'microscope.ico'),
                    type='file',
                    help='Path to the hooke icon image.'),
            Setting(section=self.setting_section, option='show splash screen',
                    value=True, type='bool',
                    help='Enable/disable the splash screen'),
            Setting(section=self.setting_section, option='splash screen image',
                    value=os.path.join('doc', 'img', 'hooke.jpg'),
                    type='file',
                    help='Path to the Hooke splash screen image.'),
            Setting(section=self.setting_section,
                    option='splash screen duration',
                    value=1000, type='int',
                    help='Duration of the splash screen in milliseconds.'),
            Setting(section=self.setting_section, option='perspective path',
                    value=os.path.join('resources', 'gui', 'perspective'),
                    help='Directory containing perspective files.'), # TODO: allow colon separated list, like $PATH.
            Setting(section=self.setting_section, option='perspective extension',
                    value='.txt',
                    help='Extension for perspective files.'),
            Setting(section=self.setting_section, option='hide extensions',
                    value=False, type='bool',
                    help='Hide file extensions when displaying names.'),
            Setting(section=self.setting_section, option='plot legend',
                    value=True, type='bool',
                    help='Enable/disable the plot legend.'),
            Setting(section=self.setting_section, option='plot SI format',
                    value='True', type='bool',
                    help='Enable/disable SI plot axes numbering.'),
            Setting(section=self.setting_section, option='plot decimals',
                    value=2, type='int',
                    help='Number of decimal places to show if "plot SI format" is enabled.'),
            Setting(section=self.setting_section, option='folders-workdir',
                    value='.', type='path',
                    help='This should probably go...'),
            Setting(section=self.setting_section, option='folders-filters',
                    value='.', type='path',
                    help='This should probably go...'),
            Setting(section=self.setting_section, option='active perspective',
                    value='Default',
                    help='Name of active perspective file (or "Default").'),
            Setting(section=self.setting_section,
                    option='folders-filter-index',
                    value=0, type='int',
                    help='This should probably go...'),
            Setting(section=self.setting_section, option='main height',
                    value=450, type='int',
                    help='Height of main window in pixels.'),
            Setting(section=self.setting_section, option='main width',
                    value=800, type='int',
                    help='Width of main window in pixels.'),
            Setting(section=self.setting_section, option='main top',
                    value=0, type='int',
                    help='Pixels from screen top to top of main window.'),
            Setting(section=self.setting_section, option='main left',
                    value=0, type='int',
                    help='Pixels from screen left to left of main window.'),
            Setting(section=self.setting_section, option='selected command',
                    value='load playlist',
                    help='Name of the initially selected command.'),
            ]

    def _app(self, commands, ui_to_command_queue, command_to_ui_queue):
        redirect = True
        if __debug__:
            redirect=False
        app = HookeApp(gui=self,
                       commands=commands,
                       inqueue=ui_to_command_queue,
                       outqueue=command_to_ui_queue,
                       redirect=redirect)
        return app

    def run(self, commands, ui_to_command_queue, command_to_ui_queue):
        app = self._app(commands, ui_to_command_queue, command_to_ui_queue)
        app.MainLoop()
