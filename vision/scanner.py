"""
This implements the scanner which reads in a test, line by line, and
turn each line into Commands.
"""

# Python Libraries
import attr
import itertools
import functools
import platform
import types
import collections
import inspect
import pprint

# Vision Libraries
import tokens

@attr.s(slots=True)
class Scanner(object):
    """
    This scanner scans in user commands from a list (probably provided
    from a file) or from an interactive prompt.  The way it scans can be
    altered by setting the line_reader attribute to a new function.
    """

    name = attr.ib(
        validator=attr.validators.instance_of(str))
    lines = attr.ib(
        validator=lambda self, name, value: value[0] and attr.validators.instance_of(collections.Sequence)(self, name, value),
        repr=False)
    position = attr.ib(
        default=0,
        init=False,
        validator=lambda self, name, value: self._validate_position(name, value),
        repr=True)
    command_type = attr.ib(
        default=tokens.Command,
        repr=False)
    _line_reader = attr.ib(
        init=False,
        default=None,
        repr=False)

    def __iter__(self):
        return self

    @property
    def line_reader(self):
        """
        Gets the line reader for next().  If there is none set, it will
        turn the one in self.default_line_reader into a method, set IT
        as the line reader for the future, and return the method.
        """

        if not self._line_reader:
            self._line_reader = types.MethodType(lambda self, index: self.lines[index], self)
        return self._line_reader

    @line_reader.setter
    def line_reader(self, reader):
        """
        Sets the line reader for next().  This should be a unary
        function, as it will be made into a method, and should return a
        string.
        """

        if reader:
            self._line_reader = types.MethodType(reader, self)
        else:
            # passing a falsey value into this is equivalent to
            # deleting, so we'll do that here
            del self.line_reader
        return reader

    @line_reader.deleter
    def line_reader(self):
        """
        Deletes the line reader, by replacing it with None.  The next
        time the getter is called, this will be set back to the default.
        """
        self._line_reader = None

    def __reversed__(self):
        """
        Returns an iterator that allows the reversed() function to be
        used with the scanner.  The iterator will return commands for
        each line from the latest returned line to the first line.  It
        will skip whitespace, as next() does.

        Create a scanner with some lines in it.
        >>> scanner = Scanner(
        ...   name="test_scanner",
        ...   lines=[
        ...     'line with no dangling whitespace',
        ...     'line with dangling whitespace    \t',
        ...     '', # empty string
        ...     'another good line',
        ...     '',]) # more empty spaces

        Iterate through the lines, to consume the scanner.
        >>> pprint.pprint(list(scanner))
        [Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=4), line=0, start=0, end=None)),
         Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=4), line=1, start=0, end=None)),
         Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=4), line=3, start=0, end=None))]

        Now iterate in reverse.
        >>> pprint.pprint(list(reversed(scanner)))
        [Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=0), line=3, start=0, end=None)),
         Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=0), line=1, start=0, end=None)),
         Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=0), line=0, start=0, end=None))]

        We'll iterate part of the way through and back, so as to prove
        that the iterator will only iterate across lines that have been
        iterated through.
        >>> next(scanner)
        Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=1), line=0, start=0, end=None))
        >>> next(scanner)
        Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=2), line=1, start=0, end=None))
        >>> pprint.pprint(list(reversed(scanner)))
        [Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=0), line=1, start=0, end=None)),
         Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=0), line=0, start=0, end=None))]
        """
        try:
            while True:
                command = None
                while not command:
                    line = self.line_reader(index=self.position)
                    if line.rstrip():
                        command = self.command_type(
                            code_provider=ScannerCodeProvider(
                                line=self.position,
                                scanner=self))
                    try:
                        self.rewind()
                    finally:
                        if command:
                            yield command
        except IndexError as ie:
            pass

    def next(self):
        """
        Returns a command for the next line to be scanned that is not
        all whitespace.  If there are no more lines, it raises a
        StopIteration with a command attribute set to None.

        Create a scanner with some lines in it.
        >>> scanner = Scanner(
        ...   name="test_scanner",
        ...   lines=[
        ...     'line with no dangling whitespace',
        ...     'line with dangling whitespace    \t',
        ...     '', # empty string
        ...     'another good line',
        ...     '',]) # more empty spaces

        Iterate through the lines.  Notice that the empty srings are
        skipped.
        >>> command = next(scanner)
        >>> command
        Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=1), line=0, start=0, end=None))
        >>> command.code
        'line with no dangling whitespace'
        >>> command = next(scanner)
        >>> command
        Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=2), line=1, start=0, end=None))
        >>> command.code
        'line with dangling whitespace    \t'
        >>> command = next(scanner)
        >>> command
        Command(code_provider=ScannerCodeProvider(scanner=Scanner(name='test_scanner', position=4), line=3, start=0, end=None))
        >>> command.code
        'another good line'
        >>> try:
        ...   next(scanner)
        ... except StopIteration as si:
        ...   print si.command
        None
        """

        command = None
        try:
            while not command:
                line = self.line_reader(index=self.position)
                if line.rstrip():
                    command = self.command_type(
                        code_provider=ScannerCodeProvider(
                            line=self.position,
                            scanner=self))
                self.advance()
        except IndexError as ie:
            si = StopIteration()
            si.command = None
            raise si
        return command

    def _validate_position(self, name, value):
        if not isinstance(value, int):
            raise TypeError(
                "Scanner.position must be <int>")
        if not (0 <= value < len(self.lines)):
            raise IndexError(
                "Scanner.position must be 0 <= Scanner.position < %d: Got %d" % (len(self.lines), value))
        return True

    def advance(self):
        """
        Moves the position of the scanner forward by one, and returns the
        new value.
        """

        self.position += 1
        try:
            attr.validate(self)
        except (IndexError, TypeError) as e:
            self.position -= 1
            raise
        return self.position

    def rewind(self):
        """
        Moves the position of the scanner back by one, and returns the
        new value.
        """

        self.position -= 1
        try:
            attr.validate(self)
        except (IndexError, TypeError) as e:
            self.position += 1
            raise
        return self.position

