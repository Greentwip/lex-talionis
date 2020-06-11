from . import GlobalConstants as GC
from . import configuration as cf

def command_chunk(text, num_lines):
    # Split on breaks and clears
    longest_dialogue_size = 0
    current_dialogue = []
    command = []
    in_command = False
    for character in text:
        if character == '{':
            in_command = True

        if in_command:
            command.append(character)
        else:
            current_dialogue.append(character)

        if character == '}':
            in_command = False
            command_text = ''.join(command)
            if command_text == '{clear}' or command_text == '{br}':
                current_text = ''.join(current_dialogue)
                # Now find out how big this needs to be to hold this
                width = determine_width(current_text, num_lines)
                if width > longest_dialogue_size:
                    longest_dialogue_size = width
                # Clear current dialogue
                current_dialogue = []
            # Clear command
            command = []
    # And do it at the end
    current_text = ''.join(current_dialogue)
    # Now find out how big this needs to be to hold this
    width = determine_width(current_text, num_lines)
    if width > longest_dialogue_size:
        longest_dialogue_size = width

    length = longest_dialogue_size + 8*2
    return length, num_lines * 16 + 16

def determine_width(text, num_lines):
    chunks = line_chunk(text)
    if len(chunks) <= 5 and sum(len(c) for c in chunks) <= 22:
        num_lines = 1  # Try just 1 line if 3 or less words
    for w in range(32, GC.WINWIDTH - 8*4, 8):
        # print('width', w)
        output_lines = line_wrap(line_chunk(text), w, GC.FONT['convo_black'], test=True)
        # print(w, output_lines)
        if len(output_lines) <= num_lines:
            return w # This is an extra buffer to account for waiting cursor
    if cf.OPTIONS['debug']:
        print('Text too big for dialog box!')
    return GC.WINWIDTH - 8*4

def line_chunk(text):
    chunks = text.strip().split(' ')
    chunks = [x for x in chunks if x] # Remove empty chunks
    return chunks

# This is such an awful algorithm :(
def line_wrap(chunks, width, font, test=False):
    lines = []
    chunks.reverse()
    space_length = font.size(' ')[0]
    if test:
        chunks.insert(0, '   ')

    while chunks:
        cur_line = []
        cur_len = 0

        while chunks:
            length = font.size(chunks[-1])[0]
            # print(cur_line, chunks[-1], cur_len, length, width)
            if length > width:
                if test:
                    return 'One word is too wide for line!'  # Which has a huge length, always failing length check
                # else
                if cur_line:
                    lines.append(' '.join(cur_line))
                cur_line = []
                cur_len = 0
                cur_line.append(chunks.pop())
                cur_len += length
                cur_len += space_length
            # Can at least squeeze this chunk onto the current line
            elif cur_len + length <= width:
                cur_line.append(chunks.pop())
                cur_len += length
                cur_len += space_length
            # Nope, this line is full
            else:
                break

        # Convert current line back to a string and store it in list
        # of all lines (return value).
        if cur_line:
            lines.append(' '.join(cur_line))
    return lines

def split(font, string, num_lines):
    total_length = font.size(string)[0]
    lines = []
    for line in range(num_lines):
        lines.append([])
    new_line = False
    which_line = 0
    for character in string:
        if new_line and character == ' ':
            which_line += 1
            new_line = False
            if which_line >= len(lines):
                break
            else:
                continue
                
        lines[which_line].append(character)
        length_so_far = font.size(''.join(lines[which_line]))[0]
        if length_so_far > total_length // num_lines:
            new_line = True
        elif length_so_far > GC.WINWIDTH - 8:
            new_line = True

    return [''.join(line) for line in lines]
