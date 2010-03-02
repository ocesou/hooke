#!/usr/bin/env python

'''
HOOKE - A force spectroscopy review & analysis tool

Copyright 2008 by Massimo Sandal (University of Bologna, Italy)
Copyright 2010 by Rolf Schmidt (Concordia University, Canada)

This program is released under the GNU General Public License version 2.
'''

import lib.libhooke as lh
import wxversion
wxversion.select(lh.WX_GOOD)

from configobj import ConfigObj
import copy
import os.path
import platform
import shutil
import time

import wx.html
import wx.lib.agw.aui as aui
import wx.lib.evtmgr as evtmgr
import wx.propgrid as wxpg

from matplotlib.ticker import FuncFormatter

from configobj import __version__ as configobj_version
from matplotlib import __version__ as mpl_version
from numpy import __version__ as numpy_version
from scipy import __version__ as scipy_version
from sys import version as python_version
from wx import __version__ as wx_version
from wx.propgrid import PROPGRID_MAJOR
from wx.propgrid import PROPGRID_MINOR
from wx.propgrid import PROPGRID_RELEASE

try:
    from agw import cubecolourdialog as CCD
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.cubecolourdialog as CCD

#set the Hooke directory
lh.hookeDir = os.path.abspath(os.path.dirname(__file__))
from config.config import config
import drivers
import lib.clickedpoint
import lib.curve
import lib.delta
import lib.playlist
import lib.plotmanipulator
import lib.prettyformat
import panels.commands
import panels.note
import panels.perspectives
import panels.playlist
import panels.plot
import panels.propertyeditor
import panels.results
import plugins

global __version__
global __codename__
global __releasedate__
__version__ = lh.HOOKE_VERSION[0]
__codename__ = lh.HOOKE_VERSION[1]
__releasedate__ = lh.HOOKE_VERSION[2]
__release_name__ = lh.HOOKE_VERSION[1]

ID_About = wx.NewId()
ID_Next = wx.NewId()
ID_Previous = wx.NewId()

ID_ViewAssistant = wx.NewId()
ID_ViewCommands = wx.NewId()
ID_ViewFolders = wx.NewId()
ID_ViewNote = wx.NewId()
ID_ViewOutput = wx.NewId()
ID_ViewPlaylists = wx.NewId()
ID_ViewProperties = wx.NewId()
ID_ViewResults = wx.NewId()

ID_DeletePerspective = wx.NewId()
ID_SavePerspective = wx.NewId()

ID_FirstPerspective = ID_SavePerspective + 1000
#I hope we'll never have more than 1000 perspectives
ID_FirstPlot = ID_SavePerspective + 2000

class Hooke(wx.App):

    def OnInit(self):
        self.SetAppName('Hooke')
        self.SetVendorName('')

        window_height = config['main']['height']
        window_left= config['main']['left']
        window_top = config['main']['top']
        window_width = config['main']['width']

        #sometimes, the ini file gets confused and sets 'left'
        #and 'top' to large negative numbers
        #let's catch and fix this
        #keep small negative numbers, the user might want those
        if window_left < -window_width:
            window_left = 0
        if window_top < -window_height:
            window_top = 0
        window_position = (window_left, window_top)
        window_size = (window_width, window_height)

        #setup the splashscreen
        if config['splashscreen']['show']:
            filename = lh.get_file_path('hooke.jpg', ['resources'])
            if os.path.isfile(filename):
                bitmap = wx.Image(filename).ConvertToBitmap()
                splashStyle = wx.SPLASH_CENTRE_ON_SCREEN|wx.SPLASH_TIMEOUT
                splashDuration = config['splashscreen']['duration']
                wx.SplashScreen(bitmap, splashStyle, splashDuration, None, -1)
                wx.Yield()
                '''
                we need for the splash screen to disappear
                for whatever reason splashDuration and sleep do not correspond to each other
                at least not on Windows
                maybe it's because duration is in milliseconds and sleep in seconds
                thus we need to increase the sleep time a bit
                a factor of 1.2 seems to work quite well
                '''
                sleepFactor = 1.2
                time.sleep(sleepFactor * splashDuration / 1000)

        plugin_objects = []
        for plugin in config['plugins']:
            if config['plugins'][plugin]:
                filename = ''.join([plugin, '.py'])
                path = lh.get_file_path(filename, ['plugins'])
                if os.path.isfile(path):
                    #get the corresponding filename and path
                    plugin_name = ''.join(['plugins.', plugin])
                    #import the module
                    __import__(plugin_name)
                    #get the file that contains the plugin
                    class_file = getattr(plugins, plugin)
                    #get the class that contains the commands
                    class_object = getattr(class_file, plugin + 'Commands')
                    plugin_objects.append(class_object)

        def make_command_class(*bases):
            #create metaclass with plugins and plotmanipulators
            return type(HookeFrame)("HookeFramePlugged", bases + (HookeFrame,), {})
        frame = make_command_class(*plugin_objects)(parent=None, id=wx.ID_ANY, title='Hooke', pos=window_position, size=window_size)
        frame.Show(True)
        self.SetTopWindow(frame)

        return True

    def OnExit(self):
        return True


