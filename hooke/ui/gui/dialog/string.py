class StringPopup (wx.Dialog):

        self._c = {
            'text': wx.StaticText(
                parent=self, label=message, style=wx.ALIGN_CENTRE),
            'button': wx.Button(parent=self, id=button_id),
            'cancel': wx.Button(self, wx.ID_CANCEL),
            }
        size = wx.Size(175, 200)
        if selection_style == 'single':
            self._c['listbox'] = wx.ListBox(
                parent=self, size=size, list=options)
            if default != None:
                self._c['listbox'].SetSelection(default)
        else:
            assert selection_style == 'multiple', selection_style
            self._c['listbox'] = wx.CheckListBox(
                parent=self, size=size, list=options)
            if default != None:
                self._c['listbox'].Check(default)
        self.Bind(wx.EVT_BUTTON, self.button, self._c['button'])
        self.Bind(wx.EVT_BUTTON, self.cancel, self._c['cancel'])

        border_width = 5

        b = wx.BoxSizer(wx.HORIZONTAL)
        b.Add(window=self._c['button'],
              flag=wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL,
              border=border_width)
        b.Add(window=self._c['cancel'],
              flag=wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL,
              border=border_width)

        v = wx.BoxSizer(wx.VERTICAL)
        v.Add(window=self._c['text'],
              flag=wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL,
              border=border_width)
        v.Add(window=self._c['listbox'],
              proportion=1,
              flag=wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL,
              border=border_width)
        v.Add(window=wx.StaticLine(
                parent=self, size=(20,-1), style=wx.LI_HORIZONTAL),
              flag=wx.GROW,
              border=border_width)
        v.Add(window=b,
              flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALL,
              border=border_width)
        self.SetSizer(v)
        v.Fit(self)
