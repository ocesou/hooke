# Copyright (C) 2010 Massimo Sandal <devicerandom@gmail.com>
#                    W. Trevor King <wking@drexel.edu>
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

"""Playlist panel for Hooke.

Provides a nice GUI interface to the
:class:`~hooke.plugin.playlist.PlaylistPlugin`.
"""

import logging
import types

import wx

from ....util.callback import callback, in_callback
from . import Panel


class Menu (wx.Menu):
    """Popup menu for selecting playlist :class:`Tree` actions.
    """
    def __init__(self, on_delete, *args, **kwargs):
        super(Menu, self).__init__(*args, **kwargs)
        self._c = {
            'delete': self.Append(id=wx.ID_ANY, text='Delete'),
            }
        self.Bind(wx.EVT_MENU, on_delete)


class Tree (wx.TreeCtrl):
    """:class:`wx.TreeCtrl` subclass handling playlist and curve selection.
    """
    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger('hooke')
        self._panel = kwargs['parent']
        self._callbacks = self._panel._callbacks # TODO: CallbackClass.set_callback{,s}()
        super(Tree, self).__init__(*args, **kwargs)
        imglist = wx.ImageList(width=16, height=16, mask=True, initialCount=2)
        imglist.Add(wx.ArtProvider.GetBitmap(
                wx.ART_FOLDER, wx.ART_OTHER, wx.Size(16, 16)))
        imglist.Add(wx.ArtProvider.GetBitmap(
                wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16, 16)))
        self.AssignImageList(imglist)
        self.image = {
            'root': 0,
            'playlist': 0,
            'curve': 1,
            }
        self._c = {
            'menu': Menu(self._on_delete),
            'root': self.AddRoot(text='Playlists', image=self.image['root'])
            }
        self.Bind(wx.EVT_RIGHT_DOWN, self._on_context_menu)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_select)

        self._setup_playlists()

    def _setup_playlists(self):
        self._playlists = {}    # {name: hooke.playlist.Playlist()}

        # In both of the following dicts, curve names are
        # (playlist.name, curve.name) to avoid cross-playlist
        # collisions.  See ._is_curve().
        self._id_for_name = {}  # {name: id}
        self._name_for_id = {}  # {id: name}

    def _is_curve(self, name):  # name from ._id_for_name / ._name_for_id
        """Return `True` if `name` corresponds to a :class:`hooke.curve.Curve`.
        """
        # Playlist names are strings, Curve names are tuples.
        # See ._setup_playlists().
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


    # Context menu

    def _on_context_menu(self, event):
        """Launch a popup :class:`Menu` with per-playlist/curve activities.
        """
        hit_id,hit_flags = self.HitTest(event.GetPosition())
        if (hit_flags & wx.TREE_HITTEST_ONITEM) != 0:
            self._hit_id = self._canonical_id(hit_id)  # store for callbacks
            menu = Menu(self._on_delete)
            self.PopupMenu(menu, event.GetPosition())
            menu.Destroy()

    # Add
    #   add_* called directly by HookeFrame
    #   _add_* called on every addition

    def add_playlist(self, playlist):
        """Add a :class:`hooke.playlist.Playlist` to the tree.

        Calls :meth:`_add_playlist` and triggers a callback.
        """
        self._add_playlist(playlist)
        in_callback(self, playlist)

    def _add_playlist(self, playlist):
        """Add a class:`hooke.playlist.Playlist` to the tree.

        No callback triggered.
        """
        if playlist.name not in self._playlists:
            pass
        else:
            raise ValueError('duplicate playlist: %s' % playlist.name)
        self._playlists[playlist.name] = playlist
        p_id = self.AppendItem(
            parent=self._c['root'],
            text=self._panel._hooke_frame._file_name(playlist.name),
            image=self.image['playlist'])
        self._id_for_name[playlist.name] = p_id
        self._name_for_id[p_id] = playlist.name
        for curve in playlist:
            self._add_curve(playlist.name, curve)

    def add_curve(self, playlist_name, curve):
        """Add a :class:`hooke.curve.Curve` to a curently loaded playlist.

        Calls :meth:`_add_curve` and triggers a callback.
        """
        self._add_curve(playlist_name, curve)
        playlist = self._playlists[playlist_name]
        in_callback(self, playlist, curve)

    def _add_curve(self, playlist_name, curve):
        """Add a class:`hooke.curve.Curve` to the tree.

        No callback triggered.
        """
        p = self._playlists[playlist_name]
        if curve not in p:
            p.append(curve)
        c_id = self.AppendItem(
            parent=self._id_for_name[playlist_name],
            text=self._panel._hooke_frame._file_name(curve.name),
            image=self.image['curve'])
        self._id_for_name[(p.name, curve.name)] = c_id
        self._name_for_id[c_id] = (p.name, curve.name)

    @callback
    def generate_new_playlist(self):
        pass  # TODO

    def _GetUniquePlaylistName(self, name):  # TODO
        playlist_name = name
        count = 1
        while playlist_name in self.playlists:
            playlist_name = ''.join([name, str(count)])
            count += 1
        return playlist_name

    # Delete
    #   delete_* called by _on_delete handler (user click) or HookeFrame
    #   _delete_* called on every deletion

    def _on_delete(self, event):
        """Handler for :class:`Menu`'s `Delete` button.

        Determines the clicked item and calls the appropriate
        `.delete_*()` method on it.
        """
        #if hasattr(self, '_hit_id'):  # called via ._c['menu']
        _id = self._hit_id
        del(self._hit_id)
        name = self._name_for_id[_id]
        if self._is_curve(name):
            self.delete_curve(playlist_name=name[0], name=name[1])
        else:
            self.delete_playlist(name)

    def delete_playlist(self, name):
        """Delete a :class:`hooke.playlist.Playlist` by name.

        Called by the :meth:`_on_delete` handler.

        Removes the playlist and its curves from the tree, then calls
        :meth:`_delete_playlist`.
        """
        _id = self._id_for_name[name]
        self.Delete(_id)
        playlist = self._playlists[name]
        self._delete_playlist(playlist)
        in_callback(self, playlist)

    def _delete_playlist(self, playlist):
        """Adjust name/id caches for the playlist and its curves.

        Called on *every* playlist deletion.
        """
        self._playlists.pop(playlist.name)
        _id = self._id_for_name.pop(playlist.name)
        del(self._name_for_id[_id])
        for curve in playlist:
            self._delete_curve(playlist, curve)
        in_callback(self, playlist)

    def delete_curve(self, playlist_name, name):
        """Delete a :class:`hooke.curve.Curve` by name.

        Called by the :meth:`_on_delete` handler.

        Removes the curve from the tree, then calls
        :meth:`_delete_curve`.
        """
        _id = self._id_for_name[(playlist_name, name)]
        self.Delete(_id)
        playlist = self._playlists[playlist_name]
        curve = None
        for i,c in enumerate(playlist):
            if c.name == name:
                curve = c
                break
        self._delete_curve(playlist, curve)
        in_callback(self, playlist, curve)

    def _delete_curve(self, playlist, curve):
        """Adjust name/id caches.

        Called on _every_ curve deletion.
        """
        _id = self._id_for_name.pop((playlist.name, curve.name))
        del(self._name_for_id[_id])
        in_callback(self, playlist, curve)

    # Get selection

    def get_selected_playlist(self):
        """Return the selected :class:`hooke.playlist.Playlist`.
        """
        _id = self.GetSelection()
        try:
            _id = self._canonical_id(_id)
        except KeyError:  # no playlist selected
            return None
        name = self._name_for_id[_id]
        if self._is_curve(name):
            name = name[0]
        return self._playlists[name]

    def get_selected_curve(self):
        """Return the selected :class:`hooke.curve.Curve`.
        """
        _id = self.GetSelection()
        name = self._name_for_id[self._canonical_id(_id)]
        if self._is_curve(name):
            p_name,c_name = name
            playlist = self._playlists[p_name]
            c = playlist.current()
            assert c.name == c_name, '%s != %s' % (c.name, c_name)
        else:
            playlist = self._playlists[name]
        return playlist.current()

    # Set selection (via user interaction with this panel)
    #
    # These are hooks for HookeFrame callbacks which will send
    # the results back via 'get curve' calling 'set_selected_curve'.

    def _on_select(self, event):
        """Select the clicked-on curve/playlist.
        """
        _id = self.GetSelection()
        name = self._name_for_id[self._canonical_id(_id)]
        if self._is_curve(name):
            p_name,c_name = name
            self._on_set_selected_curve(p_name, c_name)
        else:
            self._on_set_selected_playlist(name)

    def _on_set_selected_playlist(self, name):
        self.log.debug('playlist tree selecting playlist %s' % name)
        in_callback(self, self._playlists[name])

    def _on_set_selected_curve(self, playlist_name, name):
        self.log.debug('playlist tree selecting curve %s in %s'
                       % (name, playlist_name))
        playlist = self._playlists[playlist_name]
        curve = None
        for i,c in enumerate(playlist):
            if c.name == name:
                curve = c
                break
        if curve == None:
            raise ValueError(name)
        in_callback(self, playlist, curve)
        
    # Set selection (from the HookeFrame)

    def set_selected_curve(self, playlist, curve):
        """Make the curve the playlist's current curve.
        """
        self.log.debug('playlist tree expanding %s' % playlist.name)
        self.Expand(self._id_for_name[playlist.name])
        self.Unbind(wx.EVT_TREE_SEL_CHANGED)
        self.log.debug('playlist tree selecting %s' % curve.name)
        self.SelectItem(self._id_for_name[(playlist.name, curve.name)])
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_select)

    def update_playlist(self, playlist):
        """Absorb changed `.index()`, etc.
        """
        self._playlists[playlist.name] = playlist

    def is_playlist_loaded(self, playlist):
        """Return `True` if a playlist is loaded, `False` otherwise.
        """
        return playlist.name in self._playlists


class Playlist (Panel, wx.Panel):
    """:class:`wx.Panel` subclass wrapper for :class:`Tree`.
    """
    def __init__(self, callbacks=None, **kwargs):
        # Use the WANTS_CHARS style so the panel doesn't eat the Return key.
        super(Playlist, self).__init__(
            name='playlist', callbacks=callbacks, **kwargs)
        self._c = {
            'tree': Tree(
                parent=self,
                size=wx.Size(160, 250),
                style=wx.TR_DEFAULT_STYLE | wx.NO_BORDER | wx.TR_HIDE_ROOT),
            }

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._c['tree'], 1, wx.EXPAND)
        self.SetSizer(sizer)
        sizer.Fit(self)

        # Expose all Tree's public curve/playlist methods directly.
        # Following DRY and the LoD.
        for attribute_name in dir(self._c['tree']):
            if (attribute_name.startswith('_')
                or ('playlist' not in attribute_name
                    and 'curve' not in attribute_name)):
                continue  # not an attribute we're interested in
            attr = getattr(self._c['tree'], attribute_name)
            if hasattr(attr, '__call__'):  # attr is a function / method
                setattr(self, attribute_name, attr)  # expose it
