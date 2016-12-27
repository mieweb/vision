"""
This implements the Vision interpreter, tokenizer, and parser machinery
"""

# Python libraries
import attrs
import collections
import copy

# Vision libraries
import tokens
import scanner


@attr.s(slots=True)
class Lexicon(object):
    """
    A Lexicon is an ephemeral object that condenses Modules into
    information of how to handle the tokens in the current Command.
    """

@attr.s(slots=True)
class Tokenizer(object):
    """
    A Tokenizer is an ephemeral iterator that generates the tokens from
    a line of Vision code.
    """

    command=attr.ib(
        validator=attr.validators.instance_of(tokens.Command))
    definitions=attr.ib(
        default=attr.Factory(collections.OrderedDict),
        validator=attr.validators.instance_of(collections.Mapping))
    position=attr.ib(
        init=False,
        default=0)

    def __iter__(self):
        return self

    def next(self):
        errorstart = None
        try:
            while self.position < len(self.code):
                for pattern, definition in definitions.iteritems():
                    match = re.match(pattern, self.command.code[self.position:], re.IGNORECASE)
                    if match:
                        if errorstart is not None:
                            raise ValueError(
                                "Unrecognized token error: %s" % self.command.code[errorstart:self.position])
                        else:
                            token = definition['token'](
                                code_provider=CommandCodeProvider(
                                    command=self.command,
                                    start=match.start(),
                                    end=match.end()),
                                definition=copy.deepcopy(definition))
                            self.position=match.end()
                            return token
                else:
                    if errorstart is None:
                        errorstart = self.position
                self.position += 1
            else:
                raise ValueError(
                    "Unrecognized token error: %s" % self.command.code[errorstart:])
        except ValueError as ve:
            ve.tokenizer = self
            raise

@attr.s(slots=True)
class Interpreter(object):
    """
    This is the Vision interpreter.  It holds the history of commands
    and the scanners, and delegates most of the actual work to the Lexicon.
    I'm not sure if I need to keep it, actually.
    """

    history=attr.ib(
        init=False,
        default=attr.Factory(list),
        repr=False)

    # This is the map of scanners this interpreter uses.  They are read
    # last first
    scanners=attr.ib(
        init=False,
        default=attr.Factory(collections.OrderedDict),
        repr=False)
    base_modules=attr.ib(
        default=attr.Factory(collections.OrderedDict((modules.base.name, modules.base))),
        repr=True)

    def add_test_file(self, path, line_reader=None):
        """
        If the path we're given does not map to a current scanner,
        create a new one and put it into the scanners map.  Otherwise,
        move the matching scanner to the end of the scanners map.
        """
        with open(os.path.join(self.test_directory, path)) as scanner_file:
            new_scanner = scanner.Scanner(
                name=path,
                lines=scanner_file.readlines(),
                command_type=lambda: self.lexicon[tokens.Command].definition)
            new_scanner.line_reader = line_reader
        self.scanner = new_scanner

    @property
    def scanner(self):
        return self.scanners.values()[-1]

    @scanner.setter
    def scanner(self, scanner):
        if scanner.name in self.scanners:
            scanner = self.scanners.pop(scanner.name)
        self.scanners[scanner.name] = scanner

    @scanner.deleter
    def scanner(self, scanner):
        del self.scanners[scanner.name]

    @property
    def file_scanner(self):
        return list(scanner for scanner in self.scanners.value() if scanner.name != 'interactive')[-1]

    @property
    def interactive_scanner(self):
        return list(scanner for scanner in self.scanners.value() if scanner.name == 'interactive')[-1]

    @property
    def lexicon(self):
        """
        Gets all the modules that are currently in scope and builds a
        lexicon from them.
        """
        modules = []
        scope_level = 0
        for command, scope_change in ((command, self.get_scope_change(command)) for command in self.history):
            if scope_change < 0:
                # remove some modules
                modules = modules[:scope_change]
            elif scope_change > 0:
                modules.append(command.modules)
            scope_level += scope_change

        modules_dict = collections.OrderedDict(self.base_modules)
        for module in modules:
            for mod in module:
                modules_dict[mod.name] = mod

        # return a lexicon of the modules in scope
        return lexicon.Lexicon(
            modules=modules_dict)