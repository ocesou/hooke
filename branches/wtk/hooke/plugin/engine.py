# Copyright

"""The `engine` module provides :class:`EnginePlugin` and several
associated :class:`hooke.command.Command`\s for basic
:class:`~hooke.hooke.Hooke` and :class:`~hooke.engine.CommandEngine`
interaction.
"""

from ..command import CommandExit, Exit, Command, Argument
from ..interaction import BooleanRequest
from . import Builtin


class EnginePlugin (Builtin):
    def __init__(self):
        super(EnginePlugin, self).__init__(name='engine')
        self._commands = [
            ExitCommand(self), HelpCommand(self)]


class ExitCommand (Command):
    """Exit Hooke cleanly.
    """
    def __init__(self, plugin):
        super(ExitCommand, self).__init__(
            name='exit',
            arguments = [
                Argument(name='force', type='bool', default=False,
                         help="""
Exit without prompting the user.  Use if you save often or don't make
typing mistakes ;).
""".strip()),
                ],
             help=self.__doc__, plugin=plugin)

    def _run(self, hooke, inqueue, outqueue, params):
        """Exit Hooke, prompting if there are unsaved changes.
        """
        _exit = True
        if params['force'] == False:
            not_saved = [p.name for p in hooke.playlists
                         if p.is_saved() == False]
            msg = 'Exit?'
            default = True
            if len(not_saved) > 0:
                msg = 'Unsaved playlists (%s).  %s' \
                    % (', '.join([str(p) for p in not_saved]), msg)
                default = False
            outqueue.put(BooleanRequest(msg, default))
            result = inqueue.get()
            assert result.type == 'boolean'
            _exit = result.value
            if _exit == False:
                return
            # TODO: check for unsaved config file
        if _exit == True:
            raise Exit()


class HelpCommand (Command):
    """Called with an argument, prints that command's documentation.

    With no argument, lists all available help topics as well as any
    undocumented commands.
    """
    def __init__(self, plugin):
        super(HelpCommand, self).__init__(
            name='help', help=self.__doc__, plugin=plugin)
        # We set .arguments now (vs. using th arguments option to __init__),
        # to overwrite the default help argument.  We don't override
        # :meth:`cmd.Cmd.do_help`, so `help --help` is not a valid command.
        self.arguments = [
            Argument(name='command', type='string', optional=True,
                     help='The name of the command you want help with.')
            ]

    def _run(self, hooke, inqueue, outqueue, params):
        if params['command'] == None:
            outqueue.put(sorted([c.name for c in hooke.commands]))
        else:
            outqueue.put(hooke.command_by_name[params['command']].help())
