# Copyright

"""Selection dialog.
"""

from os import remove
import types

import wx

from ....util.callback import callback, in_callback


class Selection (wx.Dialog):
    """A selection dialog box.

    Lists options and two buttons.  The first button is setup by the
    caller.  The second button cancels the dialog.

    The button appearance can be specified by selecting one of the
    `standard wx IDs`_.

    .. _standard wx IDs:
      http://docs.wxwidgets.org/stable/wx_stdevtid.html#stdevtid
    """
    def __init__(self, options, message, button_id, callbacks=None,
                 default=None, selection_style='single', *args, **kwargs):
        super(Selection, self).__init__(*args, **kwargs)

        self._options = options
        if callbacks == None:
            callbacks = {}
        self._callbacks = callbacks
        self._selection_style = selection_style

        self._c = {
            'text': wx.StaticText(
                parent=self, label=message, style=wx.ALIGN_CENTRE),
            'button': wx.Button(parent=self, id=button_id),
            'cancel': wx.Button(self, wx.ID_CANCEL),
            }
        size = wx.Size(175, 200)
        if selection_style == 'single':
            self._c['listbox'] = wx.ListBox(
                parent=self, size=size, choices=options)
            if default != None:
                self._c['listbox'].SetSelection(default)
        else:
            assert selection_style == 'multiple', selection_style
            self._c['listbox'] = wx.CheckListBox(
                parent=self, size=size, choices=options)
            if default != None:
                self._c['listbox'].Check(default)
        self.Bind(wx.EVT_BUTTON, self.button, self._c['button'])
        self.Bind(wx.EVT_BUTTON, self.cancel, self._c['cancel'])

        b = wx.BoxSizer(wx.HORIZONTAL)
        self._add(b, 'button')
        self._add(b, 'cancel')
        v = wx.BoxSizer(wx.VERTICAL)
        self._add(v, 'text')
        self._add(v, 'listbox')
        self._add(v, wx.StaticLine(
                parent=self, size=(20,-1), style=wx.LI_HORIZONTAL),
                  flag=wx.GROW)
        self._add(v, b)
        self.SetSizer(v)
        v.Fit(self)

    def _add(self, sizer, item,
            flag=wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL,
            border=5):
        kwargs = {'flag':flag, 'border':border}
        if isinstance(item, types.StringTypes):
            item = self._c[item]
        kwargs['item'] = item # window
        sizer.Add(**kwargs)

    @callback
    def cancel(self, event):
        """Close the dialog.
        """
        self.EndModal(wx.ID_CANCEL)

    def button(self, event):
        """Call ._button_callback() and close the dialog.
        """
        if self._selection_style == 'single':
            selected = self._c['listbox'].GetSelection()
        else:
            assert self._selection_style == 'multiple', self._selection_style
            selected = self._c['listbox'].GetChecked()
        self.selected = selected
        in_callback(self, options=self._options, selected=selected)
        self.EndModal(wx.ID_CLOSE)
