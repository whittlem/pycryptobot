from models.helper.LogHelper import Logger

class TextBox:
    def __init__(self, total_width, separator_column):
        # Save 7 characters for separator, left & right borders, and spacing
        self.width = total_width
        self.max_text = total_width - 7
        self.max_left = separator_column - 4
        self.max_right = total_width - separator_column - 3

    def singleLine(self):
        Logger.info('-' * self.width)

    def doubleLine(self):
        Logger.info('=' * self.width)

    def center(self, text):
        text_slice = text[slice(self.width - 4)]
        left_space = ' ' * int((self.width - len(text_slice) - 2)/2)
        right_space = ' ' * (self.width - len(text_slice) - len(left_space) - 2)
        Logger.info(f'|{left_space}{text_slice}{right_space}|')

    def line(self, left_text, right_text):
        left_slice = left_text[slice(self.max_left)]
        right_slice = right_text[slice(self.max_right)]
        left_space = (' ' * (self.max_left - len(left_slice)))
        right_space = (' ' * (self.max_right - len(right_slice)))
        Logger.info(f'| {left_space}{left_slice} : {right_slice}{right_space} |')
