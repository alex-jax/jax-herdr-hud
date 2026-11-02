#if DEBUG
import AppKit
import SwiftTerm
import HudCore

extension SmokeRun {
  func interactionChecks() async throws {
    let window = NSWindow(contentRect: NSRect(x: 80, y: 80, width: 640, height: 360),
      styleMask: [.titled], backing: .buffered, defer: false)
    window.isReleasedWhenClosed = false
    let terminal = HudTerminal()
    terminal.frame = window.contentView!.bounds
    terminal.autoresizingMask = [.width, .height]
    window.contentView!.addSubview(terminal)
    window.makeKeyAndOrderFront(nil)
    defer { terminal.endHistorySelection(); window.orderOut(nil); app.show() }
    try await Task.sleep(nanoseconds: 150_000_000)
    let rows = terminal.terminalDimensions.rows
    let cw = terminal.selectionCellSize.width, ch = terminal.selectionCellSize.height
    func mouse(_ type: NSEvent.EventType, _ x: CGFloat, _ y: CGFloat, _ flags: NSEvent.ModifierFlags = []) -> NSEvent {
      NSEvent.mouseEvent(with: type, location: terminal.convert(NSPoint(x: x, y: terminal.bounds.height - y), to: nil),
        modifierFlags: flags, timestamp: ProcessInfo.processInfo.systemUptime,
        windowNumber: window.windowNumber, context: nil, eventNumber: 0, clickCount: 1, pressure: 0.5)!
    }
    func key(_ letter: String, flags: NSEvent.ModifierFlags = []) -> NSEvent {
      NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: flags,
        timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber,
        context: nil, characters: letter, charactersIgnoringModifiers: letter,
        isARepeat: false, keyCode: letter == "v" ? 9 : 0)!
    }
    var sent: [UInt8] = []
    terminal.testSentData = { sent += $0 }
    terminal.feed(text: "\u{1b}[2J\u{1b}[Hselect this plain text\r\nsecond line\u{1b}[?1000h\u{1b}[?1002h\u{1b}[?1006h")
    terminal.mouseDown(with: mouse(.leftMouseDown, cw, ch / 2))
    terminal.mouseDragged(with: mouse(.leftMouseDragged, cw * 12, ch / 2, .shift))
    terminal.mouseUp(with: mouse(.leftMouseUp, cw * 12, ch / 2, .shift))
    try require(NSPasteboard.general.string(forType: .string)?.contains("elect this") == true, "normal drag copies plain text")
    try require(sent.isEmpty, "selection does not reach mouse-aware CLI when Shift changes")
    terminal.mouseDown(with: mouse(.leftMouseDown, cw * 3, ch * 1.5, .shift))
    terminal.mouseDragged(with: mouse(.leftMouseDragged, cw * 5, ch * 1.5))
    terminal.mouseUp(with: mouse(.leftMouseUp, cw * 5, ch * 1.5))
    try await Task.sleep(nanoseconds: 100_000_000)
    let reports = String(decoding: sent, as: UTF8.self)
    try require(reports.contains("\u{1b}[<0;") && reports.contains("m"), "Shift route forwards unshifted press/release: \(reports.debugDescription)")
    sent = []
    NSPasteboard.general.clearContents()
    NSPasteboard.general.setString("dictated text", forType: .string)
    terminal.handleKeyDown(key("v", flags: .control))
    try await Task.sleep(nanoseconds: 100_000_000)
    try require(String(decoding: sent, as: UTF8.self) == "dictated text", "Control-V pastes clipboard text: \(String(decoding: sent, as: UTF8.self).debugDescription)")
    try require(!terminal.selectionActive, "Control-V clears selection")
    sent = []
    NSPasteboard.general.clearContents()
    NSPasteboard.general.setData(Data([1, 2, 3]), forType: .tiff)
    terminal.handleKeyDown(key("v", flags: .command))
    try await Task.sleep(nanoseconds: 100_000_000)
    try require(sent == [22], "image-only clipboard preserves CLI paste shortcut")
    sent = []
    terminal.feed(text: "\u{1b}[2J\u{1b}[Hhttps://example.com\r\n\u{1b}]8;;https://example.org/label\u{7}labelled\u{1b}]8;;\u{7}")
    var links: [String] = []
    terminal.testOpenLink = { links.append($0.absoluteString) }
    for (row, flags) in [(0, NSEvent.ModifierFlags.control), (1, .command)] {
      terminal.mouseDown(with: mouse(.leftMouseDown, cw * 3, ch * (CGFloat(row) + 0.5), flags))
      terminal.mouseUp(with: mouse(.leftMouseUp, cw * 3, ch * (CGFloat(row) + 0.5), flags))
    }
    try require(links == ["https://example.com", "https://example.org/label"], "Control/Command-click implicit and OSC 8 links")
    terminal.rightMouseDown(with: mouse(.rightMouseDown, cw * 3, ch / 2, .control))
    terminal.rightMouseUp(with: mouse(.rightMouseUp, cw * 3, ch / 2))
    try require(links.last == "https://example.com" && links.count == 3, "AppKit secondary Control-click opens link")
    try require(sent.isEmpty, "link clicks do not reach CLI")

