# Copyright

from ....util.pluggable import IsSubclass, construct_graph


HANDLER_MODULES = [
    'boolean',
    'float',
#    'int'
#    'point',
    'selection',
    'string'
    ]
"""List of handler modules.  TODO: autodiscovery
"""

class Handler (object):
    """Base class for :class:`~hooke.interaction.Request` handlers.
    
    :attr:`name` identifies the request type and should match the
    module name.
    """
    def __init__(self, name):
        self.name = name

    def run(self, hooke_frame, msg):
        raise NotImplemented

    def _cancel(self, *args, **kwargs):
        # TODO: somehow abort the running command


HANDLERS = construct_odict(
    this_modname=__name__,
    submodnames=USER_INTERFACE_MODULES,
    class_selector=IsSubclass(UserInterface, blacklist=[UserInterface]))
""":class:`hooke.compat.odict.odict` of :class:`Handler`
instances keyed by `.name`.
"""
