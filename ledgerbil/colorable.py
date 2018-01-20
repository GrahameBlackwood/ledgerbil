import re


class Colorable(object):

    START_CODE = '\033'
    END_CODE = f'{START_CODE}[0m'

    BRIGHT_OFFSET = 60

    COLORS = {
        'black': 30,
        'gray': 30,
        'grey': 30,
        'red': 31,
        'green': 32,
        'yellow': 33,
        'blue': 34,
        'magenta': 35,
        'purple': 35,
        'cyan': 36,
        'white': 37
    }

    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

    def __init__(self, color, value, fmt='', bright=False):

        try:
            self.COLORS[color]
        except KeyError:
            raise UnsupportedColorError(
                f"I don't know what to do with this color: {color}"
            )

        self.my_color = color
        self.value = value
        self.bright = bright
        self.format_string = fmt

    def __str__(self):
        ansi_str = '{start}{value:{fmt}}{end}'.format(
            start=self.ansi_sequence(
                self.COLORS[self.my_color],
                bright=self.bright
            ),
            value=self.value,
            fmt=self.format_string,
            end=self.END_CODE
        )

        return ansi_str

    def __len__(self):
        return len(self.value)

    def ansi_sequence(self, code, bright=False):
        offset = 60 if bright else 0
        return '{start}[0;{color}m'.format(
            start=self.START_CODE,
            color=code + offset
        )

    def plain(self):
        return self.value

    @staticmethod
    def get_plain_string(ansi_string):
        return Colorable.ansi_escape.sub('', ansi_string)


class UnsupportedColorError(Exception):
    pass
