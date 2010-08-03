# Copyright (C) 2010 W. Trevor King <wking@drexel.edu>
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

"""Defines :class:`CommandLine` for driving Hooke from the command
line.
"""

import codecs
import cmd
import optparse
import readline # including readline makes cmd.Cmd.cmdloop() smarter
import shlex

from ..command import CommandExit, Exit, Command, Argument, StoreValue
from ..interaction import Request, BooleanRequest, ReloadUserInterfaceConfig
from ..ui import UserInterface, CommandMessage
from ..util.encoding import get_input_encoding, get_output_encoding


# Define a few helper classes.

class Default (object):
    """Marker for options not given on the command line.
    """
    pass

class CommandLineParser (optparse.OptionParser):
    """Implement a command line syntax for a
    :class:`hooke.command.Command`.
    """
    def __init__(self, command, name_fn):
        optparse.OptionParser.__init__(self, prog=name_fn(command.name))
        self.command = command
        self.command_opts = []
        self.command_args = []
        for a in command.arguments:
            if a.name == 'help':
                continue # 'help' is a default OptionParser option
            if a.optional == True:
                name = name_fn(a.name)
                self.add_option(
                    '--%s' % name, dest=name, default=Default)
                self.command_opts.append(a)
            else:
                self.command_args.append(a)
        infinite_counters = [a for a in self.command_args if a.count == -1]
        assert len(infinite_counters) <= 1, \
            'Multiple infinite counts for %s: %s\nNeed a better CommandLineParser implementation.' \
            % (command.name, ', '.join([a.name for a in infinite_counters]))
        if len(infinite_counters) == 1: # move the big counter to the end.
            infinite_counter = infinite_counters[0]
            self.command_args.remove(infinite_counter)
            self.command_args.append(infinite_counter)

    def exit(self, status=0, msg=None):
        """Override :meth:`optparse.OptionParser.exit` which calls
        :func:`sys.exit`.
        """
        if msg:
            raise optparse.OptParseError(msg)
        raise optparse.OptParseError('OptParse EXIT')

class CommandMethod (object):
    """Base class for method replacer.

    The .__call__ methods of `CommandMethod` subclasses functions will
    provide the `do_*`, `help_*`, and `complete_*` methods of
    :class:`HookeCmd`.
    """
    def __init__(self, cmd, command, name_fn):
        self.cmd = cmd
        self.command = command
        self.name_fn = name_fn

    def __call__(self, *args, **kwargs):
        raise NotImplementedError

