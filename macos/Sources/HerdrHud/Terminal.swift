import AppKit
import Darwin
import HudCore
import SwiftTerm

final class HudTerminal: TerminalView, TerminalViewDelegate, LocalProcessDelegate {
  #if DEBUG
    var testSentData: (([UInt8]) -> Void)?
    var testOpenLink: ((URL) -> Void)?
    var testScrollCLI: ((Int) -> Void)?
  #endif
  private var keyMonitor: Any?
  private var child: LocalProcess?
  private var filter = DisplayFilter()
  var connected = false
  var onExit: (() -> Void)?
  init() {
    super.init(
      frame: .zero, font: HudStyle.mono(),
      options: TerminalOptions(scrollback: 20000))
    keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
      guard let self, self.window?.firstResponder === self else { return event }
      return self.handleKeyDown(event) ? nil : event
    }
    terminalDelegate = self
    bellStyle = .none
    optionAsMetaKey = true
    setAccessibilityLabel("Herdr terminal")
  }
  deinit { if let keyMonitor { NSEvent.removeMonitor(keyMonitor) } }
  required init?(coder: NSCoder) { fatalError("init(coder:) unavailable") }
  func attach(executable: String, session: Session, pane: Pane) {
    guard !connected else { return }
    filter.reset()
    let process = LocalProcess(delegate: self, dispatchQueue: .main)
    child = process
    let env = Host.environment().map { "\($0.key)=\($0.value)" }
    switch process.startProcessChecked(
      executable: executable,
      args: ["--session", session.name, "terminal", "attach", pane.terminal_id], environment: env,
      currentDirectory: NSHomeDirectory())
    {
    case .success: connected = true
    case .failure(let error):
      child = nil
      let message: String
      switch error {
      case .forkFailed(let code), .writeChannelFailed(let code):
        if code == EMFILE || code == ENFILE {
          message = "Too many open file handles. Quit and reopen Hud, then select this terminal again. Your Herdr terminal has not been closed."
        } else {
          message = "\(String(cString: strerror(code))) (error \(code)). Select this terminal again to retry."
        }
      default:
        message = String(describing: error)
      }
      feed(text: "\r\nCould not attach: \(message)\r\n")
      connected = false
    }
  }
  func detach() {
    endHistorySelection()
    child?.terminate()
    connected = false
  }
  func dataReceived(slice: ArraySlice<UInt8>) {
    let bytes = filter.feed(slice)
    feed(byteArray: bytes[...])
  }
  func getWindowSize() -> winsize {
    let dimensions = terminalDimensions
    return winsize(
      ws_row: UInt16(clamping: dimensions.rows), ws_col: UInt16(clamping: dimensions.cols),
      ws_xpixel: 0, ws_ypixel: 0)
  }
  func processTerminated(_ source: LocalProcess, exitCode: Int32?) {
    guard source === child else { return }
    child = nil
    connected = false
    feed(text: "\r\nDisconnected. Select this terminal again to reconnect.\r\n")
    onExit?()
  }
  func sizeChanged(source: TerminalView, newCols: Int, newRows: Int) {
    var size = getWindowSize()
    child?.updateWindowSize(&size)
  }
  func setTerminalTitle(source: TerminalView, title: String) {}
  func hostCurrentDirectoryUpdate(source: TerminalView, directory: String?) {}
  func send(source: TerminalView, data: ArraySlice<UInt8>) {
    #if DEBUG
      testSentData?(Array(data))
    #endif
    child?.send(data: data)
  }
  func scrolled(source: TerminalView, position: Double) {}
  func requestOpenLink(source: TerminalView, link: String, params: [String: String]) {
    if let url = URL(string: link),
      ["https", "http", "mailto"].contains(url.scheme?.lowercased() ?? "")
    {
      #if DEBUG
        if let testOpenLink { testOpenLink(url); return }
      #endif
      NSWorkspace.shared.open(url)
    }
  }
  func bell(source: TerminalView) {}
  func clipboardCopy(source: TerminalView, content: Data) {
    if let text = String(data: content, encoding: .utf8) {
      NSPasteboard.general.clearContents()
      NSPasteboard.general.setString(text, forType: .string)
    }
  }
  func clipboardRead(source: TerminalView) -> Data? { nil }  // OSC reads never expose the user's clipboard.
  func rangeChanged(source: TerminalView, startY: Int, endY: Int) {}
  // The route belongs to the entire gesture, even if modifiers change mid-drag.
  private var selecting = false
  private var linkPress = false
  private var pressReporting = true
  private var pressEvent: NSEvent?
  private var lastDragEvent: NSEvent?
  var onSelectionStatus: ((String) -> Void)?
  var readHistory: ((@escaping (Result<String, Error>) -> Void) -> Void)?
  var agentTerminal = false
  private var historyGeneration = 0
  private var retainedHistory: String?
  private var historyView: HistoryTerminal?
  private var liveSelection: LiveSelection?
  private var initialRows: [TerminalVisibleRowSnapshot] = []

  private func routed(_ event: NSEvent) -> NSEvent {
    guard let copied = event.cgEvent?.copy() else { return event }
    var flags = event.modifierFlags
    flags.remove(.shift)
    if linkPress { flags.remove(.control); flags.insert(.command) }
    copied.flags = CGEventFlags(rawValue: UInt64(flags.rawValue))
    return NSEvent(cgEvent: copied) ?? event
  }
  override func mouseDown(with event: NSEvent) {
    endHistorySelection()
    window?.makeFirstResponder(self)
    pressEvent = event
    lastDragEvent = event
    pressReporting = allowMouseReporting
    linkPress = !event.modifierFlags.intersection([.command, .control]).isEmpty
    selecting = !event.modifierFlags.contains(.shift) || linkPress
    allowMouseReporting = selecting ? false : pressReporting
    initialRows = terminalStateSnapshot().visibleRows
    super.mouseDown(with: routed(event))
    if selecting && !linkPress {
      let generation = historyGeneration
      readHistory? { [weak self] result in
        guard let self, generation == self.historyGeneration, self.selecting else { return }
        switch result {
        case .success(let text): self.retainedHistory = text
        case .failure(let error): self.onSelectionStatus?("Could not load selection history: " + error.localizedDescription)
        }
      }
    }
  }
  override func mouseDragged(with event: NSEvent) {
    lastDragEvent = event
    if let liveSelection {
      liveSelection.move(to: selectionPoint(event))
      return
    }
    if let historyView {
      historyView.mouseDragged(with: routed(event))
      return
    }
    let point = selectionPoint(event)
    let rowHeight = selectionCellSize.height
    let atEdge = point.y < rowHeight || point.y >= bounds.height - rowHeight
    if selecting && !linkPress && atEdge, let pressEvent {
      if !agentTerminal, let text = retainedHistory,
        text.components(separatedBy: "\n").count > terminalDimensions.rows + 1 {
        beginRetainedSelection(text, press: pressEvent, motion: event)
        return
      }
      if agentTerminal {
        // Finish SwiftTerm's local drag and keep its live renderer/input surface.
        super.mouseUp(with: routed(event))
        selectNone()
        let selection = LiveSelection(terminal: self, rows: initialRows,
          anchor: selectionPoint(pressEvent))
        liveSelection = selection
        selection.move(to: point)
        return
      }
    }
    super.mouseDragged(with: routed(event))
  }
  override func mouseUp(with event: NSEvent) {
    defer {
      selecting = false; linkPress = false; pressEvent = nil; lastDragEvent = nil
      allowMouseReporting = pressReporting
      endHistorySelection()
      window?.makeFirstResponder(self)
    }
    if let liveSelection {
      liveSelection.move(to: selectionPoint(event))
    } else if let historyView {
      historyView.mouseUp(with: routed(event))
      historyView.copy(historyView)
    } else {
      super.mouseUp(with: routed(event))
      if selecting && !linkPress && selectionActive { copy(self) }
    }
  }
  override func rightMouseDown(with event: NSEvent) {
    // AppKit can deliver Control-click as a secondary-button event.
    if event.modifierFlags.contains(.control) {
      mouseDown(with: event)
      return
    }
    window?.makeFirstResponder(self)
    paste(self)
  }
  override func rightMouseUp(with event: NSEvent) {
    if linkPress { mouseUp(with: event) }
  }
  @discardableResult func handleKeyDown(_ event: NSEvent) -> Bool {
    endHistorySelection()
    if event.charactersIgnoringModifiers?.lowercased() == "v",
      !event.modifierFlags.intersection([.command, .control]).isEmpty {
      if let text = NSPasteboard.general.string(forType: .string) {
        pasteText(text)
        selectNone()
        return true
      }
      // SwiftTerm must encode this shortcut using the CLI's active keyboard protocol.
      if event.modifierFlags.contains(.control) && !event.modifierFlags.contains(.command) {
        return false
      }
      if let controlV = NSEvent.keyEvent(with: .keyDown, location: event.locationInWindow,
        modifierFlags: .control, timestamp: event.timestamp, windowNumber: event.windowNumber,
        context: nil, characters: "\u{16}", charactersIgnoringModifiers: "v",
        isARepeat: event.isARepeat, keyCode: 9) {
        super.keyDown(with: controlV)
      }
      return true
    }
    return false
  }
  override func paste(_ sender: Any) {
    endHistorySelection()
    if let text = NSPasteboard.general.string(forType: .string) { pasteText(text) }
    selectNone()
  }
  var selectionCellSize: NSSize {
    let scale = window?.backingScaleFactor ?? 2
    let width = font.advancement(forGlyph: font.glyph(withName: "W")).width
    return NSSize(width: max(1, (width * scale).rounded() / scale),
      height: max(1, ceil(font.ascender - font.descender + font.leading)))
  }
  private func selectionPoint(_ event: NSEvent) -> NSPoint {
    let p = convert(event.locationInWindow, from: nil)
    return NSPoint(x: p.x, y: bounds.maxY - p.y)
  }
  func visibleTextRows() -> [String] {
    terminalStateSnapshot().visibleRows.map { $0.text.replacingOccurrences(of: #"\s+$"#, with: "", options: .regularExpression) }
  }
  func scrollCLI(_ direction: Int) {
    #if DEBUG
      if let testScrollCLI { testScrollCLI(direction); return }
    #endif
    guard let window,
      let cg = CGEvent(scrollWheelEvent2Source: nil, units: .line, wheelCount: 1,
        wheel1: Int32(-direction), wheel2: 0, wheel3: 0) else { return }
    // SwiftTerm uses event coordinates for wheel reports. Aim inside the transcript.
    let screen = window.convertPoint(toScreen: convert(NSPoint(x: bounds.midX, y: bounds.midY), to: nil))
    let desktopTop = NSScreen.screens.first?.frame.maxY ?? 0
    cg.location = NSPoint(x: screen.x, y: desktopTop - screen.y)
    cg.flags = []
    guard let event = NSEvent(cgEvent: cg) else { return }
    allowMouseReporting = pressReporting
    super.scrollWheel(with: event)
    allowMouseReporting = false
  }
  func endHistorySelection() {
    if selecting, let event = lastDragEvent ?? pressEvent {
      historyView?.mouseUp(with: routed(event))
      super.mouseUp(with: routed(event))
      allowMouseReporting = pressReporting
      selecting = false; linkPress = false; pressEvent = nil; lastDragEvent = nil
    }
    historyGeneration += 1
    retainedHistory = nil
    liveSelection?.stop()
    liveSelection = nil
    historyView?.removeFromSuperview()
    historyView = nil
  }
  override func viewDidMoveToWindow() {
    super.viewDidMoveToWindow()
    if window == nil { endHistorySelection() }
  }
  private func beginRetainedSelection(_ text: String, press: NSEvent, motion: NSEvent) {
    super.mouseUp(with: routed(motion))
    selectNone()
    let view = HistoryTerminal(frame: bounds, font: HudStyle.mono(), options: TerminalOptions(scrollback: 20000))
    view.allowMouseReporting = false
    if let currentPalette { view.apply(currentPalette) }
    view.autoresizingMask = [.width, .height]
    addSubview(view)
    view.resize(cols: terminalDimensions.cols, rows: terminalDimensions.rows)
    let filter = DisplayFilter()
    view.feed(byteArray: filter.feed(Array(text.replacingOccurrences(of: "\r\n", with: "\n").replacingOccurrences(of: "\n", with: "\r\n").utf8)[...])[...])
    view.scroll(toPosition: 1)
    historyView = view
    view.mouseDown(with: routed(press))
    view.mouseDragged(with: routed(motion))
    window?.makeFirstResponder(self)
  }
  private var currentPalette: PaletteVariant?

}

struct PaletteVariant: Decodable {
  let foreground, background, cursor: String
  let colors: [String]
}
struct Palette: Decodable {
  let name: String
  let light, dark: PaletteVariant
  let primary: Bool?
}
extension NSColor {
  convenience init(hex: String) {
    let raw = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
    let value = UInt64(raw, radix: 16) ?? 0
    self.init(
      srgbRed: CGFloat((value >> 16) & 255) / 255, green: CGFloat((value >> 8) & 255) / 255,
      blue: CGFloat(value & 255) / 255, alpha: 1)
  }
}
extension HudTerminal {
  func apply(_ palette: PaletteVariant) {
    currentPalette = palette
    selectedTextForegroundColor = NSColor(hex:palette.foreground)
    selectedTextBackgroundColor = HudStyle.blend(NSColor(hex:palette.background),NSColor(hex:palette.colors[4]),0.35)
    nativeForegroundColor = NSColor(hex: palette.foreground)
    nativeBackgroundColor = NSColor(hex: palette.background)
    caretColor = NSColor(hex: palette.cursor)
    installColors(
      palette.colors.map { hex in
        let c = NSColor(hex: hex)
        return Color(
          red: UInt16(c.redComponent * 65535), green: UInt16(c.greenComponent * 65535),
          blue: UInt16(c.blueComponent * 65535))
      })
    needsDisplay = true
  }
}
