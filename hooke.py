#!/usr/bin/env python

'''
HOOKE - A force spectroscopy review & analysis tool

Copyright 2008 by Massimo Sandal (University of Bologna, Italy).
Copyright 2010 by Rolf Schmidt (Concordia University, Canada).

This program is released under the GNU General Public License version 2.
'''

import wxversion
import lib.libhooke as lh
wxversion.select(lh.WX_GOOD)

from configobj import ConfigObj
import copy
import os.path
import platform
import time
#import wx
import wx.html
import wx.lib.agw.aui as aui
import wx.lib.evtmgr as evtmgr
import wx.propgrid as wxpg

from matplotlib import __version__ as mpl_version
from numpy import __version__ as numpy_version
from scipy import __version__ as scipy_version
from sys import version as python_version
from wx import __version__ as wx_version

try:
    from agw import cubecolourdialog as CCD
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.cubecolourdialog as CCD

#set the Hooke directory
lh.hookeDir = os.path.abspath(os.path.dirname(__file__))
from config.config import config
import drivers
import lib.playlist
import lib.plotmanipulator
import panels.commands
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

#TODO: add general preferences to Hooke
#this might be useful
#ID_Config = wx.NewId()
ID_About = wx.NewId()
ID_Next = wx.NewId()
ID_Previous = wx.NewId()

ID_ViewAssistant = wx.NewId()
ID_ViewCommands = wx.NewId()
ID_ViewFolders = wx.NewId()
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

        windowPosition = (config['main']['left'], config['main']['top'])
        windowSize = (config['main']['width'], config['main']['height'])

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
        frame = make_command_class(*plugin_objects)(parent=None, id=wx.ID_ANY, title='Hooke', pos=windowPosition, size=windowSize)
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
        #create panels here
        self.panelAssistant = self.CreatePanelAssistant()
        self.panelCommands = self.CreatePanelCommands()
        self.panelFolders = self.CreatePanelFolders()
        self.panelPlaylists = self.CreatePanelPlaylists()
        self.panelProperties = self.CreatePanelProperties()
        self.panelOutput = self.CreatePanelOutput()
        self.panelResults = self.CreatePanelResults()
        self.plotNotebook = self.CreateNotebook()
        #self.textCtrlCommandLine=self.CreateCommandLine()

        # add panes
        self._mgr.AddPane(self.panelFolders, aui.AuiPaneInfo().Name('Folders').Caption('Folders').Left().CloseButton(True).MaximizeButton(False))
        self._mgr.AddPane(self.panelPlaylists, aui.AuiPaneInfo().Name('Playlists').Caption('Playlists').Left().CloseButton(True).MaximizeButton(False))
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
                        #TODO: check for existing commands and warn the user!
                        commands = [command for command in commands if command.startswith('do_')]
                        if commands:
                            self.plugins[plugin] = commands
                        try:
                            #initialize the plugin
                            eval('module.' + plugin+ '.' + plugin + 'Commands._plug_init(self)')
                        except AttributeError:
                            pass
                    except ImportError:
                        pass
        #initialize the commands tree
        commands = dir(HookeFrame)
        commands = [command for command in commands if command.startswith('do_')]
        if commands:
            self.plugins['core'] = commands
        self.panelCommands.Initialize(self.plugins)
        for command in dir(self):
            if command.startswith('plotmanip_'):
                self.plotmanipulators.append(lib.plotmanipulator.Plotmanipulator(method=getattr(self, command), command=command))

        #load default list, if possible
        self.do_loadlist(self.config['core']['list'])
        #self.do_loadlist()

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
            for index, file_to_add in enumerate(playlist.files):
                #TODO: optionally remove the extension from the name of the curve
                #item_text, extension = os.path.splitext(curve.name)
                #curve_ID = self.panelPlaylists.PlaylistsTree.AppendItem(playlist_root, item_text, 1)
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
            self.UpdatePlot()

    def AppendToOutput(self, text):
        self.panelOutput.AppendText(''.join([text, '\n']))

    def AppliesPlotmanipulator(self, name):
        '''
        returns True if the plotmanipulator 'name' is applied, False otherwise
        name does not contain 'plotmanip_', just the name of the plotmanipulator (e.g. 'flatten')
        '''
        return self.GetBoolFromConfig('core', 'plotmanipulators', name)

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
        folder = self.config['core']['workdir']
        return wx.GenericDirCtrl(self, -1, dir=folder, size=(200, 250), style=wx.DIRCTRL_SHOW_FILTERS, filter=filters, defaultFilter=index)

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
        #perspectives
