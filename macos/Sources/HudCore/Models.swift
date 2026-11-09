import Foundation

public struct Session: Codable, Equatable, Sendable {
  public let name: String
  public let socket_path: String
  public let running: Bool
  public init(name: String, socket_path: String, running: Bool) {
    self.name = name
    self.socket_path = socket_path
    self.running = running
  }
}
public struct Pane: Decodable, Equatable, Sendable {
  public let pane_id, terminal_id, workspace_id, tab_id, agent_status: String
  public let label, tab_label, agent, cwd, foreground_cwd, title, process_title, terminal_title_stripped: String?
  public var displayName: String {
    [label, tab_label, title, process_title].compactMap { $0 }.first { !$0.isEmpty } ?? "Terminal"
  }
  public var isAgent: Bool { !(agent ?? "").isEmpty }
}
public struct Workspace: Decodable, Equatable, Sendable {
  public let workspace_id: String
  public let label: String?
}
public struct Tab: Decodable, Equatable, Sendable {
  public let tab_id: String
  public let label: String?
}
public struct Snapshot: Decodable, Equatable, Sendable {
  public let panes: [Pane]
  public let workspaces: [Workspace]
  public let tabs: [Tab]
  public func label(for pane: Pane) -> String {
    let tab = tabs.first { $0.tab_id == pane.tab_id }?.label
    return [pane.label, pane.tab_label, tab, pane.title, pane.process_title].compactMap { $0 }.first
    { !$0.isEmpty } ?? "Terminal"
  }
  public func canClose(pane: Pane) -> Bool {
    guard let first = workspaces.first else { return false }
    return pane.workspace_id != first.workspace_id
      || panes.filter { $0.workspace_id == first.workspace_id }.count > 1
  }
  public func canClose(workspace: Workspace) -> Bool {
    workspaces.first?.workspace_id != workspace.workspace_id
  }
}
public struct TerminalKey: Hashable, Sendable {
  public let socket: String
  public let id: String
  public init(_ socket: String, _ id: String) {
    self.socket = socket
    self.id = id
  }
}
public struct SpaceKey: Hashable, Sendable {
  public let socket: String
  public let id: String
  public init(_ socket: String, _ id: String) {
    self.socket = socket
    self.id = id
  }
}
public func attention(previous: String?, current: String) -> String? {
  if current == "blocked" && previous != current { return "Needs your input" }
  if current == "done" && previous != current { return "Finished" }
  if previous == "working" && current == "idle" { return "Finished" }
  return nil
}
public enum HudError: LocalizedError {
  case message(String)
  public var errorDescription: String? {
    if case .message(let s) = self { return s }
    return nil
  }
}
public struct Preferences: Codable {
  public var herdrPath = ""
  public var appearance = "dark"
  public var palette = "Vs Code"
  public var windowFrame: [Double] = []
  public var bubbleFrame: [Double] = []
  public var sidebarWidth: Double = 245
  public var sectionPosition: Double = 260
  public var spacesExpanded = true
  public var agentsExpanded = true
  public init() {}
  enum CodingKeys: CodingKey {
    case herdrPath, appearance, palette, windowFrame, bubbleFrame, sidebarWidth, sectionPosition,
      spacesExpanded, agentsExpanded
  }
  public init(from decoder: Decoder) throws {
    self.init()
    let c = try decoder.container(keyedBy: CodingKeys.self)
    herdrPath = (try? c.decode(String.self, forKey: .herdrPath)) ?? ""
    appearance = (try? c.decode(String.self, forKey: .appearance)) ?? "dark"
    if !["dark", "light", "system"].contains(appearance) { appearance = "dark" }
    palette = (try? c.decode(String.self, forKey: .palette)) ?? "Vs Code"
    windowFrame = (try? c.decode([Double].self, forKey: .windowFrame)) ?? []
    bubbleFrame = (try? c.decode([Double].self, forKey: .bubbleFrame)) ?? []
    sidebarWidth = (try? c.decode(Double.self, forKey: .sidebarWidth)) ?? 245
    sidebarWidth = sidebarWidth.isFinite ? min(600, max(0, sidebarWidth)) : 245
    sectionPosition = (try? c.decode(Double.self, forKey: .sectionPosition)) ?? 260
    sectionPosition = sectionPosition.isFinite ? max(60, sectionPosition) : 260
    spacesExpanded = (try? c.decode(Bool.self, forKey: .spacesExpanded)) ?? true
    agentsExpanded = (try? c.decode(Bool.self, forKey: .agentsExpanded)) ?? true
  }
  public static var directory: URL {
    #if DEBUG
      if let path = ProcessInfo.processInfo.environment["HUD_TEST_CONFIG"] {
        return URL(fileURLWithPath: path)
      }
    #endif
    return FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(
      "Library/Application Support/Herdr Hud")
  }
  public static func load() -> Preferences {
    (try? JSONDecoder().decode(
      Self.self, from: Data(contentsOf: directory.appendingPathComponent("settings.json"))))
      ?? Self()
  }
  public func save() throws {
    try FileManager.default.createDirectory(at: Self.directory, withIntermediateDirectories: true)
    try JSONEncoder().encode(self).write(
      to: Self.directory.appendingPathComponent("settings.json"), options: .atomic)
  }
}

/// Identity explicitly supplied by a shell in its terminal title.
public func titleIdentity(_ title: String?) -> String? {
  guard let title, let range = title.range(
    of: #"^[A-Za-z0-9_][A-Za-z0-9_.-]*@[A-Za-z0-9][A-Za-z0-9_.-]*(?=$|[: /])"#,
    options: .regularExpression) else { return nil }
  return String(title[range])
}
