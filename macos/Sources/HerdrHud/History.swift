import AppKit
import HudCore
import SwiftTerm

/// Retained shell history uses the same terminal renderer, without an attachment.
final class HistoryTerminal: TerminalView {
  override func hitTest(_ point: NSPoint) -> NSView? { nil }
  func apply(_ palette: PaletteVariant) {
    nativeForegroundColor = NSColor(hex: palette.foreground)
    nativeBackgroundColor = NSColor(hex: palette.background)
    selectedTextForegroundColor = NSColor(hex: palette.foreground)
    selectedTextBackgroundColor = HudStyle.selected
    installColors(palette.colors.map { hex in
      let c = NSColor(hex: hex)
      return Color(red: UInt16(c.redComponent * 65535), green: UInt16(c.greenComponent * 65535), blue: UInt16(c.blueComponent * 65535))
    })
  }
}

/// This view paints highlights only. The live terminal continues to own input,
/// render ANSI colors, and maintain its original dimensions and attachment.
private final class SelectionOverlay: NSView {
  var rectangles: [NSRect] = [] { didSet { needsDisplay = true } }
  override var isFlipped: Bool { true }
  override func hitTest(_ point: NSPoint) -> NSView? { nil }
  override func draw(_ dirtyRect: NSRect) {
    NSColor(calibratedRed: 0.35, green: 0.55, blue: 0.86, alpha: 0.30).setFill()
    rectangles.forEach { $0.fill() }
  }
}

final class LiveSelection {
  private weak var terminal: HudTerminal?
  private let overlay = SelectionOverlay()
  private var timer: Timer?
  private var frame: [String]
  private var document: [String]
  private var frameStart = 0, bodyHead = 0
  private var anchorRow: Int, anchorColumn: Int
  private var point: NSPoint
  private var initialFrame = true, waiting = false, paused = false
  private var unchangedTicks = 0
  private var stopped = false
  private var dimensions: TerminalDimensions
  private var widths: [String: [Int]] = [:]

  init(terminal: HudTerminal, rows: [TerminalVisibleRowSnapshot], anchor: NSPoint) {
    self.terminal = terminal
    let textRows = rows.map { $0.text.replacingOccurrences(of: #"\s+$"#, with: "", options: .regularExpression) }
    frame = textRows; document = textRows; point = anchor
    dimensions = terminal.terminalDimensions
    let height = terminal.selectionCellSize.height
    let width = terminal.selectionCellSize.width
    anchorRow = max(0, min(rows.count - 1, Int(anchor.y / height)))
    anchorColumn = max(0, Int(anchor.x / width))
    for (row, text) in zip(rows, textRows) { widths[text] = row.cellWidths.filter { $0 > 0 } }
    overlay.frame = terminal.bounds
    overlay.autoresizingMask = [.width, .height]
    terminal.addSubview(overlay)
    let timer = Timer(timeInterval: 0.18, repeats: true) { [weak self] _ in self?.tick() }
    RunLoop.main.add(timer, forMode: .common)
    self.timer = timer
  }
  func move(to point: NSPoint) { self.point = point; update() }
  func stop() {
    stopped = true
    timer?.invalidate(); timer = nil
    overlay.removeFromSuperview()
  }
  private func tick() {
    guard !stopped, !waiting, !paused, let terminal, terminal.window?.isVisible == true,
      terminal.terminalDimensions.cols == dimensions.cols, terminal.terminalDimensions.rows == dimensions.rows else {
      if terminal?.window?.isVisible != true { stop() }
      return
    }
    let rowHeight = terminal.selectionCellSize.height
    let direction = point.y < rowHeight ? -1 : point.y >= terminal.bounds.height - rowHeight ? 1 : 0
    guard direction != 0 else { return }
    waiting = true
    terminal.scrollCLI(direction)
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.12) { [weak self] in
      guard let self, !self.stopped, let terminal = self.terminal else { return }
      self.waiting = false
      let snapshot = terminal.terminalStateSnapshot().visibleRows
      let rows = terminal.visibleTextRows()
      for (row, text) in zip(snapshot, rows) { self.widths[text] = row.cellWidths.filter { $0 > 0 } }
      guard rows != self.frame else {
        self.unchangedTicks += 1
        if self.initialFrame && self.unchangedTicks >= 3 { _ = terminal.fallbackToRetainedHistory() }
        return
      }
      self.unchangedTicks = 0
      guard let overlap = ScrollOverlap.match(self.frame, rows, direction: direction) else {
        self.paused = true
        terminal.onSelectionStatus?("Selection paused: CLI text changed without a matching scroll overlap")
        return
      }
      if self.initialFrame {
        self.document = overlap.old
        self.frameStart = 0
        self.anchorRow = max(0, min(overlap.old.count - 1, self.anchorRow - overlap.head))
        self.initialFrame = false
      }
      var start = self.frameStart + overlap.shift
      let prepend = max(0, -start)
      let append = max(0, start + overlap.new.count - self.document.count)
      guard self.document.count + prepend + append <= 20000 else {
        self.paused = true
        terminal.onSelectionStatus?("Selection reached the 20,000-line capture limit")
        return
      }
      if prepend > 0 {
        self.document.insert(contentsOf: overlap.new.prefix(prepend), at: 0)
        self.anchorRow += prepend; start = 0
      }
      if append > 0 { self.document.append(contentsOf: overlap.new.suffix(append)) }
      self.frameStart = start; self.bodyHead = overlap.head; self.frame = rows
      self.update()
    }
  }
  private func update() {
    guard !stopped, let terminal, !document.isEmpty else { return }
    let cw = terminal.selectionCellSize.width
    let ch = terminal.selectionCellSize.height
    let row = max(0, min(document.count - 1,
      frameStart + Int(max(0, min(point.y, terminal.bounds.height - 1)) / ch) - bodyHead))
    var column = max(0, Int(point.x / cw))
    if point.y < 0 { column = 0 }
    if point.y >= terminal.bounds.height { column = dimensions.cols }
    let anchor = (row: anchorRow, col: anchorColumn), end = (row: row, col: column)
    let forward = anchor.row < end.row || (anchor.row == end.row && anchor.col <= end.col)
    let first = forward ? anchor : end, last = forward ? end : anchor
    var lines = Array(document[first.row...last.row])
    // Convert terminal cell offsets to character offsets, including CJK/emoji widths.
    func slice(_ line: String, from: Int, to: Int) -> String {
      var cells = 0, result = ""
      let cellWidths = widths[line] ?? []
      for (index, char) in line.enumerated() {
        let width = index < cellWidths.count ? cellWidths[index] : 1
        if cells >= from && cells < to { result.append(char) }
        cells += width
      }
      return result
    }
    if lines.count == 1 { lines[0] = slice(lines[0], from: first.col, to: last.col) }
    else {
      lines[0] = slice(lines[0], from: first.col, to: Int.max)
      lines[lines.count - 1] = slice(lines[lines.count - 1], from: 0, to: last.col)
    }
    let text = lines.joined(separator: "\n")
    if !text.isEmpty {
      NSPasteboard.general.clearContents()
      NSPasteboard.general.setString(text, forType: .string)
    }
    overlay.rectangles = (0..<dimensions.rows).compactMap { visibleRow in
      let index = frameStart + visibleRow - bodyHead
      guard index >= first.row && index <= last.row else { return nil }
      let left = index == first.row ? CGFloat(first.col) * cw : 0
      let right = index == last.row ? CGFloat(last.col) * cw : terminal.bounds.width
      return NSRect(x: left, y: CGFloat(visibleRow) * ch, width: max(0, right-left), height: ch)
    }
  }
}
