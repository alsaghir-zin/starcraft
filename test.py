import curses
import sys

import curses


def main(stdscr):
    stdscr.addstr(0, 0, "Current mode: Typing mode",
              curses.A_REVERSE)
    while True:
        k = stdscr.getkey()
        if k == "q":
            sys.exit(0)




if __name__ == "__main__":
    curses.wrapper(main)
