#!/usr/bin/env python

"""Commands and settings panel for Hooke.

This panel handles command generation of
:class:`hooke.engine.CommandMessage`\s for all of the commands that
don't have panels of their own.  Actually it can generate
:class:`hooke.engine.CommandMessage`\s for those as well, but the
command-specific panel will probably have a nicer interface.

# TODO: command arguments.
"""

import types

import wx

from ....util.callback import callback, in_callback
from . import Panel


class Tree (wx.TreeCtrl):
    """The main widget of :class:`CommandsPanel`.

    `callbacks` is shared with the parent :class:`Commands`.
    """
    def __init__(self, commands, selected, callbacks, *args, **kwargs):
        super(Tree, self).__init__(*args, **kwargs)
        imglist = wx.ImageList(width=16, height=16, mask=True, initialCount=2)
        imglist.Add(wx.ArtProvider.GetBitmap(
                wx.ART_FOLDER, wx.ART_OTHER, wx.Size(16, 16)))
        imglist.Add(wx.ArtProvider.GetBitmap(
                wx.ART_EXECUTABLE_FILE, wx.ART_OTHER, wx.Size(16, 16)))
        self.AssignImageList(imglist)
        self.image = {
            'root': 0,
            'plugin': 0,
            'command': 1,
            }
        self._c = {
            'root': self.AddRoot(
                text='Commands and Settings', image=self.image['root']),
            }
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_selection_changed)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_execute)
        self.Bind(wx.EVT_MOTION, self._on_motion)

        self._callbacks = callbacks
        self._setup_commands(commands, selected)
        self._last_tooltip = None

    def _setup_commands(self, commands, selected):
        self._plugins = {}    # {name: hooke.plugin.Plugin()}
        self._commands = {}   # {name: hooke.command.Command()}

        # In both of the following dicts, command names are
        # (plugin.name, command.name) to avoid cross-plugin
        # collisions.  See ._is_command().
        self._id_for_name = {}  # {name: id}
        self._name_for_id = {}  # {id: name}

        selected = None
        plugins = sorted(set([c.plugin for c in commands]),
                         key=lambda p:p.name)
        for plugin in plugins:
            self._plugins[plugin.name] = plugin
            _id = self.AppendItem(
                parent=self._c['root'],
                text=plugin.name,
                image=self.image['plugin'])
            self._id_for_name[plugin.name] = _id
            self._name_for_id[_id] = plugin.name
        for command in sorted(commands, key=lambda c:c.name):
            name = (command.plugin.name, command.name)
            self._commands[name] = command
            _id = self.AppendItem(
                parent=self._id_for_name[command.plugin.name],
                text=command.name,
                image=self.image['command'])
            self._id_for_name[name] = _id
            self._name_for_id[_id] = name
            if command.name == selected:
                selected = _id

        #for plugin in self._plugins.values():
        #    self.Expand(self._id_for_name[plugin.name])
        # make sure the selected command/plugin is visible in the tree
        if selected is not None:
            self.SelectItem(selected, True)
            self.EnsureVisible(selected)

    def _is_command(self, name):  # name from ._id_for_name / ._name_for_id
        """Return `True` if `name` corresponds to a :class:`hooke.command.Command`.
        """
        # Plugin names are strings, Command names are tuples.
        # See ._setup_commands().
        return not isinstance(name, types.StringTypes)

    def _canonical_id(self, _id):
        """Return a canonical form of `_id` suitable for accessing `._name_for_id`.

        For some reason, `.GetSelection()`, etc. return items that
        hash differently than the original `.AppendItem()`-returned
        IDs.  This means that `._name_for_id[self.GetSelection()]`
        will raise `KeyError`, even if there is an id `X` in
        `._name_for_id` for which `X == self.GetSelection()` will
        return `True`.  This method "canonicalizes" IDs so that the
        hashing is consistent.
        """
        for c_id in self._name_for_id.keys():
            if c_id == _id:
                return c_id
        raise KeyError(_id)

    def _on_selection_changed(self, event):
        active_id = event.GetItem()
        selected_id = self.GetSelection()
        name = self._name_for_id[self._canonical_id(selected_id)]
        if self._is_command(name):
            self.select_command(self._commands[name])
        else:
            self.select_plugin(self._plugins[name])

    def _on_execute(self, event):
        self.execute()

    def _on_motion(self, event):
        """Enable tooltips.
        """
        hit_id,hit_flags = self.HitTest(event.GetPosition())
        try:
            hit_id = self._canonical_id(hit_id)
        except KeyError:
            hit_id = None
        if hit_id == None:
            msg = ''
        else:
            name = self._name_for_id[hit_id]
            if self._is_command(name):
                msg = self._commands[name].help()
            else:
                msg = ''  # self._plugins[name].help() TODO: Plugin.help method
        if msg != self._last_tooltip:
            self._last_tooltip = msg
            event.GetEventObject().SetToolTipString(msg)

    def select_plugin(self, plugin):
        in_callback(self, plugin)

    def select_command(self, command):
        in_callback(self, command)

    def execute(self):
        _id = self.GetSelection()
        name = self._name_for_id[self._canonical_id(_id)]
        if self._is_command(name):
            command = self._commands[name]
            in_callback(self, command)


class CommandsPanel (Panel, wx.Panel):
    """UI for selecting from available commands.

    `callbacks` is shared with the underlying :class:`Tree`.
    """
    def __init__(self, callbacks=None, commands=None, selected=None, **kwargs):
        super(CommandsPanel, self).__init__(
            name='commands', callbacks=callbacks, **kwargs)
        self._c = {
            'tree': Tree(
                commands=commands,
                selected=selected,
                callbacks=callbacks,
                parent=self,
                pos=wx.Point(0, 0),
                size=wx.Size(160, 250),
                style=wx.TR_DEFAULT_STYLE|wx.NO_BORDER|wx.TR_HIDE_ROOT),
            'execute': wx.Button(self, label='Execute'),
            }
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._c['execute'], 0, wx.EXPAND)
        sizer.Add(self._c['tree'], 1, wx.EXPAND)
        # Put 'tree' second because its min size may be large enough
        # to push the button out of view.
        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Bind(wx.EVT_BUTTON, self._on_execute_button)

    def _on_execute_button(self, event):
        self._c['tree'].execute()