class DoCommand (CommandMethod):
    def __init__(self, *args, **kwargs):
        super(DoCommand, self).__init__(*args, **kwargs)
        self.parser = CommandLineParser(self.command, self.name_fn)

    def __call__(self, args):
        try:
            args = self._parse_args(args)
        except optparse.OptParseError, e:
            self.cmd.stdout.write(str(e).lstrip()+'\n')
            self.cmd.stdout.write('Failure\n')
            return
        self.cmd.inqueue.put(CommandMessage(self.command, args))
        while True:
            msg = self.cmd.outqueue.get()
            if isinstance(msg, Exit):
                return True
            elif isinstance(msg, CommandExit):
                self.cmd.stdout.write(msg.__class__.__name__+'\n')
                self.cmd.stdout.write(str(msg).rstrip()+'\n')
                break
            elif isinstance(msg, ReloadUserInterfaceConfig):
                self.cmd.ui.reload_config(msg.config)
                continue
            elif isinstance(msg, Request):
                self._handle_request(msg)
                continue
            self.cmd.stdout.write(str(msg).rstrip()+'\n')

    def _parse_args(self, args):
        options,args = self.parser.parse_args(args)
        self._check_argument_length_bounds(args)
        params = {}
        for argument in self.parser.command_opts:
            value = getattr(options, self.name_fn(argument.name))
            if value != Default:
                params[argument.name] = value
        arg_index = 0
        for argument in self.parser.command_args:
            if argument.count == 1:
                params[argument.name] = args[arg_index]
            elif argument.count > 1:
                params[argument.name] = \
                    args[arg_index:arg_index+argument.count]
            else: # argument.count == -1:
                params[argument.name] = args[arg_index:]
            arg_index += argument.count
        return params

    def _check_argument_length_bounds(self, arguments):
        """Check that there are an appropriate number of arguments in
        `args`.

        If not, raise optparse.OptParseError().
        """
        min_args = 0
        max_args = 0
        for argument in self.parser.command_args:
            if argument.optional == False and argument.count > 0:
                min_args += argument.count
            if max_args >= 0: # otherwise already infinite
                if argument.count == -1:
                    max_args = -1
                else:
                    max_args += argument.count
        if len(arguments) < min_args \
                or (max_args >= 0 and len(arguments) > max_args):
            if min_args == max_args:
                target_string = str(min_args)
            elif max_args == -1:
                target_string = 'more than %d' % min_args
            else:
                target_string = '%d to %d' % (min_args, max_args)
            raise optparse.OptParseError(
                '%d arguments given, but %s takes %s'
                % (len(arguments), self.name_fn(self.command.name),
                   target_string))

    def _handle_request(self, msg):
        """Repeatedly try to get a response to `msg`.
        """
        prompt = getattr(self, '_%s_request_prompt' % msg.type, None)
        if prompt == None:
            raise NotImplementedError('_%s_request_prompt' % msg.type)
        prompt_string = prompt(msg)
        parser = getattr(self, '_%s_request_parser' % msg.type, None)
        if parser == None:
            raise NotImplementedError('_%s_request_parser' % msg.type)
        error = None
        while True:
            if error != None:
                self.cmd.stdout.write(''.join([
                        error.__class__.__name__, ': ', str(error), '\n']))
            self.cmd.stdout.write(prompt_string)
            value = parser(msg, self.cmd.stdin.readline())
            try:
                response = msg.response(value)
                break
            except ValueError, error:
                continue
        self.cmd.inqueue.put(response)

    def _boolean_request_prompt(self, msg):
        if msg.default == True:
            yn = ' [Y/n] '
        else:
            yn = ' [y/N] '
        return msg.msg + yn

    def _boolean_request_parser(self, msg, response):
        value = response.strip().lower()
        if value.startswith('y'):
            value = True
        elif value.startswith('n'):
            value = False
        elif len(value) == 0:
            value = msg.default
        return value

    def _string_request_prompt(self, msg):
        if msg.default == None:
            d = ' '
        else:
            d = ' [%s] ' % msg.default
        return msg.msg + d

    def _string_request_parser(self, msg, response):
        return response.strip()

    def _float_request_prompt(self, msg):
        return self._string_request_prompt(msg)

    def _float_request_parser(self, msg, resposne):
        return float(response)

    def _selection_request_prompt(self, msg):
        options = []
        for i,option in enumerate(msg.options):
            options.append('   %d) %s' % (i,option))
        options = ''.join(options)
        if msg.default == None:
            prompt = '? '
        else:
            prompt = '? [%d] ' % msg.default
        return '\n'.join([msg,options,prompt])
    
    def _selection_request_parser(self, msg, response):
        return int(response)


class HelpCommand (CommandMethod):
    def __init__(self, *args, **kwargs):
        super(HelpCommand, self).__init__(*args, **kwargs)
        self.parser = CommandLineParser(self.command, self.name_fn)

    def __call__(self):
        blocks = [self.command.help(name_fn=self.name_fn),
                  '----',
                  'Usage: ' + self._usage_string(),
                  '']
        self.cmd.stdout.write('\n'.join(blocks))

    def _message(self):
        return self.command.help(name_fn=self.name_fn)

    def _usage_string(self):
        if len(self.parser.command_opts) == 0:
            options_string = ''
        else:
            options_string = '[options]'
        arg_string = ' '.join(
            [self.name_fn(arg.name) for arg in self.parser.command_args])
        return ' '.join([x for x in [self.parser.prog,
                                     options_string,
                                     arg_string]
                         if x != ''])

class CompleteCommand (CommandMethod):
    def __call__(self, text, line, begidx, endidx):
        pass


# Define some additional commands