@attr.s(
    slots=True,
    cmp=False)
class ScannerCodeProvider(tokens.CodeProvider):
    """
    CodeProviders abstract away different ways for tokens to access the
    Vision code they're based on.
    This provides the line of code for a ParseUnit from a scanner.

    We'll make one, and test its interface.
    >>> scanner1 = Scanner(
    ...   name="test_scanner1",
    ...   lines=[
    ...     'line with no dangling whitespace',
    ...     'line with dangling whitespace    \t',
    ...     '', # empty string
    ...     'another good line',
    ...     '',]) # more empty spaces
    >>> scp1 = ScannerCodeProvider(
    ...   scanner=scanner1,
    ...   line=0)
    >>> str(scp1)
    'line with no dangling whitespace'
    >>> scp1.code
    'line with no dangling whitespace'

    There are requirements.
    'scanner' must be a Scanner, or an exception is raised.
    >>> ScannerCodeProvider(
    ...  scanner="Not a Scanner",
    ...  line=0)
    Traceback (most recent call last):
      ...
    TypeError: ("'scanner' must be <class '__main__.Scanner'> (got 'Not a Scanner' that is a <type 'str'>).", Attribute(name='scanner', default=NOTHING, validator=<instance_of validator for type <class '__main__.Scanner'>>, repr=True, cmp=True, hash=True, init=True, convert=None, metadata=mappingproxy({})), <class '__main__.Scanner'>, 'Not a Scanner')

    'line' must be a positive integer that can index into the scanner,
    or an exception will be raised.
    >>> ScannerCodeProvider(
    ...  scanner=scanner1,
    ...  line="not an integer")
    Traceback (most recent call last):
      ...
    TypeError: ScannerCodeProvider.line must be <int>
    >>> ScannerCodeProvider(
    ...  scanner=scanner1,
    ...  line=-1)
    Traceback (most recent call last):
      ...
    IndexError: ScannerCodeProvider.line must be 0 <= ScannerCodeProvider.line < 5: Got -1
    >>> ScannerCodeProvider(
    ...  scanner=scanner1,
    ...  line=6)
    Traceback (most recent call last):
      ...
    IndexError: ScannerCodeProvider.line must be 0 <= ScannerCodeProvider.line < 5: Got 6

    'line' also must index to a non-whitespace line, or an exception is
    raised.
    >>> ScannerCodeProvider(
    ...  scanner=scanner1,
    ...  line=2)
    Traceback (most recent call last):
      ...
    ValueError: Scanner.line_reader(index=ScannerCodeProvider.line) must be non-whitespace

    'scanner' and 'line' are required, or an exception will be raised.
    >>> ScannerCodeProvider(
    ...  scanner=scanner1)
    Traceback (most recent call last):
      ...
    TypeError: __init__() takes at least 3 arguments (2 given)
    >>> ScannerCodeProvider(
    ...  line=6)
    Traceback (most recent call last):
      ...
    TypeError: __init__() takes at least 3 arguments (2 given)

    ScannerCodeProviders can be compared, if they are based on same
    lines in Scanners of the same name.
    >>> scanner2 = Scanner(
    ...   name="test_scanner1",
    ...   lines=[
    ...     'line with no dangling whitespace',
    ...     'line with dangling whitespace    \t',
    ...     '', # empty string
    ...     'another good line',
    ...     '',]) # more empty spaces
    >>> scp2 = ScannerCodeProvider(
    ...   scanner=scanner2,
    ...   line=0)
    >>> scp1.can_compare_to(scp2)
    True
    >>> scp2.can_compare_to(scp1)
    True

    If the Scanners have different names, they can't be compared.
    >>> scanner3 = Scanner(
    ...   name="test_scanner2",
    ...   lines=[
    ...     'line with no dangling whitespace',
    ...     'line with dangling whitespace    \t',
    ...     '', # empty string
    ...     'another good line',
    ...     '',]) # more empty spaces
    >>> scp3 = ScannerCodeProvider(
    ...   scanner=scanner3,
    ...   line=0)
    >>> scp1.can_compare_to(scp3)
    False
    >>> scp3.can_compare_to(scp1)
    False

    If the ScannerCodeProviders use different lines, they can't be
    compared.
    >>> scp4 = ScannerCodeProvider(
    ...   scanner=scanner1,
    ...   line=1)
    >>> scp1.can_compare_to(scp4)
    False
    >>> scp4.can_compare_to(scp1)
    False

    ScannerCodeProviders that can be compared can be sorted based on the
    starting point in the line they're based on.
    >>> scp5 = ScannerCodeProvider(
    ...   scanner=scanner1,
    ...   line=1,
    ...   start=5)
    >>> pprint.pprint([scp5, scp4])
    [ScannerCodeProvider(scanner=Scanner(name='test_scanner1', position=0), line=1, start=5, end=None),
     ScannerCodeProvider(scanner=Scanner(name='test_scanner1', position=0), line=1, start=0, end=None)]
    >>> pprint.pprint(list(sorted([scp5, scp4])))
    [ScannerCodeProvider(scanner=Scanner(name='test_scanner1', position=0), line=1, start=0, end=None),
     ScannerCodeProvider(scanner=Scanner(name='test_scanner1', position=0), line=1, start=5, end=None)]

    Trying to sort ScannerCodeProvider that cannot be compared will raise
    a ValueException.
    >>> list(sorted([scp3, scp4]))
    Traceback (most recent call last):
      ...
    ValueError: These CodeProviders cannot be compared
    """

    scanner = attr.ib(
        validator=attr.validators.instance_of(Scanner))
    line = attr.ib(
        validator=lambda self, name, value:self._validate_line(name, value))
    start = attr.ib(
        default=0,
        validator=lambda self, name, value:self.code[value])
    end = attr.ib(
        default=None,
        validator=attr.validators.optional(lambda self, name, value:self.code[self.start:value]))

    def can_compare_to(self, other):
        """
        Check if 'self' can be meaningfully compared to 'other'
        """
        return self.scanner.name == other.scanner.name and self.line == other.line

    @property
    def code(self):
        return str(self)

    def __str__(self):
        if self.end is not None:
            return self.scanner.line_reader(self.line)[self.start:self.end]
        else:
            return self.scanner.line_reader(self.line)[self.start:]

    def _validate_line(self, name, value):
        try:
            self.scanner._validate_position('line', value)
        except TypeError as te:
            raise TypeError(
                "ScannerCodeProvider.line must be <int>")
        except IndexError as ie:
            raise IndexError(
                "ScannerCodeProvider.line must be 0 <= ScannerCodeProvider.line < %d: Got %d" % (len(self.scanner.lines), value))
        if not str(self).strip():
            # If the line we're given results in a line that is all
            # whitespace, raise a ValueError
            raise ValueError("Scanner.line_reader(index=ScannerCodeProvider.line) must be non-whitespace")
        return True

if __name__ == "__main__":
    import doctest
    doctest.testmod()