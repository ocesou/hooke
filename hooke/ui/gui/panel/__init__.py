# Copyright

"""The `panel` module provides optional submodules that add GUI panels.
"""

from ....util.pluggable import IsSubclass, construct_odict


PANEL_MODULES = [
    'commands',
    'note',
#    'notebook',
    'output',
    'playlist',
    'plot',
    'propertyeditor',
#    'results',
#    'selection',
#    'welcome',
    ]
"""List of panel modules.  TODO: autodiscovery
"""

class Panel (object):
    """Base class for Hooke GUI panels.
    
    :attr:`name` identifies the request type and should match the
    module name.
    """
    def __init__(self, name=None, callbacks=None, **kwargs):
        super(Panel, self).__init__(**kwargs)
        self.name = name
        self.managed_name = name.capitalize()
        self._hooke_frame = kwargs.get('parent', None)
        if callbacks == None:
            callbacks = {}
        self._callbacks = callbacks


PANELS = construct_odict(
    this_modname=__name__,
    submodnames=PANEL_MODULES,
    class_selector=IsSubclass(Panel, blacklist=[Panel]),
    instantiate=False)
""":class:`hooke.compat.odict.odict` of :class:`Panel`
instances keyed by `.name`.
"""
