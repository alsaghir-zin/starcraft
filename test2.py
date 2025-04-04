import curses
from curses import textpad

def create_input_window(stdscr, height, width, y, x, title):
    """Create a bordered window with a text input field"""
    win = curses.newwin(height, width, y, x)
    win.border()
    win.addstr(0, 2, f" {title} ")
    textbox_win = win.derwin(height-2, width-4, 1, 2)
    return win, textbox_win

def get_input(stdscr, prompt, y=0, x=0):
    """Get single-line input from user"""
    stdscr.addstr(y, x, prompt)
    curses.echo()  # Show user input
    input_str = stdscr.getstr(y, x + len(prompt), 20)  # Max 20 chars
    curses.noecho()
    return input_str.decode('utf-8')

def main(stdscr):
    # Initialize curses
    curses.curs_set(1)  # Visible cursor
    stdscr.clear()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    
    height, width = stdscr.getmaxyx()
    
    # Title
    stdscr.addstr(1, width//2-10, "Curses Input Demo", curses.A_BOLD | curses.color_pair(1))
    
    # Example 1: Simple single-line input
    name = get_input(stdscr, "Enter your name: ", 3, 5)
    
    # Example 2: Multi-line textpad input
    stdscr.addstr(6, 5, "Enter your address (press Ctrl-G when done):", curses.color_pair(2))
    address_win, textbox = create_input_window(stdscr, 6, 50, 7, 5, "Address")
    address_win.refresh()
    box = textpad.Textbox(textbox)
    textbox.refresh()
    address = box.edit()  # Allows multi-line editing
    address = address.strip()  # Remove trailing whitespace
    
    # Example 3: Password field (hidden input)
    stdscr.addstr(14, 5, "Enter password (hidden):", curses.color_pair(2))
    password = ""
    stdscr.refresh()
    y, x = 15, 5
    stdscr.addstr(y, x, "Password: ")
    curses.noecho()
    while True:
        c = stdscr.getch()
        if c == 10:  # Enter key
            break
        elif c == curses.KEY_BACKSPACE or c == 127:
            if len(password) > 0:
                password = password[:-1]
                stdscr.addstr(y, x+10+len(password), ' ')
        else:
            password += chr(c)
            stdscr.addstr(y, x+10+len(password)-1, '*')
        stdscr.move(y, x+10+len(password))
    
    # Display results
    stdscr.clear()
    stdscr.addstr(2, 5, f"Name: {name}", curses.A_BOLD)
    stdscr.addstr(4, 5, "Address:", curses.A_BOLD)
    for i, line in enumerate(address.split('\n')):
        stdscr.addstr(5+i, 7, line)
    stdscr.addstr(8, 5, f"Password length: {len(password)} characters", curses.A_BOLD)
    
    stdscr.addstr(height-2, 5, "Press any key to exit...", curses.A_REVERSE)
    stdscr.refresh()
    stdscr.getch()

if __name__ == "__main__":
    curses.wrapper(main)