class HookeFrame(wx.Frame):

    def __init__(self, parent, id=-1, title='', pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE|wx.SUNKEN_BORDER|wx.CLIP_CHILDREN):
        #call parent constructor
        wx.Frame.__init__(self, parent, id, title, pos, size, style)
        self.config = config
        self.CreateApplicationIcon()
        #self.configs contains: {the name of the Commands file: corresponding ConfigObj}
        self.configs = {}
        #self.displayed_plot holds the currently displayed plot
        self.displayed_plot = None
        #self.playlists contains: {the name of the playlist: [playlist, tabIndex, plotID]}
        self.playlists = {}
        #list of all plotmanipulators
        self.plotmanipulators = []
        #self.plugins contains: {the name of the plugin: [caption, function]}
        self.plugins = {}
        #self.results_str contains the type of results we want to display
        self.results_str = 'wlc'

        #tell FrameManager to manage this frame
        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self)
        #set the gradient style
        self._mgr.GetArtProvider().SetMetric(aui.AUI_DOCKART_GRADIENT_TYPE, aui.AUI_GRADIENT_NONE)
        #set transparent drag
        self._mgr.SetFlags(self._mgr.GetFlags() ^ aui.AUI_MGR_TRANSPARENT_DRAG)

        # set up default notebook style
        self._notebook_style = aui.AUI_NB_DEFAULT_STYLE | aui.AUI_NB_TAB_EXTERNAL_MOVE | wx.NO_BORDER
        self._notebook_theme = 0

        #holds the perspectives: {name, perspective_str}
        self._perspectives = {}

        # min size for the frame itself isn't completely done.
        # see the end up FrameManager::Update() for the test
        # code. For now, just hard code a frame minimum size
        self.SetMinSize(wx.Size(500, 500))
        #define the list of active drivers
        self.drivers = []
        for driver in self.config['drivers']:
            if self.config['drivers'][driver]:
                #get the corresponding filename and path
                filename = ''.join([driver, '.py'])
                path = lh.get_file_path(filename, ['drivers'])
                #the driver is active for driver[1] == 1
                if os.path.isfile(path):
                    #driver files are located in the 'drivers' subfolder
                    driver_name = ''.join(['drivers.', driver])
                    __import__(driver_name)
                    class_file = getattr(drivers, driver)
                    for command in dir(class_file):
                        if command.endswith('Driver'):
                            self.drivers.append(getattr(class_file, command))
        #import all active plugins and plotmanips
        #add 'core.ini' to self.configs (this is not a plugin and thus must be imported separately)
        ini_path = lh.get_file_path('core.ini', ['plugins'])
        plugin_config = ConfigObj(ini_path)
        #self.config.merge(plugin_config)
        self.configs['core'] = plugin_config
        #existing_commands contains: {command: plugin}
        existing_commands = {}
        #make sure we execute _plug_init() for every command line plugin we import
        for plugin in self.config['plugins']:
            if self.config['plugins'][plugin]:
                filename = ''.join([plugin, '.py'])
                path = lh.get_file_path(filename, ['plugins'])
                if os.path.isfile(path):
                    #get the corresponding filename and path
                    plugin_name = ''.join(['plugins.', plugin])
                    try:
                        #import the module
                        module = __import__(plugin_name)
                        #prepare the ini file for inclusion
                        ini_path = path.replace('.py', '.ini')
                        #include ini file
                        plugin_config = ConfigObj(ini_path)
                        #self.config.merge(plugin_config)
                        self.configs[plugin] = plugin_config
                        #add to plugins
                        commands = eval('dir(module.' + plugin+ '.' + plugin + 'Commands)')
                        #keep only commands (ie names that start with 'do_')
                        commands = [command for command in commands if command.startswith('do_')]
                        if commands:
                            for command in commands:
                                if existing_commands.has_key(command):
                                    message_str = 'Adding "' + command + '" in plugin "' + plugin + '".\n\n'
                                    message_str += '"' + command + '" already exists in "' + str(existing_commands[command]) + '".\n\n'
                                    message_str += 'Only "' + command + '" in "' + str(existing_commands[command]) + '" will work.\n\n'
                                    message_str += 'Please rename one of the commands in the source code and restart Hooke or disable one of the plugins.'
                                    dialog = wx.MessageDialog(self, message_str, 'Warning', wx.OK|wx.ICON_WARNING|wx.CENTER)
                                    dialog.ShowModal()
                                    dialog.Destroy()
                                existing_commands[command] = plugin
                            self.plugins[plugin] = commands
                        try:
                            #initialize the plugin
                            eval('module.' + plugin+ '.' + plugin + 'Commands._plug_init(self)')
                        except AttributeError:
                            pass
                    except ImportError:
                        pass
        #add commands from hooke.py i.e. 'core' commands
        commands = dir(HookeFrame)
        commands = [command for command in commands if command.startswith('do_')]
        if commands:
            self.plugins['core'] = commands
        #create panels here
        self.panelAssistant = self.CreatePanelAssistant()
        self.panelCommands = self.CreatePanelCommands()
        self.panelFolders = self.CreatePanelFolders()
        self.panelPlaylists = self.CreatePanelPlaylists()
        self.panelProperties = self.CreatePanelProperties()
        self.panelNote = self.CreatePanelNote()
        self.panelOutput = self.CreatePanelOutput()
        self.panelResults = self.CreatePanelResults()
        self.plotNotebook = self.CreateNotebook()

        # add panes
        self._mgr.AddPane(self.panelFolders, aui.AuiPaneInfo().Name('Folders').Caption('Folders').Left().CloseButton(True).MaximizeButton(False))
        self._mgr.AddPane(self.panelPlaylists, aui.AuiPaneInfo().Name('Playlists').Caption('Playlists').Left().CloseButton(True).MaximizeButton(False))
        self._mgr.AddPane(self.panelNote, aui.AuiPaneInfo().Name('Note').Caption('Note').Left().CloseButton(True).MaximizeButton(False))
        self._mgr.AddPane(self.plotNotebook, aui.AuiPaneInfo().Name('Plots').CenterPane().PaneBorder(False))
        self._mgr.AddPane(self.panelCommands, aui.AuiPaneInfo().Name('Commands').Caption('Settings and commands').Right().CloseButton(True).MaximizeButton(False))
        self._mgr.AddPane(self.panelProperties, aui.AuiPaneInfo().Name('Properties').Caption('Properties').Right().CloseButton(True).MaximizeButton(False))
        self._mgr.AddPane(self.panelAssistant, aui.AuiPaneInfo().Name('Assistant').Caption('Assistant').Right().CloseButton(True).MaximizeButton(False))
        self._mgr.AddPane(self.panelOutput, aui.AuiPaneInfo().Name('Output').Caption('Output').Bottom().CloseButton(True).MaximizeButton(False))
        self._mgr.AddPane(self.panelResults, aui.AuiPaneInfo().Name('Results').Caption('Results').Bottom().CloseButton(True).MaximizeButton(False))
        #self._mgr.AddPane(self.textCtrlCommandLine, aui.AuiPaneInfo().Name('CommandLine').CaptionVisible(False).Fixed().Bottom().Layer(2).CloseButton(False).MaximizeButton(False))
        #self._mgr.AddPane(panelBottom, aui.AuiPaneInfo().Name("panelCommandLine").Bottom().Position(1).CloseButton(False).MaximizeButton(False))

        # add the toolbars to the manager
        #self.toolbar=self.CreateToolBar()
        self.toolbarNavigation=self.CreateToolBarNavigation()
        #self._mgr.AddPane(self.toolbar, aui.AuiPaneInfo().Name('toolbar').Caption('Toolbar').ToolbarPane().Top().Layer(1).Row(1).LeftDockable(False).RightDockable(False))
        self._mgr.AddPane(self.toolbarNavigation, aui.AuiPaneInfo().Name('toolbarNavigation').Caption('Navigation').ToolbarPane().Top().Layer(1).Row(1).LeftDockable(False).RightDockable(False))
        # "commit" all changes made to FrameManager
        self._mgr.Update()
        #create the menubar after the panes so that the default perspective
        #is created with all panes open
        self.CreateMenuBar()
        self.statusbar = self.CreateStatusbar()
        self._BindEvents()

        name = self.config['perspectives']['active']
        menu_item = self.GetPerspectiveMenuItem(name)
        if menu_item is not None:
            self.OnRestorePerspective(menu_item)
            #TODO: config setting to remember playlists from last session
        self.playlists = self.panelPlaylists.Playlists
        #initialize the commands tree
        self.panelCommands.Initialize(self.plugins)
        for command in dir(self):
            if command.startswith('plotmanip_'):
                self.plotmanipulators.append(lib.plotmanipulator.Plotmanipulator(method=getattr(self, command), command=command))

        #load default list, if possible
        self.do_loadlist(self.GetStringFromConfig('core', 'preferences', 'playlist'))

    def _BindEvents(self):
        #TODO: figure out if we can use the eventManager for menu ranges
        #and events of 'self' without raising an assertion fail error
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        # Show How To Use The Closing Panes Event
        self.Bind(aui.EVT_AUI_PANE_CLOSE, self.OnPaneClose)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnNotebookPageClose)
        #menu
        evtmgr.eventManager.Register(self.OnAbout, wx.EVT_MENU, win=self, id=wx.ID_ABOUT)
        evtmgr.eventManager.Register(self.OnClose, wx.EVT_MENU, win=self, id=wx.ID_EXIT)
        #view
        self.Bind(wx.EVT_MENU_RANGE, self.OnView, id=ID_ViewAssistant, id2=ID_ViewResults)
        #perspectives
        self.Bind(wx.EVT_MENU, self.OnDeletePerspective, id=ID_DeletePerspective)
        self.Bind(wx.EVT_MENU, self.OnSavePerspective, id=ID_SavePerspective)
        self.Bind(wx.EVT_MENU_RANGE, self.OnRestorePerspective, id=ID_FirstPerspective, id2=ID_FirstPerspective+1000)
        #toolbar
        evtmgr.eventManager.Register(self.OnNext, wx.EVT_TOOL, win=self, id=ID_Next)
        evtmgr.eventManager.Register(self.OnPrevious, wx.EVT_TOOL, win=self, id=ID_Previous)
        #self.Bind(.EVT_AUITOOLBAR_TOOL_DROPDOWN, self.OnDropDownToolbarItem, id=ID_DropDownToolbarItem)
        #dir control
        treeCtrl = self.panelFolders.GetTreeCtrl()
        #tree.Bind(wx.EVT_LEFT_UP, self.OnDirCtrl1LeftUp)
        #tree.Bind(wx.EVT_LEFT_DOWN, self.OnGenericDirCtrl1LeftDown)
        treeCtrl.Bind(wx.EVT_LEFT_DCLICK, self.OnDirCtrlLeftDclick)
        #playlist tree
        self.panelPlaylists.PlaylistsTree.Bind(wx.EVT_LEFT_DOWN, self.OnPlaylistsLeftDown)
        self.panelPlaylists.PlaylistsTree.Bind(wx.EVT_LEFT_DCLICK, self.OnPlaylistsLeftDclick)
        #commands tree
        evtmgr.eventManager.Register(self.OnExecute, wx.EVT_BUTTON, self.panelCommands.ExecuteButton)
        evtmgr.eventManager.Register(self.OnTreeCtrlCommandsSelectionChanged, wx.EVT_TREE_SEL_CHANGED, self.panelCommands.CommandsTree)
        evtmgr.eventManager.Register(self.OnTreeCtrlItemActivated, wx.EVT_TREE_ITEM_ACTIVATED, self.panelCommands.CommandsTree)
        evtmgr.eventManager.Register(self.OnUpdateNote, wx.EVT_BUTTON, self.panelNote.UpdateButton)
        #property editor
        self.panelProperties.pg.Bind(wxpg.EVT_PG_CHANGED, self.OnPropGridChanged)
        #results panel
        self.panelResults.results_list.OnCheckItem = self.OnResultsCheck

    def _GetActiveFileIndex(self):
        lib.playlist.Playlist = self.GetActivePlaylist()
        #get the selected item from the tree
        selected_item = self.panelPlaylists.PlaylistsTree.GetSelection()
        #test if a playlist or a curve was double-clicked
        if self.panelPlaylists.PlaylistsTree.ItemHasChildren(selected_item):
            return -1
        else:
            count = 0
            selected_item = self.panelPlaylists.PlaylistsTree.GetPrevSibling(selected_item)
            while selected_item.IsOk():
                count += 1
                selected_item = self.panelPlaylists.PlaylistsTree.GetPrevSibling(selected_item)
            return count

    def _GetPlaylistTab(self, name):
        for index, page in enumerate(self.plotNotebook._tabs._pages):
            if page.caption == name:
                return index
        return -1

    def _GetUniquePlaylistName(self, name):
        playlist_name = name
        count = 1
        while playlist_name in self.playlists:
            playlist_name = ''.join([name, str(count)])
            count += 1
        return playlist_name

    def _RestorePerspective(self, name):
        self._mgr.LoadPerspective(self._perspectives[name])
        self.config['perspectives']['active'] = name
        self._mgr.Update()
        all_panes = self._mgr.GetAllPanes()
        for pane in all_panes:
            if not pane.name.startswith('toolbar'):
                if pane.name == 'Assistant':
                    self.MenuBar.FindItemById(ID_ViewAssistant).Check(pane.window.IsShown())
                if pane.name == 'Folders':
                    self.MenuBar.FindItemById(ID_ViewFolders).Check(pane.window.IsShown())
                if pane.name == 'Playlists':
                    self.MenuBar.FindItemById(ID_ViewPlaylists).Check(pane.window.IsShown())
                if pane.name == 'Commands':
                    self.MenuBar.FindItemById(ID_ViewCommands).Check(pane.window.IsShown())
                if pane.name == 'Note':
                    self.MenuBar.FindItemById(ID_ViewNote).Check(pane.window.IsShown())
                if pane.name == 'Properties':
                    self.MenuBar.FindItemById(ID_ViewProperties).Check(pane.window.IsShown())
                if pane.name == 'Output':
                    self.MenuBar.FindItemById(ID_ViewOutput).Check(pane.window.IsShown())
                if pane.name == 'Results':
                    self.MenuBar.FindItemById(ID_ViewResults).Check(pane.window.IsShown())

    def _SavePerspectiveToFile(self, name, perspective):
        filename = ''.join([name, '.txt'])
        filename = lh.get_file_path(filename, ['perspectives'])
        perspectivesFile = open(filename, 'w')
        perspectivesFile.write(perspective)
        perspectivesFile.close()

    def _UnbindEvents(self):
        #menu
        evtmgr.eventManager.DeregisterListener(self.OnAbout)
        evtmgr.eventManager.DeregisterListener(self.OnClose)
        #toolbar
        evtmgr.eventManager.DeregisterListener(self.OnNext)
        evtmgr.eventManager.DeregisterListener(self.OnPrevious)
        #commands tree
        evtmgr.eventManager.DeregisterListener(self.OnExecute)
        evtmgr.eventManager.DeregisterListener(self.OnTreeCtrlCommandsSelectionChanged)
        evtmgr.eventManager.DeregisterListener(self.OnTreeCtrlItemActivated)
        evtmgr.eventManager.DeregisterListener(self.OnUpdateNote)

    def AddPlaylist(self, playlist=None, name='Untitled'):
        if playlist and playlist.count > 0:
            playlist.name = self._GetUniquePlaylistName(name)
            playlist.reset()
            self.AddToPlaylists(playlist)

    def AddPlaylistFromFiles(self, files=[], name='Untitled'):
        if files:
            playlist = lib.playlist.Playlist(self, self.drivers)
            for item in files:
                playlist.add_curve(item)
        if playlist.count > 0:
            playlist.name = self._GetUniquePlaylistName(name)
            playlist.reset()
            self.AddTayliss(playlist)

    def AddToPlaylists(self, playlist):
        if playlist.count > 0:
            #setup the playlist in the Playlist tree
            tree_root = self.panelPlaylists.PlaylistsTree.GetRootItem()
            playlist_root = self.panelPlaylists.PlaylistsTree.AppendItem(tree_root, playlist.name, 0)
            #add all files to the Playlist tree
