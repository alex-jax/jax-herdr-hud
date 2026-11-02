import Darwin
import Foundation
import HudCore

func expectEqual<T: Equatable>(_ a: T, _ b: T, file: StaticString = #file, line: UInt = #line) {
  precondition(a == b, "Expected \(a) == \(b)", file: file, line: line)
}
func expectNotEqual<T: Equatable>(_ a: T, _ b: T) { precondition(a != b) }
func expectTrue(_ value: Bool) { precondition(value) }
func expectFalse(_ value: Bool) { precondition(!value) }
func expectNil<T>(_ value: T?) { precondition(value == nil) }
func expectAtLeast<T: Comparable>(_ a: T, _ b: T) { precondition(a >= b) }
func expectError<T>(_ body: @autoclosure () throws -> T, _ handler: (Error) -> Void = { _ in }) {
  do {
    _ = try body()
    preconditionFailure("Expected error")
  } catch { handler(error) }
}

final class CoreTests {
  func testAttentionTransitions() {
    expectNil(attention(previous: nil, current: "idle"))
    expectNil(attention(previous: "unknown", current: "idle"))
    expectEqual(attention(previous: "working", current: "idle"), "Finished")
    expectEqual(attention(previous: nil, current: "blocked"), "Needs your input")
    expectEqual(attention(previous: "idle", current: "done"), "Finished")
    expectNil(attention(previous: "done", current: "done"))
  }
  func testEnvironmentAndExplicitExecutable() throws {
    let env = Host.environment([
      "HOME": "/test", "PATH": "/bin", "HERDR_SESSION": "nested", "TERM": "bad", "TOKEN": "keep",
    ])
    expectNil(env["HERDR_SESSION"])
    expectEqual(env["TERM"], "xterm-256color")
    expectEqual(env["TOKEN"], "keep")
    expectTrue(env["PATH"]!.contains("/opt/homebrew/bin"))
    expectError(try Host.executable("relative/herdr"))
    expectError(try Host.executable("/usr/bin"))
    expectError(try Host.executable("/does-not-exist", environment: env))
  }
  func testPreferencesRecoverInvalidFields() throws {
    let p = try JSONDecoder().decode(
      Preferences.self,
      from: Data(#"{"appearance":4,"sidebarWidth":"bad","spacesExpanded":false,"palette":4}"#.utf8))
    expectEqual(p.appearance, "dark")
    expectEqual(p.sidebarWidth, 245)
    expectFalse(p.spacesExpanded)
    expectEqual(p.palette, "Vs Code")
  }
  func testStreamingColorsAndControls() {
    let input =
      "a\u{1b}[38;2;2;3;4;48;2;5;6;7mred\u{1b}[0m\u{1b}]4;1;#fff\u{7}\u{1b}[?1006h\u{1b}]11;?\u{7}"
    let expected = "a\u{1b}[38;2;2;3;4;48;2;5;6;7mred\u{1b}[0m\u{1b}[?1006h\u{1b}]11;?\u{7}"
    let bytes = Array(input.utf8)
    for split in 0...bytes.count {
      let f = DisplayFilter()
      let result = f.feed(bytes[..<split]) + f.feed(bytes[split...])
      expectEqual(String(decoding: result, as: UTF8.self), expected)
    }
    let f = DisplayFilter()
    expectEqual(
      String(
        decoding: f.feed(Array("\u{1b}[38:2::10:20:30;48:2::1:2:3m".utf8)[...]), as: UTF8.self),
      "\u{1b}[38:2::10:20:30;48:2::1:2:3m")
  }
  func testReadableHighlights() {
    let controls = [
      "\u{1b}[30;47mselected\u{1b}[0m", "\u{1b}[31;40mred on black",
      "\u{1b}[38;5;16;48;5;231m", "\u{1b}[38:2::0:0:0;48:2::255:255:255m",
      "\u{1b}[7mreverse\u{1b}[27m", "\u{1b}[?2004h\u{1b}[200~paste\u{1b}[201~",
      "\u{1b}]8;;https://example.com\u{7}link\u{1b}]8;;\u{7}",
      "\u{1b}Pprivate;payload\u{1b}\\", "\u{1b}]104\u{7}"
    ]
    for text in controls {
      let bytes = Array(text.utf8)
      for split in 0...bytes.count {
        let f = DisplayFilter()
        let expected = text == "\u{1b}]104\u{7}" ? "" : text
        expectEqual(String(decoding: f.feed(bytes[..<split]) + f.feed(bytes[split...]), as: UTF8.self), expected)
      }
    }
    expectEqual(Preferences().palette, "Vs Code")
    let saved = try! JSONDecoder().decode(Preferences.self, from: Data(#"{"palette":"nord","appearance":"light"}"#.utf8))
    expectEqual(saved.palette, "nord")
    expectEqual(saved.appearance, "light")
  }
  func testHistoryOverlap() {
    let before = ["header", "a", "b", "c", "d", "input", "footer"]
    let after = ["header", "c", "d", "e", "f", "input", "footer"]
    let down = ScrollOverlap.match(before, after, direction: 1)!
    expectEqual(down.head, 1); expectEqual(down.shift, 2)
    expectEqual(down.old, ["a", "b", "c", "d"])
    let up = ScrollOverlap.match(after, before, direction: -1)!
    expectEqual(up.shift, -2)
    expectNil(ScrollOverlap.match(["a", "b", "c"], ["x", "y", "z"], direction: 1))
    expectNil(ScrollOverlap.match(["a", "", ""], ["", "", "b"], direction: 1))
    let old = ["header"] + (0..<20).map { "line \($0)" } + ["Back to bottom", "input", "earlier messages"]
    let new = ["header"] + (3..<23).map { "line \($0)" } + ["", "input", "shortcuts"]
    let changed = ScrollOverlap.match(old, new, direction: 1)!
    expectEqual(changed.head, 1); expectEqual(changed.shift, 3)
    expectEqual(changed.old, Array(old[1...20]))
    expectEqual(ScrollOverlap.match(new, old, direction: -1)!.shift, -3)
  }
  func testSocketFragmentationAndErrors() throws {
    let directory = URL(fileURLWithPath: "/tmp/hud-socket-" + UUID().uuidString.prefix(8))
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: directory) }
    func serve(_ response: String) throws -> SocketConnection {
      let path = directory.appendingPathComponent(UUID().uuidString.prefix(8) + ".sock").path
      let fd = socket(AF_UNIX, SOCK_STREAM, 0)
      expectAtLeast(fd, 0)
      var addr = sockaddr_un()
      addr.sun_family = sa_family_t(AF_UNIX)
      addr.sun_len = UInt8(MemoryLayout<sockaddr_un>.size)
      withUnsafeMutableBytes(of: &addr.sun_path) { $0.copyBytes(from: Array(path.utf8) + [0]) }
      let rc = withUnsafePointer(to: &addr) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
          bind(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
        }
      }
      expectEqual(rc, 0)
      expectEqual(listen(fd, 1), 0)
      DispatchQueue.global().async {
        let peer = accept(fd, nil, nil)
        defer {
          close(peer)
          close(fd)
        }
        for byte in response.utf8 {
          var b = byte
          _ = write(peer, &b, 1)
        }
      }
      return try SocketConnection(path: path)
    }
    let c = try serve("{\"result\":{\"ok\":true}}\n{\"result\":{\"second\":true}}\n")
    let first = try c.read()
    expectEqual((first["result"] as? [String: Bool])?["ok"], true)
    let second = try c.read()
    expectEqual((second["result"] as? [String: Bool])?["second"], true)
    let error = try serve("{\"error\":{\"message\":\"ownership denied\"}}\n")
    expectError(try error.read()) {
      expectTrue($0.localizedDescription.contains("ownership denied"))
    }
    let invalid = try serve("[]\n")
    expectError(try invalid.read())
    let eof = try serve("{}")
    expectError(try eof.read())
  }
  func testSnapshotValidationAndIdentity() throws {
    expectError(
      try JSONDecoder().decode(
        Snapshot.self, from: Data(#"{"panes":[{}],"workspaces":[],"tabs":[]}"#.utf8)))
    let snap = try JSONDecoder().decode(
      Snapshot.self,
      from: Data(
        #"{"panes":[{"pane_id":"p1","terminal_id":"t1","workspace_id":"w1","tab_id":"tab1","agent_status":"idle"}],"workspaces":[{"workspace_id":"w1","label":"Space 1"}],"tabs":[{"tab_id":"tab1","label":"First"}]}"#
          .utf8))
    expectFalse(snap.canClose(pane: snap.panes[0]))
    expectFalse(snap.canClose(workspace: snap.workspaces[0]))
    expectEqual(snap.label(for: snap.panes[0]), "First")
    expectNotEqual(TerminalKey("a", "1"), TerminalKey("b", "1"))
  }
}

@main struct CoreCheckRunner {
  static func main() throws {
    let suite = CoreTests()
    suite.testAttentionTransitions()
    try suite.testEnvironmentAndExplicitExecutable()
    try suite.testPreferencesRecoverInvalidFields()
    suite.testStreamingColorsAndControls()
    suite.testReadableHighlights()
    suite.testHistoryOverlap()
    try suite.testSocketFragmentationAndErrors()
    try suite.testSnapshotValidationAndIdentity()
    print(
      "PASS: attention, environment/discovery, preferences, streaming colors/highlight contrast, socket fragmentation/errors, snapshot identity/guards"
    )
  }
}