class LocalHelpCommand (Command):
    """Called with an argument, prints that command's documentation.

    With no argument, lists all available help topics as well as any
    undocumented commands.
    """
    def __init__(self):
        super(LocalHelpCommand, self).__init__(name='help', help=self.__doc__)
        # We set .arguments now (vs. using th arguments option to __init__),
        # to overwrite the default help argument.  We don't override
        # :meth:`cmd.Cmd.do_help`, so `help --help` is not a valid command.
        self.arguments = [
            Argument(name='command', type='string', optional=True,
                     help='The name of the command you want help with.')
            ]

    def _run(self, hooke, inqueue, outqueue, params):
        raise NotImplementedError # cmd.Cmd already implements .do_help()

class LocalExitCommand (Command):
    """Exit Hooke cleanly.
    """
    def __init__(self):
        super(LocalExitCommand, self).__init__(
            name='exit', aliases=['quit', 'EOF'], help=self.__doc__,
            arguments = [
                Argument(name='force', type='bool', default=False,
                         help="""
Exit without prompting the user.  Use if you save often or don't make
typing mistakes ;).
""".strip()),
                ])

    def _run(self, hooke, inqueue, outqueue, params):
        """The guts of the `do_exit/_quit/_EOF` commands.

        A `True` return stops :meth:`.cmdloop` execution.
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
        if _exit == True:
            raise Exit()


# Now onto the main attraction.

class HookeCmd (cmd.Cmd):
    def __init__(self, ui, commands, inqueue, outqueue):
        cmd.Cmd.__init__(self)
        self.ui = ui
        self.commands = commands
        self.local_commands = [LocalExitCommand(), LocalHelpCommand()]
        self.prompt = 'hooke> '
        self._add_command_methods()
        self.inqueue = inqueue
        self.outqueue = outqueue

    def _name_fn(self, name):
        return name.replace(' ', '_')

    def _add_command_methods(self):
        for command in self.commands + self.local_commands:
            for name in [command.name] + command.aliases:
                name = self._name_fn(name)
                setattr(self.__class__, 'help_%s' % name,
                        HelpCommand(self, command, self._name_fn))
                if name != 'help':
                    setattr(self.__class__, 'do_%s' % name,
                            DoCommand(self, command, self._name_fn))
                    setattr(self.__class__, 'complete_%s' % name,
                            CompleteCommand(self, command, self._name_fn))

    def parseline(self, line):
        """Override Cmd.parseline to use shlex.split.

        Notes
        -----
        This allows us to handle comments cleanly.  With the default
        Cmd implementation, a pure comment line will call the .default
        error message.

        Since we use shlex to strip comments, we return a list of
        split arguments rather than the raw argument string.
        """
        line = line.strip()
        argv = shlex.split(line, comments=True, posix=True)
        if len(argv) == 0:
            return None, None, '' # return an empty line
        elif argv[0] == '?':
            argv[0] = 'help'
        elif argv[0] == '!':
            argv[0] = 'system'
        return argv[0], argv[1:], line

    def do_help(self, arg):
        """Wrap Cmd.do_help to handle our .parseline argument list.
        """
        if len(arg) == 0:
            return cmd.Cmd.do_help(self, '')
        return cmd.Cmd.do_help(self, arg[0])

    def empytline(self):
        """Override Cmd.emptyline to not do anything.

        Repeating the last non-empty command seems unwise.  Explicit
        is better than implicit.
        """
        pass

class CommandLine (UserInterface):
    """Command line interface.  Simple and powerful.
    """
    def __init__(self):
        super(CommandLine, self).__init__(name='command line')

    def _cmd(self, commands, ui_to_command_queue, command_to_ui_queue):
        cmd = HookeCmd(self, commands,
                       inqueue=ui_to_command_queue,
                       outqueue=command_to_ui_queue)
        #cmd.stdin = codecs.getreader(get_input_encoding())(cmd.stdin)
        cmd.stdout = codecs.getwriter(get_output_encoding())(cmd.stdout)
        return cmd

    def run(self, commands, ui_to_command_queue, command_to_ui_queue):
        cmd = self._cmd(commands, ui_to_command_queue, command_to_ui_queue)
        cmd.cmdloop(self._splash_text(extra_info={
                    'get-details':'run `license`',
                    }))

    def run_lines(self, commands, ui_to_command_queue, command_to_ui_queue,
                  lines):
        cmd = self._cmd(commands, ui_to_command_queue, command_to_ui_queue)
        for line in lines:
            cmd.onecmd(line)