#            files = {}
            hide_curve_extension = self.GetBoolFromConfig('core', 'preferences', 'hide_curve_extension')
            for index, file_to_add in enumerate(playlist.files):
                #optionally remove the extension from the name of the curve
                if hide_curve_extension:
                    file_to_add.name = lh.remove_extension(file_to_add.name)
                file_ID = self.panelPlaylists.PlaylistsTree.AppendItem(playlist_root, file_to_add.name, 1)
                if index == playlist.index:
                    self.panelPlaylists.PlaylistsTree.SelectItem(file_ID)
            playlist.reset()
            #create the plot tab and add playlist to the dictionary
            plotPanel = panels.plot.PlotPanel(self, ID_FirstPlot + len(self.playlists))
            notebook_tab = self.plotNotebook.AddPage(plotPanel, playlist.name, True)
            #tab_index = self.plotNotebook.GetSelection()
            playlist.figure = plotPanel.get_figure()
            self.playlists[playlist.name] = playlist
            #self.playlists[playlist.name] = [playlist, figure]
            self.panelPlaylists.PlaylistsTree.Expand(playlist_root)
            self.statusbar.SetStatusText(playlist.get_status_string(), 0)
            self.UpdateNote()
            self.UpdatePlot()

    def AppendToOutput(self, text):
        self.panelOutput.AppendText(''.join([text, '\n']))

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

    def CreateApplicationIcon(self):
        iconFile = 'resources' + os.sep + 'microscope.ico'
        icon = wx.Icon(iconFile, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

    def CreateCommandLine(self):
        return wx.TextCtrl(self, -1, '', style=wx.NO_BORDER|wx.EXPAND)

    def CreatePanelAssistant(self):
        panel = wx.TextCtrl(self, -1, '', wx.Point(0, 0), wx.Size(150, 90), wx.NO_BORDER|wx.TE_MULTILINE)
        panel.SetEditable(False)
        return panel

    def CreatePanelCommands(self):
        return panels.commands.Commands(self)

    def CreatePanelFolders(self):
        #set file filters
        filters = self.config['folders']['filters']
        index = self.config['folders'].as_int('filterindex')
        #set initial directory
        folder = self.GetStringFromConfig('core', 'preferences', 'workdir')
        return wx.GenericDirCtrl(self, -1, dir=folder, size=(200, 250), style=wx.DIRCTRL_SHOW_FILTERS, filter=filters, defaultFilter=index)

    def CreatePanelNote(self):
        return panels.note.Note(self)

    def CreatePanelOutput(self):
        return wx.TextCtrl(self, -1, '', wx.Point(0, 0), wx.Size(150, 90), wx.NO_BORDER|wx.TE_MULTILINE)

    def CreatePanelPlaylists(self):
        return panels.playlist.Playlists(self)

    def CreatePanelProperties(self):
        return panels.propertyeditor.PropertyEditor(self)

    def CreatePanelResults(self):
        return panels.results.Results(self)

    def CreatePanelWelcome(self):
        #TODO: move into panels.welcome
        ctrl = wx.html.HtmlWindow(self, -1, wx.DefaultPosition, wx.Size(400, 300))
        introStr = '<h1>Welcome to Hooke</h1>' + \
                 '<h3>Features</h3>' + \
                 '<ul>' + \
                 '<li>View, annotate, measure force files</li>' + \
                 '<li>Worm-like chain fit of force peaks</li>' + \
                 '<li>Automatic convolution-based filtering of empty files</li>' + \
                 '<li>Automatic fit and measurement of multiple force peaks</li>' + \
                 '<li>Handles force-clamp force experiments (experimental)</li>' + \
                 '<li>It is extensible by users by means of plugins and drivers</li>' + \
                 '</ul>' + \
                 '<p>See the <a href="http://code.google.com/p/hooke/wiki/DocumentationIndex">DocumentationIndex</a> for more information</p>'
        ctrl.SetPage(introStr)
        return ctrl

    def CreateMenuBar(self):
        menu_bar = wx.MenuBar()
        self.SetMenuBar(menu_bar)
        #file
        file_menu = wx.Menu()
        file_menu.Append(wx.ID_EXIT, 'Exit\tCtrl-Q')
#        edit_menu.AppendSeparator();
#        edit_menu.Append(ID_Config, 'Preferences')
        #view
        view_menu = wx.Menu()
        view_menu.AppendCheckItem(ID_ViewFolders, 'Folders\tF5')
        view_menu.AppendCheckItem(ID_ViewPlaylists, 'Playlists\tF6')
        view_menu.AppendCheckItem(ID_ViewCommands, 'Commands\tF7')
        view_menu.AppendCheckItem(ID_ViewProperties, 'Properties\tF8')
        view_menu.AppendCheckItem(ID_ViewAssistant, 'Assistant\tF9')
        view_menu.AppendCheckItem(ID_ViewResults, 'Results\tF10')
        view_menu.AppendCheckItem(ID_ViewOutput, 'Output\tF11')
        view_menu.AppendCheckItem(ID_ViewNote, 'Note\tF12')
        #perspectives
        perspectives_menu = wx.Menu()

        #help
        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, 'About Hooke')
        #put it all together
        menu_bar.Append(file_menu, 'File')
        menu_bar.Append(view_menu, 'View')
        menu_bar.Append(perspectives_menu, "Perspectives")
        self.UpdatePerspectivesMenu()
        menu_bar.Append(help_menu, 'Help')

    def CreateNotebook(self):
        # create the notebook off-window to avoid flicker
        client_size = self.GetClientSize()
        ctrl = aui.AuiNotebook(self, -1, wx.Point(client_size.x, client_size.y), wx.Size(430, 200), self._notebook_style)
        arts = [aui.AuiDefaultTabArt, aui.AuiSimpleTabArt, aui.VC71TabArt, aui.FF2TabArt, aui.VC8TabArt, aui.ChromeTabArt]
        art = arts[self._notebook_theme]()
        ctrl.SetArtProvider(art)
        #uncomment if we find a nice icon
        #page_bmp = wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16, 16))
        ctrl.AddPage(self.CreatePanelWelcome(), "Welcome", False)
        return ctrl

    def CreateStatusbar(self):
        statusbar = self.CreateStatusBar(2, wx.ST_SIZEGRIP)
        statusbar.SetStatusWidths([-2, -3])
        statusbar.SetStatusText('Ready', 0)
        welcomeString=u'Welcome to Hooke (version '+__version__+', '+__release_name__+')!'
        statusbar.SetStatusText(welcomeString, 1)
        return statusbar

    def CreateToolBarNavigation(self):
        toolbar = wx.ToolBar(self, -1, wx.DefaultPosition, wx.DefaultSize, wx.TB_FLAT | wx.TB_NODIVIDER)
        toolbar.SetToolBitmapSize(wx.Size(16,16))
        toolbar_bmpBack = wx.ArtProvider_GetBitmap(wx.ART_GO_BACK, wx.ART_OTHER, wx.Size(16, 16))
        toolbar_bmpForward = wx.ArtProvider_GetBitmap(wx.ART_GO_FORWARD, wx.ART_OTHER, wx.Size(16, 16))
        toolbar.AddLabelTool(ID_Previous, 'Previous', toolbar_bmpBack, shortHelp='Previous curve')
        toolbar.AddLabelTool(ID_Next, 'Next', toolbar_bmpForward, shortHelp='Next curve')
        toolbar.Realize()
        return toolbar

    def DeleteFromPlaylists(self, name):
        if name in self.playlists:
            del self.playlists[name]
        tree_root = self.panelPlaylists.PlaylistsTree.GetRootItem()
        item, cookie = self.panelPlaylists.PlaylistsTree.GetFirstChild(tree_root)
        while item.IsOk():
            playlist_name = self.panelPlaylists.PlaylistsTree.GetItemText(item)
            if playlist_name == name:
                try:
                    self.panelPlaylists.PlaylistsTree.Delete(item)
                except:
                    pass
            item = self.panelPlaylists.PlaylistsTree.GetNextSibling(item)

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

    def GetActivePlaylist(self):
        playlist_name = self.GetActivePlaylistName()
        if playlist_name in self.playlists:
            return self.playlists[playlist_name]
        return None

    def GetActivePlaylistName(self):
        #get the selected item from the tree
        selected_item = self.panelPlaylists.PlaylistsTree.GetSelection()
        #test if a playlist or a curve was double-clicked
        if self.panelPlaylists.PlaylistsTree.ItemHasChildren(selected_item):
            playlist_item = selected_item
        else:
            #get the name of the playlist
            playlist_item = self.panelPlaylists.PlaylistsTree.GetItemParent(selected_item)
        #now we have a playlist
        return self.panelPlaylists.PlaylistsTree.GetItemText(playlist_item)

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
        return self._mgr.GetArtProvider()

    def GetBoolFromConfig(self, *args):
        if len(args) == 2:
            plugin = args[0]
            section = args[0]
            key = args[1]
        elif len(args) == 3:
            plugin = args[0]
            section = args[1]
            key = args[2]
        if self.configs.has_key(plugin):
            config = self.configs[plugin]
            return config[section][key].as_bool('value')
        return None

    def GetColorFromConfig(self, *args):
        if len(args) == 2:
            plugin = args[0]
            section = args[0]
            key = args[1]
        elif len(args) == 3:
            plugin = args[0]
            section = args[1]
            key = args[2]
        if self.configs.has_key(plugin):
            config = self.configs[plugin]
            color_tuple = eval(config[section][key]['value'])
            color = [value / 255.0 for value in color_tuple]
            return color
        return None

    def GetFloatFromConfig(self, *args):
        if len(args) == 2:
            plugin = args[0]
            section = args[0]
            key = args[1]
        elif len(args) == 3:
            plugin = args[0]
            section = args[1]
            key = args[2]
        if self.configs.has_key(plugin):
            config = self.configs[plugin]
            return config[section][key].as_float('value')
        return None

    def GetIntFromConfig(self, *args):
        if len(args) == 2:
            plugin = args[0]
            section = args[0]
            key = args[1]
        elif len(args) == 3:
            plugin = args[0]
            section = args[1]
            key = args[2]
        if self.configs.has_key(plugin):
            config = self.configs[plugin]
            return config[section][key].as_int('value')
        return None

    def GetStringFromConfig(self, *args):
        if len(args) == 2:
            plugin = args[0]
            section = args[0]
            key = args[1]
        elif len(args) == 3:
            plugin = args[0]
            section = args[1]
            key = args[2]
        if self.configs.has_key(plugin):
            config = self.configs[plugin]
            return config[section][key]['value']
        return None

    def GetPlotmanipulator(self, name):
        '''
        Returns a plot manipulator function from its name
        '''
        for plotmanipulator in self.plotmanipulators:
            if plotmanipulator.name == name:
                return plotmanipulator
        return None

    def GetPerspectiveMenuItem(self, name):
        if self._perspectives.has_key(name):
            perspectives_list = [key for key, value in self._perspectives.iteritems()]
            perspectives_list.sort()
            index = perspectives_list.index(name)
            perspective_Id = ID_FirstPerspective + index
            menu_item = self.MenuBar.FindItemById(perspective_Id)
            return menu_item
        else:
            return None

    def HasPlotmanipulator(self, name):
        '''
        returns True if the plotmanipulator 'name' is loaded, False otherwise
        '''
        for plotmanipulator in self.plotmanipulators:
            if plotmanipulator.command == name:
                return True
        return False

    def OnAbout(self, event):
        message = 'Hooke\n\n'+\
            'A free, open source data analysis platform\n\n'+\
            'Copyright 2006-2008 by Massimo Sandal\n'+\
            'Copyright 2010 by Dr. Rolf Schmidt\n\n'+\
            'Hooke is released under the GNU General Public License version 2.'
        dialog = wx.MessageDialog(self, message, 'About Hooke', wx.OK | wx.ICON_INFORMATION)
        dialog.ShowModal()
        dialog.Destroy()

    def OnClose(self, event):
        #apply changes
        self.config['main']['height'] = str(self.GetSize().GetHeight())
        self.config['main']['left'] = str(self.GetPosition()[0])
        self.config['main']['top'] = str(self.GetPosition()[1])
        self.config['main']['width'] = str(self.GetSize().GetWidth())
        #save the configuration file to 'config/hooke.ini'
        self.config.write()
        #save all plugin config files
        for config in self.configs:
            plugin_config = self.configs[config]
            plugin_config.write()
        self._UnbindEvents()
        self._mgr.UnInit()
        del self._mgr
        self.Destroy()

    def OnDeletePerspective(self, event):
        dialog = panels.perspectives.Perspectives(self, -1, 'Delete perspective(s)')
        dialog.CenterOnScreen()
        dialog.ShowModal()
        dialog.Destroy()
        self.UpdatePerspectivesMenu()
        #unfortunately, there is a bug in wxWidgets (Ticket #3258) that
        #makes the radio item indicator in the menu disappear
        #the code should be fine once this issue is fixed

    def OnDirCtrlLeftDclick(self, event):
        file_path = self.panelFolders.GetPath()
        if os.path.isfile(file_path):
            if file_path.endswith('.hkp'):
                self.do_loadlist(file_path)
        event.Skip()

    def OnEraseBackground(self, event):
        event.Skip()

    def OnExecute(self, event):
        item = self.panelCommands.CommandsTree.GetSelection()
        if item.IsOk():
            if not self.panelCommands.CommandsTree.ItemHasChildren(item):
                item_text = self.panelCommands.CommandsTree.GetItemText(item)
                command = ''.join(['self.do_', item_text, '()'])
                #self.AppendToOutput(command + '\n')
                exec(command)

    def OnExit(self, event):
        self.Close()

    def OnNext(self, event):
        '''
        NEXT
        Go to the next curve in the playlist.
        If we are at the last curve, we come back to the first.
        -----
        Syntax: next, n
        '''
        selected_item = self.panelPlaylists.PlaylistsTree.GetSelection()
        if self.panelPlaylists.PlaylistsTree.ItemHasChildren(selected_item):
            #GetFirstChild returns a tuple
            #we only need the first element
            next_item = self.panelPlaylists.PlaylistsTree.GetFirstChild(selected_item)[0]
        else:
            next_item = self.panelPlaylists.PlaylistsTree.GetNextSibling(selected_item)
            if not next_item.IsOk():
                parent_item = self.panelPlaylists.PlaylistsTree.GetItemParent(selected_item)
                #GetFirstChild returns a tuple
                #we only need the first element
                next_item = self.panelPlaylists.PlaylistsTree.GetFirstChild(parent_item)[0]
        self.panelPlaylists.PlaylistsTree.SelectItem(next_item, True)
        if not self.panelPlaylists.PlaylistsTree.ItemHasChildren(selected_item):
            playlist = self.GetActivePlaylist()
            if playlist.count > 1:
                playlist.next()
                self.statusbar.SetStatusText(playlist.get_status_string(), 0)
                self.UpdateNote()
                self.UpdatePlot()

    def OnNotebookPageClose(self, event):
        ctrl = event.GetEventObject()
        playlist_name = ctrl.GetPageText(ctrl._curpage)
        self.DeleteFromPlaylists(playlist_name)

    def OnPaneClose(self, event):
        event.Skip()

    def OnPlaylistsLeftDclick(self, event):
        if self.panelPlaylists.PlaylistsTree.Count > 0:
            playlist_name = self.GetActivePlaylistName()
            #if that playlist already exists
            #we check if it is the active playlist (ie selected in panelPlaylists)
            #and switch to it if necessary
            if playlist_name in self.playlists:
                index = self.plotNotebook.GetSelection()
                current_playlist = self.plotNotebook.GetPageText(index)
                if current_playlist != playlist_name:
                    index = self._GetPlaylistTab(playlist_name)
                    self.plotNotebook.SetSelection(index)
                #if a curve was double-clicked
                item = self.panelPlaylists.PlaylistsTree.GetSelection()
                if not self.panelPlaylists.PlaylistsTree.ItemHasChildren(item):
                    index = self._GetActiveFileIndex()
                else:
                    index = 0
                if index >= 0:
                    playlist = self.GetActivePlaylist()
                    playlist.index = index
                    self.statusbar.SetStatusText(playlist.get_status_string(), 0)
                    self.UpdateNote()
                    self.UpdatePlot()
            #if you uncomment the following line, the tree will collapse/expand as well
            #event.Skip()

    def OnPlaylistsLeftDown(self, event):
        hit_item, hit_flags = self.panelPlaylists.PlaylistsTree.HitTest(event.GetPosition())
        if (hit_flags & wx.TREE_HITTEST_ONITEM) != 0:
            self.panelPlaylists.PlaylistsTree.SelectItem(hit_item)
            playlist_name = self.GetActivePlaylistName()
            playlist = self.GetActivePlaylist()
            #if a curve was clicked
            item = self.panelPlaylists.PlaylistsTree.GetSelection()
            if not self.panelPlaylists.PlaylistsTree.ItemHasChildren(item):
                index = self._GetActiveFileIndex()
                if index >= 0:
                    playlist.index = index
            self.playlists[playlist_name] = playlist
        event.Skip()

    def OnPrevious(self, event):
        '''
        PREVIOUS
        Go to the previous curve in the playlist.
        If we are at the first curve, we jump to the last.
        -------
        Syntax: previous, p
        '''
        #playlist = self.playlists[self.GetActivePlaylistName()][0]
        #select the previous curve and tell the user if we wrapped around
        #self.AppendToOutput(playlist.previous())
        selected_item = self.panelPlaylists.PlaylistsTree.GetSelection()
        if self.panelPlaylists.PlaylistsTree.ItemHasChildren(selected_item):
            previous_item = self.panelPlaylists.PlaylistsTree.GetLastChild(selected_item)
        else:
            previous_item = self.panelPlaylists.PlaylistsTree.GetPrevSibling(selected_item)
            if not previous_item.IsOk():
                parent_item = self.panelPlaylists.PlaylistsTree.GetItemParent(selected_item)
                previous_item = self.panelPlaylists.PlaylistsTree.GetLastChild(parent_item)
        self.panelPlaylists.PlaylistsTree.SelectItem(previous_item, True)
        playlist = self.GetActivePlaylist()
        if playlist.count > 1:
            playlist.previous()
            self.statusbar.SetStatusText(playlist.get_status_string(), 0)
            self.UpdateNote()
            self.UpdatePlot()

    def OnPropGridChanged (self, event):
        prop = event.GetProperty()
        if prop:
            item_section = self.panelProperties.SelectedTreeItem
            item_plugin = self.panelCommands.CommandsTree.GetItemParent(item_section)
            plugin = self.panelCommands.CommandsTree.GetItemText(item_plugin)
            config = self.configs[plugin]
            property_section = self.panelCommands.CommandsTree.GetItemText(item_section)
            property_key = prop.GetName()
            property_value = prop.GetDisplayedString()

            config[property_section][property_key]['value'] = property_value

    def OnRestorePerspective(self, event):
        name = self.MenuBar.FindItemById(event.GetId()).GetLabel()
        self._RestorePerspective(name)

    def OnResultsCheck(self, index, flag):
        results = self.GetActivePlot().results
        if results.has_key(self.results_str):
            results[self.results_str].results[index].visible = flag
            results[self.results_str].update()
            self.UpdatePlot()

    def OnSavePerspective(self, event):

        def nameExists(name):
            menu_position = self.MenuBar.FindMenu('Perspectives')
            menu = self.MenuBar.GetMenu(menu_position)
            for item in menu.GetMenuItems():
                if item.GetText() == name:
                    return True
            return False

        done = False
        while not done:
            dialog = wx.TextEntryDialog(self, 'Enter a name for the new perspective:', 'Save perspective')
            dialog.SetValue('New perspective')
            if dialog.ShowModal() != wx.ID_OK:
                return
            else:
                name = dialog.GetValue()

            if nameExists(name):
                dialogConfirm = wx.MessageDialog(self, 'A file with this name already exists.\n\nDo you want to replace it?', 'Confirm', wx.YES_NO|wx.ICON_QUESTION|wx.CENTER)
                if dialogConfirm.ShowModal() == wx.ID_YES:
                    done = True
            else:
                done = True

        perspective = self._mgr.SavePerspective()
        self._SavePerspectiveToFile(name, perspective)
        self.config['perspectives']['active'] = name
        self.UpdatePerspectivesMenu()