    // Retained shell history, using the same asynchronous callback as pane.read.
    terminal.readHistory = { completion in completion(.success((0..<100).map { "\u{1b}[32mhistory line \($0)\u{1b}[0m" }.joined(separator: "\n"))) }
    terminal.mouseDown(with: mouse(.leftMouseDown, cw, ch * 3))
    terminal.mouseDragged(with: mouse(.leftMouseDragged, cw * 8, -ch * 2))
    try await Task.sleep(nanoseconds: 350_000_000)
    terminal.mouseUp(with: mouse(.leftMouseUp, cw * 8, -ch * 2))
    try require(NSPasteboard.general.string(forType: .string)?.contains("history line") == true, "edge selection copies retained shell history")
    try require(window.firstResponder === terminal, "history release restores live terminal focus")
    terminal.readHistory = nil
    terminal.agentTerminal = true
    for direction in [-1, 1] {
      var offset = 30
      func redraw() {
        let text = ["pinned header"] + (offset..<(offset + rows - 3)).map { "transcript line \($0)" } + ["input", "footer"]
        terminal.feed(text: "\u{1b}[H\u{1b}[2J" + text.joined(separator: "\r\n"))
      }
      redraw()
      terminal.testScrollCLI = { actual in offset += actual * 2; redraw() }
      let edge = direction < 0 ? -ch : terminal.bounds.height + ch
      terminal.mouseDown(with: mouse(.leftMouseDown, cw, ch * CGFloat(rows / 2)))
      terminal.mouseDragged(with: mouse(.leftMouseDragged, cw * 8, edge))
      try await Task.sleep(nanoseconds: 650_000_000)
      terminal.mouseUp(with: mouse(.leftMouseUp, cw * 8, edge))
      let copied = NSPasteboard.general.string(forType: .string) ?? ""
      try require(offset != 30 && copied.contains("transcript line"), "live CLI edge selection direction \(direction)")
      try require(!copied.contains("pinned header") && !copied.contains("footer"), "live selection excludes pinned controls")
      let released = offset
      try await Task.sleep(nanoseconds: 250_000_000)
      try require(offset == released, "release cancels edge scroll timer")
      try require(window.firstResponder === terminal, "live selection keeps focus")
    }
    terminal.testScrollCLI = nil
    terminal.keyDown(with: key("a"))
    try await Task.sleep(nanoseconds: 100_000_000)
    try require(sent.last == 97, "typing after selection needs no Escape")
    app.show()
    app.window.makeFirstResponder(app.themeButton)
    app.toggleTheme()
    try await Task.sleep(nanoseconds: 100_000_000)
    try require(app.window.firstResponder === app.terminals[app.selected!], "header action restores terminal focus")
  }
}
#endif
