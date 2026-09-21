#!/usr/bin/python3
"""Hud-only color presentation around Herdr's native direct-attach client.

Input, mouse reports, resize and terminal control sequences pass through. SGR foreground colors
are preserved for filenames, syntax and CLI controls; explicit backgrounds use
the selected Hud background. OSC palette replacements are
blocked so VTE retains the user-selected theme.
No shell or agent process is created, signalled or reconfigured by this helper.
"""
import errno
import fcntl
import os
import pty
import select
import signal
import sys
import termios
import tty


class DisplayFilter:
    def __init__(self):
        self.pending = bytearray()
        self.state = 'text'

    @staticmethod
    def theme_background(sequence):
        # Parse complete SGR parameters so RGB components cannot be mistaken for
        # standalone background codes. Unknown/malformed sequences pass through.
        parts = sequence[2:-1].split(b';')
        result = []
        index = 0
        while index < len(parts):
            part = parts[index]
            code = part.split(b':', 1)[0]
            if code in (b'38', b'48', b'58'):
                if b':' in part:
                    result.append(b'49' if code == b'48' else part)
                    index += 1
                    continue
                if index + 1 >= len(parts):
                    return sequence
                mode = parts[index + 1]
                count = 5 if mode == b'2' else 3 if mode == b'5' else 0
                if not count or index + count > len(parts):
                    return sequence
                result.extend([b'49'] if code == b'48' else parts[index:index + count])
                index += count
                continue
            if part.isdigit() and (40 <= int(part) <= 47 or 100 <= int(part) <= 107):
                result.append(b'49')
            else:
                result.append(part)
            index += 1
        return b'\x1b[' + b';'.join(result) + b'm'

    def feed(self, data):
        output = bytearray()
        for byte in data:
            if self.state == 'text':
                if byte == 27:
                    self.pending.append(byte)
                    self.state = 'escape'
                else:
                    output.append(byte)
            elif self.state == 'escape':
                self.pending.append(byte)
                if byte == ord('['):
                    self.state = 'csi'
                elif byte == ord(']'):
                    self.state = 'osc'
                elif byte in b'PX^_':
                    output.extend(self.pending)
                    self.pending.clear()
                    self.state = 'string'
                else:
                    output.extend(self.pending)
                    self.pending.clear()
                    self.state = 'text'
            elif self.state in ('string', 'string_escape'):
                output.append(byte)
                if self.state == 'string_escape' and byte == ord('\\'):
                    self.state = 'text'
                else:
                    self.state = 'string_escape' if byte == 27 else 'string'
            else:
                self.pending.append(byte)
                complete = (self.state == 'csi' and 0x40 <= byte <= 0x7e or
                            self.state == 'osc' and (byte == 7 or self.pending.endswith(b'\x1b\\')))
                if complete:
                    sequence = bytes(self.pending)
                    if self.state == 'csi' and sequence.endswith(b'm'):
                        sequence = self.theme_background(sequence)
                    if self.state == 'osc' and sequence[2:].split(b';', 1)[0].rstrip(b'\x07\x1b\\') in (
                            b'4', b'10', b'11', b'12', b'104', b'110', b'111', b'112'):
                        # Queries still receive VTE's answer; assignments cannot override Hud.
                        if b'?' in sequence:
                            output.extend(sequence)
                    else:
                        output.extend(sequence)
                    self.pending.clear()
                    self.state = 'text'
                elif len(self.pending) > 65536:
                    output.extend(self.pending)
                    self.pending.clear()
                    self.state = 'text'
        return bytes(output)


def write_all(fd, data):
    while data:
        written = os.write(fd, data)
        data = data[written:]


def run(argv):
    size = fcntl.ioctl(0, termios.TIOCGWINSZ, b'\0' * 8)
    saved = termios.tcgetattr(0)
    pid, master = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, size)
        os.execvp(argv[0], argv)
    def resize(*_):
        fcntl.ioctl(master, termios.TIOCSWINSZ,
                    fcntl.ioctl(0, termios.TIOCGWINSZ, b'\0' * 8))
    def stop(*_):
        raise SystemExit(0)
    signal.signal(signal.SIGWINCH, resize)
    signal.signal(signal.SIGHUP, stop)
    signal.signal(signal.SIGTERM, stop)
    filtering = DisplayFilter()
    try:
        tty.setraw(0)
        resize()
        while True:
            ready, _, _ = select.select([0, master], [], [])
            for fd in ready:
                try:
                    data = os.read(fd, 65536)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        return
                    raise
                if not data:
                    return
                write_all(master if fd == 0 else 1,
                          data if fd == 0 else filtering.feed(data))
    finally:
        # Only our attach client belongs to us; Herdr's server owns the real pane.
        try:
            os.kill(pid, signal.SIGHUP)
        except ProcessLookupError:
            pass
        os.close(master)
        try:
            termios.tcsetattr(0, termios.TCSANOW, saved)
        except termios.error:
            pass
        os.waitpid(pid, 0)


if __name__ == '__main__':
    run(sys.argv[1:])