#        if nameExists(name):
#            #check the corresponding menu item
#            menu_item = self.GetPerspectiveMenuItem(name)
#            #replace the perspectiveStr in _pespectives
#            self._perspectives[name] = perspective
#        else:
#            #because we deal with radio items, we need to do some extra work
#            #delete all menu items from the perspectives menu
#            for item in self._perspectives_menu.GetMenuItems():
#                self._perspectives_menu.DeleteItem(item)
#            #recreate the perspectives menu
#            self._perspectives_menu.Append(ID_SavePerspective, 'Save Perspective')
#            self._perspectives_menu.Append(ID_DeletePerspective, 'Delete Perspective')
#            self._perspectives_menu.AppendSeparator()
#            #convert the perspectives dictionary into a list
#            # the list contains:
#            #[0]: name of the perspective
#            #[1]: perspective
#            perspectives_list = [key for key, value in self._perspectives.iteritems()]
#            perspectives_list.append(name)
#            perspectives_list.sort()
#            #add all previous perspectives
#            for index, item in enumerate(perspectives_list):
#                menu_item = self._perspectives_menu.AppendRadioItem(ID_FirstPerspective + index, item)
#                if item == name:
#                    menu_item.Check()
#            #add the new perspective to _perspectives
#            self._perspectives[name] = perspective

    def OnSize(self, event):
        event.Skip()

    def OnTreeCtrlCommandsSelectionChanged(self, event):
        selected_item = event.GetItem()
        if selected_item is not None:
            plugin = ''
            section = ''
            #deregister/register the listener to avoid infinite loop
            evtmgr.eventManager.DeregisterListener(self.OnTreeCtrlCommandsSelectionChanged)
            self.panelCommands.CommandsTree.SelectItem(selected_item)
            evtmgr.eventManager.Register(self.OnTreeCtrlCommandsSelectionChanged, wx.EVT_TREE_SEL_CHANGED, self.panelCommands.CommandsTree)
            self.panelProperties.SelectedTreeItem = selected_item
            #if a command was clicked
            properties = []
            if not self.panelCommands.CommandsTree.ItemHasChildren(selected_item):
                item_plugin = self.panelCommands.CommandsTree.GetItemParent(selected_item)
                plugin = self.panelCommands.CommandsTree.GetItemText(item_plugin)
                if self.configs.has_key(plugin):
                    #config = self.panelCommands.CommandsTree.GetPyData(item_plugin)
                    config = self.configs[plugin]
                    section = self.panelCommands.CommandsTree.GetItemText(selected_item)
                    #display docstring in help window
                    doc_string = eval('self.do_' + section + '.__doc__')
                    if section in config:
                        for option in config[section]:
                            properties.append([option, config[section][option]])
            else:
                plugin = self.panelCommands.CommandsTree.GetItemText(selected_item)
                if plugin != 'core':
                    doc_string = eval('plugins.' + plugin + '.' + plugin + 'Commands.__doc__')
                else:
                    doc_string = 'The module "core" contains Hooke core functionality'
            if doc_string is not None:
                self.panelAssistant.ChangeValue(doc_string)
            else:
                self.panelAssistant.ChangeValue('')
            panels.propertyeditor.PropertyEditor.Initialize(self.panelProperties, properties)
            #save the currently selected command/plugin to the config file
            self.config['command']['command'] = section
            self.config['command']['plugin'] = plugin

    def OnTreeCtrlItemActivated(self, event):
        self.OnExecute(event)

    def OnUpdateNote(self, event):
        '''
        Saves the note to the active file.
        '''
        active_file = self.GetActiveFile()
        active_file.note = self.panelNote.Editor.GetValue()

    def OnView(self, event):
        menu_id = event.GetId()
        menu_item = self.MenuBar.FindItemById(menu_id)
        menu_label = menu_item.GetLabel()

        pane = self._mgr.GetPane(menu_label)
        pane.Show(not pane.IsShown())
        #if we don't do the following, the Folders pane does not resize properly on hide/show
        if pane.caption == 'Folders' and pane.IsShown() and pane.IsDocked():
            #folders_size = pane.GetSize()
            self.panelFolders.Fit()
        self._mgr.Update()

    def _clickize(self, xvector, yvector, index):
        '''
        Returns a ClickedPoint() object from an index and vectors of x, y coordinates
        '''
        point = lib.clickedpoint.ClickedPoint()
        point.index = index
        point.absolute_coords = xvector[index], yvector[index]
        point.find_graph_coords(xvector, yvector)
        return point

    def _delta(self, message='Click 2 points', whatset=lh.RETRACTION):
        '''
        Calculates the difference between two clicked points
        '''
        clicked_points = self._measure_N_points(N=2, message=message, whatset=whatset)

        plot = self.GetDisplayedPlotCorrected()
        curve = plot.curves[whatset]

        delta = lib.delta.Delta()
        delta.point1.x = clicked_points[0].graph_coords[0]
        delta.point1.y = clicked_points[0].graph_coords[1]
        delta.point2.x = clicked_points[1].graph_coords[0]
        delta.point2.y = clicked_points[1].graph_coords[1]
        delta.units.x = curve.units.x
        delta.units.y = curve.units.y

        return delta

    def _measure_N_points(self, N, message='', whatset=lh.RETRACTION):
        '''
        General helper function for N-points measurements
        By default, measurements are done on the retraction
        '''
        if message:
            dialog = wx.MessageDialog(None, message, 'Info', wx.OK)
            dialog.ShowModal()

        figure = self.GetActiveFigure()

        xvector = self.displayed_plot.curves[whatset].x
        yvector = self.displayed_plot.curves[whatset].y

        clicked_points = figure.ginput(N, timeout=-1, show_clicks=True)

        points = []
        for clicked_point in clicked_points:
            point = lib.clickedpoint.ClickedPoint()
            point.absolute_coords = clicked_point[0], clicked_point[1]
            point.dest = 0
            #TODO: make this optional?
            #so far, the clicked point is taken, not the corresponding data point
            point.find_graph_coords(xvector, yvector)
            point.is_line_edge = True
            point.is_marker = True
            points.append(point)
        return points

    def do_copylog(self):
        '''
        Copies all files in the current playlist that have a note to the destination folder.
        destination: select folder where you want the files to be copied
        use_LVDT_folder: when checked, the files will be copied to a folder called 'LVDT' in the destination folder (for MFP-1D files only)
        '''
        playlist = self.GetActivePlaylist()
        if playlist is not None:
            destination = self.GetStringFromConfig('core', 'copylog', 'destination')
            if not os.path.isdir(destination):
                os.makedirs(destination)
            for current_file in playlist.files:
                if current_file.note:
                    shutil.copy(current_file.filename, destination)
                    if current_file.driver.filetype == 'mfp1d':
                        filename = current_file.filename.replace('deflection', 'LVDT', 1)
                        path, name = os.path.split(filename)
                        filename = os.path.join(path, 'lvdt', name)
                        use_LVDT_folder = self.GetBoolFromConfig('core', 'copylog', 'use_LVDT_folder')
                        if use_LVDT_folder:
                            destination = os.path.join(destination, 'LVDT')
                        shutil.copy(filename, destination)

    def do_plotmanipulators(self):
        '''
        Please select the plotmanipulators you would like to use
        and define the order in which they will be applied to the data.

        Click 'Execute' to apply your changes.
        '''
        self.UpdatePlot()

    def do_preferences(self):
        '''
        Please set general preferences for Hooke here.
        hide_curve_extension: hides the extension of the force curve files.
                              not recommended for 'picoforce' files
        '''
        pass

    def do_test(self):
        '''
        Use this command for testing purposes. You find do_test in hooke.py.
        '''
        pass

    def do_version(self):
        '''
        VERSION
        ------
        Prints the current version and codename, plus library version. Useful for debugging.
        '''
        self.AppendToOutput('Hooke ' + __version__ + ' (' + __codename__ + ')')
        self.AppendToOutput('Released on: ' + __releasedate__)
        self.AppendToOutput('---')
        self.AppendToOutput('Python version: ' + python_version)
        self.AppendToOutput('WxPython version: ' + wx_version)
        self.AppendToOutput('Matplotlib version: ' + mpl_version)
        self.AppendToOutput('SciPy version: ' + scipy_version)
        self.AppendToOutput('NumPy version: ' + numpy_version)
        self.AppendToOutput('ConfigObj version: ' + configobj_version)
        self.AppendToOutput('wxPropertyGrid version: ' + '.'.join([str(PROPGRID_MAJOR), str(PROPGRID_MINOR), str(PROPGRID_RELEASE)]))
        self.AppendToOutput('---')
        self.AppendToOutput('Platform: ' + str(platform.uname()))
        self.AppendToOutput('******************************')
        self.AppendToOutput('Loaded plugins')
        self.AppendToOutput('---')

        #sort the plugins into alphabetical order
        plugins_list = [key for key, value in self.plugins.iteritems()]
        plugins_list.sort()
        for plugin in plugins_list:
            self.AppendToOutput(plugin)

    def UpdateNote(self):
        #update the note for the active file
        active_file = self.GetActiveFile()
        if active_file is not None:
            self.panelNote.Editor.SetValue(active_file.note)

    def UpdatePerspectivesMenu(self):
        #add perspectives to menubar and _perspectives
        perspectivesDirectory = os.path.join(lh.hookeDir, 'perspectives')
        self._perspectives = {}
        if os.path.isdir(perspectivesDirectory):
            perspectiveFileNames = os.listdir(perspectivesDirectory)
            for perspectiveFilename in perspectiveFileNames:
                filename = lh.get_file_path(perspectiveFilename, ['perspectives'])
                if os.path.isfile(filename):
                    perspectiveFile = open(filename, 'rU')
                    perspective = perspectiveFile.readline()
                    perspectiveFile.close()
                    if perspective:
                        name, extension = os.path.splitext(perspectiveFilename)
                        if extension == '.txt':
                            self._perspectives[name] = perspective

        #in case there are no perspectives
        if not self._perspectives:
            perspective = self._mgr.SavePerspective()
            self._perspectives['Default'] = perspective
            self._SavePerspectiveToFile('Default', perspective)

        selected_perspective = self.config['perspectives']['active']
        if not self._perspectives.has_key(selected_perspective):
            self.config['perspectives']['active'] = 'Default'
            selected_perspective = 'Default'

        perspectives_list = [key for key, value in self._perspectives.iteritems()]
        perspectives_list.sort()

        #get the Perspectives menu
        menu_position = self.MenuBar.FindMenu('Perspectives')
        menu = self.MenuBar.GetMenu(menu_position)
        #delete all menu items
        for item in menu.GetMenuItems():
            menu.DeleteItem(item)
        #rebuild the menu by adding the standard menu items
        menu.Append(ID_SavePerspective, 'Save Perspective')
        menu.Append(ID_DeletePerspective, 'Delete Perspective')
        menu.AppendSeparator()
        #add all previous perspectives
        for index, label in enumerate(perspectives_list):
            menu_item = menu.AppendRadioItem(ID_FirstPerspective + index, label)
            if label == selected_perspective:
                self._RestorePerspective(label)
                menu_item.Check(True)

    def UpdatePlaylistsTreeSelection(self):
        playlist = self.GetActivePlaylist()
        if playlist is not None:
            if playlist.index >= 0:
                self.statusbar.SetStatusText(playlist.get_status_string(), 0)
                self.UpdateNote()
                self.UpdatePlot()

    def UpdatePlot(self, plot=None):

        def add_to_plot(curve, set_scale=True):
            if curve.visible and curve.x and curve.y:
                #get the index of the subplot to use as destination
                destination = (curve.destination.column - 1) * number_of_rows + curve.destination.row - 1
                #set all parameters for the plot
                axes_list[destination].set_title(curve.title)
                if set_scale:
                    axes_list[destination].set_xlabel(curve.prefix.x + curve.units.x)
                    axes_list[destination].set_ylabel(curve.prefix.y + curve.units.y)
                    #set the formatting details for the scale
                    formatter_x = lib.curve.PrefixFormatter(curve.decimals.x, curve.prefix.x, use_zero)
                    formatter_y = lib.curve.PrefixFormatter(curve.decimals.y, curve.prefix.y, use_zero)
                    axes_list[destination].xaxis.set_major_formatter(formatter_x)
                    axes_list[destination].yaxis.set_major_formatter(formatter_y)
                if curve.style == 'plot':
                    axes_list[destination].plot(curve.x, curve.y, color=curve.color, label=curve.label, lw=curve.linewidth, zorder=1)
                if curve.style == 'scatter':
                    axes_list[destination].scatter(curve.x, curve.y, color=curve.color, label=curve.label, s=curve.size, zorder=2)
                #add the legend if necessary
                if curve.legend:
                    axes_list[destination].legend()

        if plot is None:
            active_file = self.GetActiveFile()
            if not active_file.driver:
                #the first time we identify a file, the following need to be set
                active_file.identify(self.drivers)
                for curve in active_file.plot.curves:
                    curve.decimals.x = self.GetIntFromConfig('core', 'preferences', 'x_decimals')
                    curve.decimals.y = self.GetIntFromConfig('core', 'preferences', 'y_decimals')
                    curve.legend = self.GetBoolFromConfig('core', 'preferences', 'legend')
                    curve.prefix.x = self.GetStringFromConfig('core', 'preferences', 'x_prefix')
                    curve.prefix.y = self.GetStringFromConfig('core', 'preferences', 'y_prefix')
            if active_file.driver is None:
                self.AppendToOutput('Invalid file: ' + active_file.filename)
                return
            self.displayed_plot = copy.deepcopy(active_file.plot)
            #add raw curves to plot
            self.displayed_plot.raw_curves = copy.deepcopy(self.displayed_plot.curves)
            #apply all active plotmanipulators
            self.displayed_plot = self.ApplyPlotmanipulators(self.displayed_plot, active_file)
            #add corrected curves to plot
            self.displayed_plot.corrected_curves = copy.deepcopy(self.displayed_plot.curves)
        else:
            active_file = None
            self.displayed_plot = copy.deepcopy(plot)

        figure = self.GetActiveFigure()
        figure.clear()

        #use '0' instead of e.g. '0.00' for scales
        use_zero = self.GetBoolFromConfig('core', 'preferences', 'use_zero')
        #optionally remove the extension from the title of the plot
        hide_curve_extension = self.GetBoolFromConfig('core', 'preferences', 'hide_curve_extension')
        if hide_curve_extension:
            title = lh.remove_extension(self.displayed_plot.title)
        else:
            title = self.displayed_plot.title
        figure.suptitle(title, fontsize=14)
        #create the list of all axes necessary (rows and columns)
        axes_list =[]
        number_of_columns = max([curve.destination.column for curve in self.displayed_plot.curves])
        number_of_rows = max([curve.destination.row for curve in self.displayed_plot.curves])
        for index in range(number_of_rows * number_of_columns):
            axes_list.append(figure.add_subplot(number_of_rows, number_of_columns, index + 1))

        #add all curves to the corresponding plots
        for curve in self.displayed_plot.curves:
            add_to_plot(curve)

        #make sure the titles of 'subplots' do not overlap with the axis labels of the 'main plot'
        figure.subplots_adjust(hspace=0.3)

        #display results
        self.panelResults.ClearResults()
        if self.displayed_plot.results.has_key(self.results_str):
            for curve in self.displayed_plot.results[self.results_str].results:
                add_to_plot(curve, set_scale=False)
            self.panelResults.DisplayResults(self.displayed_plot.results[self.results_str])
        else:
            self.panelResults.ClearResults()
        #refresh the plot
        figure.canvas.draw()

if __name__ == '__main__':

    ## now, silence a deprecation warning for py2.3
    import warnings
    warnings.filterwarnings("ignore", "integer", DeprecationWarning, "wxPython.gdi")

    redirect = True
    if __debug__:
        redirect=False

    app = Hooke(redirect=redirect)

    app.MainLoop()