#        perspectives_menu = self.CreatePerspectivesMenu()
        perspectives_menu = wx.Menu()

        #help
        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, 'About Hooke')
        #put it all together
        menu_bar.Append(file_menu, 'File')
#        menu_bar.Append(edit_menu, 'Edit')
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
        plot.curves = []
        plot.curves = copy.deepcopy(plot.curves)
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
#        self._mgr.LoadPerspective(self._perspectives[name])
#        self.config['perspectives']['active'] = name
#        self._mgr.Update()
#        all_panes = self._mgr.GetAllPanes()
#        for pane in all_panes:
#            if not pane.name.startswith('toolbar'):
#                if pane.name == 'Assistant':
#                    self.MenuBar.FindItemById(ID_ViewAssistant).Check(pane.window.IsShown())
#                if pane.name == 'Folders':
#                    self.MenuBar.FindItemById(ID_ViewFolders).Check(pane.window.IsShown())
#                if pane.name == 'Playlists':
#                    self.MenuBar.FindItemById(ID_ViewPlaylists).Check(pane.window.IsShown())
#                if pane.name == 'Commands':
#                    self.MenuBar.FindItemById(ID_ViewCommands).Check(pane.window.IsShown())
#                if pane.name == 'Properties':
#                    self.MenuBar.FindItemById(ID_ViewProperties).Check(pane.window.IsShown())
#                if pane.name == 'Output':
#                    self.MenuBar.FindItemById(ID_ViewOutput).Check(pane.window.IsShown())
#                if pane.name == 'Results':
#                    self.MenuBar.FindItemById(ID_ViewResults).Check(pane.window.IsShown())

    def OnResultsCheck(self, index, flag):
        #TODO: fix for multiple results
        results = self.GetActivePlot().results
        fit_function_str = self.GetStringFromConfig('results', 'show_results', 'fit_function')
        results[fit_function_str].results[index].visible = flag
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

    def _measure_N_points(self, N, message='', whatset=lh.RETRACTION):
        '''
        General helper function for N-points measurements
        By default, measurements are done on the retraction
        '''
        if message != '':
            dialog = wx.MessageDialog(None, message, 'Info', wx.OK)
            dialog.ShowModal()

        figure = self.GetActiveFigure()

        xvector = self.displayed_plot.curves[whatset].x
        yvector = self.displayed_plot.curves[whatset].y

        clicked_points = figure.ginput(N, timeout=-1, show_clicks=True)

        points = []
        for clicked_point in clicked_points:
            point = lh.ClickedPoint()
            point.absolute_coords = clicked_point[0], clicked_point[1]
            point.dest = 0
            #TODO: make this optional?
            #so far, the clicked point is taken, not the corresponding data point
            point.find_graph_coords(xvector, yvector)
            point.is_line_edge = True
            point.is_marker = True
            points.append(point)
        return points

    def _clickize(self, xvector, yvector, index):
        '''
        returns a ClickedPoint() object from an index and vectors of x, y coordinates
        '''
        point = lh.ClickedPoint()
        point.index = index
        point.absolute_coords = xvector[index], yvector[index]
        point.find_graph_coords(xvector, yvector)
        return point

    def _delta(self, color='black', message='Click 2 points', show=True, whatset=1):
        '''
        calculates the difference between two clicked points
        '''
        clicked_points = self._measure_N_points(N=2, message=message, whatset=whatset)
        dx = abs(clicked_points[0].graph_coords[0] - clicked_points[1].graph_coords[0])
        dy = abs(clicked_points[0].graph_coords[1] - clicked_points[1].graph_coords[1])

        plot = self.GetDisplayedPlotCorrected()

        curve = plot.curves[whatset]
        unitx = curve.units.x
        unity = curve.units.y

        #TODO: move this to clicked_points?
        if show:
            for point in clicked_points:
                points = copy.deepcopy(curve)
                points.x = point.graph_coords[0]
                points.y = point.graph_coords[1]

                points.color = color
                points.size = 20
                points.style = 'scatter'
                plot.curves.append(points)

        self.UpdatePlot(plot)

        return dx, unitx, dy, unity

    def do_plotmanipulators(self):
        '''
        Please select the plotmanipulators you would like to use
        and define the order in which they will be applied to the data.

        Click 'Execute' to apply your changes.
        '''
        self.UpdatePlot()

    def do_test(self):
        self.AppendToOutput(self.config['perspectives']['active'])
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
        self.AppendToOutput('---')
        self.AppendToOutput('Platform: ' + str(platform.uname()))
        #TODO: adapt to 'new' config
        #self.AppendToOutput('---')
        #self.AppendToOutput('Loaded plugins:', self.config['loaded_plugins'])

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
                    if perspective != '':
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
                self.UpdatePlot()

    def UpdatePlot(self, plot=None):

        def add_to_plot(curve):
            if curve.visible and curve.x and curve.y:
                destination = (curve.destination.column - 1) * number_of_rows + curve.destination.row - 1
                axes_list[destination].set_title(curve.title)
                axes_list[destination].set_xlabel(curve.units.x)
                axes_list[destination].set_ylabel(curve.units.y)
                if curve.style == 'plot':
                    axes_list[destination].plot(curve.x, curve.y, color=curve.color, label=curve.label, zorder=1)
                if curve.style == 'scatter':
                    axes_list[destination].scatter(curve.x, curve.y, color=curve.color, label=curve.label, s=curve.size, zorder=2)

        if plot is None:
            active_file = self.GetActiveFile()
            if not active_file.driver:
                active_file.identify(self.drivers)
            self.displayed_plot = copy.deepcopy(active_file.plot)
            #add raw curves to plot
            self.displayed_plot.raw_curves = copy.deepcopy(self.displayed_plot.curves)
            #apply all active plotmanipulators and add the 'manipulated' data
            for plotmanipulator in self.plotmanipulators:
                if self.GetBoolFromConfig('core', 'plotmanipulators', plotmanipulator.name):
                    self.displayed_plot = plotmanipulator.method(self.displayed_plot, active_file)
            #add corrected curves to plot
            self.displayed_plot.corrected_curves = copy.deepcopy(self.displayed_plot.curves)
        else:
            active_file = None
            self.displayed_plot = copy.deepcopy(plot)

        figure = self.GetActiveFigure()

        figure.clear()
        figure.suptitle(self.displayed_plot.title, fontsize=14)

        axes_list =[]

        number_of_columns = max([curve.destination.column for curve in self.displayed_plot.curves])
        number_of_rows = max([curve.destination.row for curve in self.displayed_plot.curves])

        for index in range(number_of_rows * number_of_columns):
            axes_list.append(figure.add_subplot(number_of_rows, number_of_columns, index + 1))

        for curve in self.displayed_plot.curves:
            add_to_plot(curve)

        #make sure the titles of 'subplots' do not overlap with the axis labels of the 'main plot'
        figure.subplots_adjust(hspace=0.3)

        #TODO: add multiple results support to fit in curve.results:
        #get the fit_function results to display
        fit_function_str = self.GetStringFromConfig('results', 'show_results', 'fit_function')
        self.panelResults.ClearResults()
        plot = self.GetActivePlot()
        if plot is not None:
            if plot.results.has_key(fit_function_str):
                for curve in plot.results[fit_function_str].results:
                    add_to_plot(curve)
                self.panelResults.DisplayResults(plot.results[fit_function_str])
            else:
                self.panelResults.ClearResults()

        figure.canvas.draw()

        for axes in axes_list:
            #TODO: add legend as global option or per graph option
            #axes.legend()
            axes.figure.canvas.draw()


if __name__ == '__main__':

    ## now, silence a deprecation warning for py2.3
    import warnings
    warnings.filterwarnings("ignore", "integer", DeprecationWarning, "wxPython.gdi")

    redirect = True
    if __debug__:
        redirect=False

    app = Hooke(redirect=redirect)

    app.MainLoop()


