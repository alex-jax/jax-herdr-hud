#if DEBUG
import AppKit
import ApplicationServices
import HudCore

extension SmokeRun {
  func liveCLIChecks() async throws {
    guard let key = app.selected, app.pane(key) != nil,
      let terminal = app.terminals[key] else { throw HudError.message("Missing disposable CLI terminal") }
    let root = URL(fileURLWithPath: "/private/tmp/hud-cli-" + UUID().uuidString)
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: root) }
    let script = root.appendingPathComponent("cli.py")
    let output = root.appendingPathComponent("offset")
    try #"""
import os, re, sys, termios, tty
old = termios.tcgetattr(0)
position = 100
pending = b''
rows = os.get_terminal_size().lines

def draw():
    lines = ['pinned header'] + ['roundtrip line %d' % i for i in range(position, position + rows - 3)] + ['input', 'footer']
    os.write(1, ('\x1b[H\x1b[2J' + '\r\n'.join(lines)).encode())
    with open(sys.argv[1], 'w') as f:
        f.write(str(position))

try:
    tty.setraw(0)
    os.write(1, b'\x1b[?1049h\x1b[?1000h\x1b[?1006h')
    draw()
    while True:
        pending += os.read(0, 4096)
        if b'q' in pending:
            break
        while True:
            match = re.search(rb'\x1b\[<(\d+);(\d+);(\d+)[Mm]', pending)
            if match is None:
                break
            button, col, row = map(int, match.groups())
            pending = pending[match.end():]
            if 2 <= row <= rows - 2 and button in (64, 65):
                position += -2 if button == 64 else 2
                draw()
finally:
    os.write(1, b'\x1b[?1000l\x1b[?1006l\x1b[?1049l')
    termios.tcsetattr(0, termios.TCSANOW, old)
    print('HUD_CLI_ROUNDTRIP_DONE', flush=True)
"""#.write(to: script, atomically: true, encoding: .utf8)
    terminal.send(source: terminal,
      data: Array(("/usr/bin/python3 " + script.path + " " + output.path + "\r").utf8)[...])
    try await until("controlled CLI starts") { terminal.visibleTextRows().contains("roundtrip line 100") }
    var finished = false
    defer { if !finished { terminal.send(source: terminal, data: [113][...]) } }
    try require(!terminal.agentTerminal, "CLI selection does not depend on agent reporting")
    let ch = terminal.selectionCellSize.height, cw = terminal.selectionCellSize.width
    func mouse(_ type: NSEvent.EventType, _ y: CGFloat) -> NSEvent {
      NSEvent.mouseEvent(with: type,
        location: terminal.convert(NSPoint(x: cw * 6, y: terminal.bounds.height - y), to: nil),
        modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime,
        windowNumber: app.window.windowNumber, context: nil, eventNumber: 0, clickCount: 1, pressure: 0.5)!
    }
    func offset() -> Int { Int((try? String(contentsOf: output, encoding: .utf8)) ?? "") ?? 100 }
    for direction in [-1, 1] {
      let before = offset()
      let edge = direction < 0 ? ch / 2 : terminal.bounds.height - ch / 2
      terminal.mouseDown(with: mouse(.leftMouseDown, terminal.bounds.height / 2))
      terminal.mouseDragged(with: mouse(.leftMouseDragged, edge))
      try await until("real CLI wheel direction \(direction)", timeout: 4) {
        direction < 0 ? offset() < before : offset() > before
      }
      try await Task.sleep(nanoseconds: 350_000_000)
      terminal.mouseUp(with: mouse(.leftMouseUp, edge))
      try require(NSPasteboard.general.string(forType: .string)?.contains("roundtrip line") == true,
        "real CLI history copy direction \(direction)")
      try require(app.window.firstResponder === terminal, "real CLI retains terminal focus")
      let released = offset()
      try await Task.sleep(nanoseconds: 250_000_000)
      try require(offset() == released, "real CLI wheel stops on release")
    }
    if ProcessInfo.processInfo.environment["HUD_TEST_REAL_POINTER"] == "1" {
      try require(AXIsProcessTrusted(), "macOS Accessibility permission required for pointer events")
      guard let oldPosition = CGEvent(source: nil)?.location else {
        throw HudError.message("Cannot read pointer position")
      }
      defer { CGWarpMouseCursorPosition(oldPosition) }
      func screenPoint(_ y: CGFloat) -> CGPoint {
        let inWindow = terminal.convert(NSPoint(x: cw * 6, y: terminal.bounds.height - y), to: nil)
        let screen = app.window.convertPoint(toScreen: inWindow)
        return CGPoint(x: screen.x, y: (NSScreen.screens.first?.frame.maxY ?? 0) - screen.y)
      }
      func post(_ type: CGEventType, _ point: CGPoint) throws {
        guard let event = CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: point, mouseButton: .left) else {
          throw HudError.message("Cannot create pointer event")
        }
        event.post(tap: .cghidEventTap)
      }
      app.show()
      try await Task.sleep(nanoseconds: 200_000_000)
      for direction in [-1, 1] {
        let before = offset(), start = screenPoint(terminal.bounds.height / 2)
        let edge = screenPoint(direction < 0 ? ch / 2 : terminal.bounds.height - ch / 2)
        try post(.mouseMoved, start)
        try post(.leftMouseDown, start)
        try await Task.sleep(nanoseconds: 100_000_000)
        try post(.leftMouseDragged, edge)
        do {
          try await until("pointer drag direction \(direction)", timeout: 4) {
            direction < 0 ? offset() < before : offset() > before
          }
        } catch {
          try? post(.leftMouseUp, edge)
          throw error
        }
        try post(.leftMouseUp, edge)
        try await Task.sleep(nanoseconds: 250_000_000)
        let released = offset()
        try await Task.sleep(nanoseconds: 250_000_000)
        try require(offset() == released, "pointer release stops scrolling direction \(direction)")
        try require(NSPasteboard.general.string(forType: .string)?.contains("roundtrip line") == true,
          "pointer selection copies CLI text direction \(direction)")
      }
    }
    terminal.send(source: terminal, data: [113][...])
    try await until("controlled CLI exits") { terminal.visibleTextRows().contains { $0.contains("HUD_CLI_ROUNDTRIP_DONE") } }
    finished = true
  }
}
#endif
