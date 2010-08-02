# Copyright

"""Define :class:`SelectionHandler` to handle
:class:`~hooke.interaction.SelectionRequest`\s.
"""

import wx

from ..dialog.selection import SelectionDialog
from . import Handler


class SelectionHandler (Handler):
    def __init__(self):
        super(StringHandler, self).__init__(name='selection')

    def run(self, hooke_frame, msg):
        self._canceled = True
        while self._canceled:
            s = SelectionDialog(
                options=msg.options,
                message=msg.msg,
                button_id=wxID_OK,
                callbacks={
                    'button': self._selection,
                    },
                default=msg.default,
                selection_style='single',
                parent=self,
                label='Selection handler',
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER),
            )
        return self._selected

    def _selection(self, _class, method, options, selected):
        self._selected = selected
        self._canceled = False
