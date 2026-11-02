import Darwin
import Foundation

private final class BoundedOutput: @unchecked Sendable {
  private let lock = NSLock()
  private var bytes = Data()
  private var overflow = false
  var data: Data {
    lock.lock()
    defer { lock.unlock() }
    return bytes
  }
  var exceeded: Bool {
    lock.lock()
    defer { lock.unlock() }
    return overflow
  }
  func append(_ data: Data) {
    lock.lock()
    defer { lock.unlock() }
    let available = max(0, 8 * 1024 * 1024 - bytes.count)
    if data.count > available { overflow = true }
    bytes.append(data.prefix(available))
  }
}

public enum Host {
  public static func environment(_ source: [String: String] = ProcessInfo.processInfo.environment)
    -> [String: String]
  {
    var env = source.filter {
      !$0.key.hasPrefix("HERDR_") && !$0.key.hasPrefix("_HUD_") && !$0.key.hasPrefix("SNAP")
    }
    env["TERM"] = "xterm-256color"
    let paths = (env["PATH"] ?? "/usr/bin:/bin:/usr/sbin:/sbin").split(separator: ":").map(
      String.init)
    let extra = [
      FileManager.default.homeDirectoryForCurrentUser.path + "/.local/bin", "/opt/homebrew/bin",
      "/usr/local/bin",
    ]
    env["PATH"] = (paths + extra.filter { !paths.contains($0) }).joined(separator: ":")
    return env
  }
  public static func executable(
    _ selected: String = "", environment: [String: String] = Host.environment()
  ) throws -> String {
    let fm = FileManager.default
    if !selected.isEmpty {
      var directory: ObjCBool = false
      guard selected.hasPrefix("/"), fm.fileExists(atPath: selected, isDirectory: &directory),
        !directory.boolValue, fm.isExecutableFile(atPath: selected)
      else { throw HudError.message("Choose an absolute path to an executable Herdr file.") }
      return selected
    }
    let home = environment["HOME"] ?? fm.homeDirectoryForCurrentUser.path
    for path in [home + "/.local/bin/herdr"]
      + (environment["PATH"] ?? "").split(separator: ":").map({ String($0) + "/herdr" })
    {
      var directory: ObjCBool = false
      if fm.fileExists(atPath: path, isDirectory: &directory), !directory.boolValue,
        fm.isExecutableFile(atPath: path)
      {
        return path
      }
    }
    throw HudError.message(
      "Herdr was not found. Install Herdr 0.9.1 or select its executable in Settings.")
  }
  public static func run(_ executable: String, _ arguments: [String], timeout: TimeInterval = 5)
    throws -> Data
  {
    // Monitor calls this repeatedly from a long-lived dispatch block. Its outer
    // autorelease pool does not drain between polls, so scope Foundation's
    // temporary Process/Pipe objects to one invocation.
    try autoreleasepool {
      try collectOutput(executable, arguments, timeout: timeout)
    }
  }
  private static func collectOutput(
    _ executable: String, _ arguments: [String], timeout: TimeInterval
  ) throws -> Data {
    let process = Process()
    let output = Pipe()
    let errors = Pipe()
    let pipes = [output, errors]
    // Own descriptor cleanup explicitly, including launch errors and timeouts;
    // ARC/autorelease timing must not determine how long a pipe remains open.
    defer {
      for pipe in pipes {
        try? pipe.fileHandleForReading.close()
        try? pipe.fileHandleForWriting.close()
      }
    }
    process.executableURL = URL(fileURLWithPath: executable)
    process.arguments = arguments
    process.environment = environment()
    process.standardOutput = output
    process.standardError = errors
    let group = DispatchGroup()
    let outputBuffer = BoundedOutput()
    let errorBuffer = BoundedOutput()
    try process.run()
    // Only the child writes output. Keeping a parent writer alive can prevent
    // EOF and leave a reader blocked after the command has exited.
    for pipe in pipes { try? pipe.fileHandleForWriting.close() }
    for (pipe, buffer) in [(output, outputBuffer), (errors, errorBuffer)] {
      group.enter()
      DispatchQueue.global().async {
        autoreleasepool {
          defer { group.leave() }
          while let data = try? pipe.fileHandleForReading.read(upToCount: 65536), !data.isEmpty {
            buffer.append(data)
          }
        }
      }
    }
    let deadline = Date().addingTimeInterval(timeout)
    while process.isRunning && Date() < deadline { Thread.sleep(forTimeInterval: 0.02) }
    if process.isRunning {
      process.terminate()
      Thread.sleep(forTimeInterval: 0.05)
      if process.isRunning { kill(process.processIdentifier, SIGKILL) }
      process.waitUntilExit()
      throw HudError.message("Herdr command timed out.")
    }
    guard group.wait(timeout: .now() + 1) == .success else {
      throw HudError.message("Herdr command output did not close.")
    }
    guard process.terminationStatus == 0 else {
      throw HudError.message(
        String(data: errorBuffer.data, encoding: .utf8) ?? "Herdr command failed.")
    }
    guard !outputBuffer.exceeded else { throw HudError.message("Herdr response exceeded 8 MiB.") }
    return outputBuffer.data
  }
}

public final class SocketConnection {
  private var fd: Int32
  private var pending = Data()
  private let lock = NSLock()
  public init(path: String, timeout: Int = 3) throws {
    var address = sockaddr_un()
    let bytes = Array(path.utf8)
    guard bytes.count < MemoryLayout.size(ofValue: address.sun_path) else {
      throw HudError.message("Herdr socket path is too long.")
    }
    fd = Darwin.socket(AF_UNIX, SOCK_STREAM, 0)
    guard fd >= 0 else { throw HudError.message("Could not open Herdr socket.") }
    address.sun_family = sa_family_t(AF_UNIX)
    address.sun_len = UInt8(MemoryLayout<sockaddr_un>.size)
    withUnsafeMutableBytes(of: &address.sun_path) { buffer in buffer.copyBytes(from: bytes + [0]) }
    var tv = timeval(tv_sec: timeout, tv_usec: 0)
    var one: Int32 = 1
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, socklen_t(MemoryLayout.size(ofValue: tv)))
    setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, socklen_t(MemoryLayout.size(ofValue: tv)))
    setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, socklen_t(MemoryLayout.size(ofValue: one)))
    let rc = withUnsafePointer(to: &address) {
      $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
        Darwin.connect(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
      }
    }
    if rc != 0 {
      Darwin.close(fd)
      fd = -1
      throw HudError.message("Could not connect to Herdr: \(String(cString: strerror(errno)))")
    }
  }
  deinit { if fd >= 0 { Darwin.close(fd) } }
  public func cancel() {
    lock.lock()
    defer { lock.unlock() }
    if fd >= 0 { Darwin.shutdown(fd, SHUT_RDWR) }
  }
  public func send(_ object: [String: Any]) throws {
    var data = try JSONSerialization.data(withJSONObject: object)
    data.append(10)
    try data.withUnsafeBytes { buffer in
      var offset = 0
      while offset < buffer.count {
        let count = Darwin.write(
          fd, buffer.baseAddress!.advanced(by: offset), buffer.count - offset)
        if count < 0 && errno == EINTR { continue }
        guard count > 0 else { throw HudError.message("Herdr socket write failed.") }
        offset += count
      }
    }
  }
  public func read() throws -> [String: Any] {
    while true {
      if let end = pending.firstIndex(of: 10) {
        let line = pending.prefix(upTo: end)
        pending.removeSubrange(...end)
        guard line.count <= 8 * 1024 * 1024,
          let value = try JSONSerialization.jsonObject(with: line) as? [String: Any]
        else { throw HudError.message("Invalid Herdr response.") }
        if let error = value["error"] {
          throw HudError.message(
            (error as? [String: Any])?["message"] as? String ?? String(describing: error))
        }
        return value
      }
      guard pending.count <= 8 * 1024 * 1024 else {
        throw HudError.message("Herdr response exceeded 8 MiB.")
      }
      var bytes = [UInt8](repeating: 0, count: 65536)
      let count = Darwin.read(fd, &bytes, bytes.count)
      if count < 0 && errno == EINTR { continue }
      guard count > 0 else {
        throw HudError.message(
          count == 0 ? "Herdr disconnected." : "Herdr read timed out or failed.")
      }
      pending.append(contentsOf: bytes.prefix(count))
    }
  }
}

public final class Backend: Sendable {
  public let selectedPath: String
  public let defaultSession: String
  public let isolated: Bool
  public init(path: String = "", defaultSession: String = "default", isolated: Bool = false) {
    selectedPath = path
    self.defaultSession = defaultSession
    self.isolated = isolated
  }
  public func executable() throws -> String { try Host.executable(selectedPath) }
  public func check() throws -> String {
    let text = String(decoding: try Host.run(executable(), ["--version"]), as: UTF8.self)
      .trimmingCharacters(in: .whitespacesAndNewlines)
    guard text.hasPrefix("herdr ") else {
      throw HudError.message("The selected file did not identify itself as Herdr.")
    }
    return text
  }
  public func sessions() throws -> [Session] {
    struct Result: Decodable { let sessions: [Session] }
    return try JSONDecoder().decode(
      Result.self, from: Host.run(executable(), ["session", "list", "--json"])
    ).sessions.filter { $0.running && (!isolated || $0.name == defaultSession) }
  }
  public func request(_ session: Session, _ method: String, _ params: [String: Any] = [:]) throws
    -> [String: Any]
  {
    let connection = try SocketConnection(path: session.socket_path)
    try connection.send(["id": "hud", "method": method, "params": params])
    guard let result = try connection.read()["result"] as? [String: Any] else {
      throw HudError.message("Unsupported Herdr reply: missing result.")
    }
    return result
  }
  public func snapshot(_ session: Session) throws -> Snapshot {
    let result = try request(session, "session.snapshot")
    guard let value = result["snapshot"] else { throw HudError.message("Missing Herdr snapshot.") }
    return try JSONDecoder().decode(
      Snapshot.self, from: JSONSerialization.data(withJSONObject: value))
  }
  public func ensureDefault(initialize: Bool = true) throws -> Session {
    if let session = try sessions().first(where: { $0.name == defaultSession }) {
      if initialize { try initializeEmpty(session) }
      return session
    }
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/nohup")
    process.arguments = [try executable(), "--session", defaultSession, "server"]
    process.environment = Host.environment()
    process.standardInput = FileHandle.nullDevice
    let logs = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(
      "Library/Logs/Herdr Hud")
    try FileManager.default.createDirectory(at: logs, withIntermediateDirectories: true)
    let log = logs.appendingPathComponent("server-start.log")
    if !FileManager.default.fileExists(atPath: log.path) {
      FileManager.default.createFile(atPath: log.path, contents: nil)
    }
    let handle = try FileHandle(forWritingTo: log)
    try handle.seekToEnd()
    defer { try? handle.close() }
    process.standardOutput = handle
    process.standardError = handle
    try process.run()
    let deadline = Date().addingTimeInterval(10)
    while Date() < deadline {
      if let session = try sessions().first(where: { $0.name == defaultSession }) {
        if initialize { try initializeEmpty(session) }
        return session
      }
      if !process.isRunning { break }
      Thread.sleep(forTimeInterval: 0.15)
    }
    throw HudError.message(
      "Herdr did not become ready. See ~/Library/Logs/Herdr Hud/server-start.log.")
  }
  private func initializeEmpty(_ session: Session) throws {
    if try snapshot(session).panes.isEmpty {
      _ = try request(
        session, "workspace.create", ["cwd": FileManager.default.homeDirectoryForCurrentUser.path])
    }
  }
}

public final class Monitor {
  private let backend: Backend
  private let lock = NSLock()
  private var stopped = false
  private var connections: [String: SocketConnection] = [:]
  private var watching = Set<String>()
  public var onSessions: (([Session]) -> Void)?
  public var onSnapshot: ((Session, Snapshot) -> Void)?
  public var onEvent: ((Session, [String: Any]) -> Void)?
  public var onError: ((String) -> Void)?
  public init(backend: Backend) { self.backend = backend }
  private var running: Bool {
    lock.lock()
    defer { lock.unlock() }
    return !stopped
  }
  public func stop() {
    lock.lock()
    stopped = true
    let active = Array(connections.values)
    lock.unlock()
    active.forEach { $0.cancel() }
  }
  public func start() {
    DispatchQueue.global().async { [self] in
      while running {
        do {
          let sessions = try backend.sessions()
          if !running { break }
          onSessions?(sessions)
          lock.lock()
          let paths = Set(sessions.map(\.socket_path))
          let removed = connections.filter { !paths.contains($0.key) }.map(\.value)
          let added = sessions.filter { !watching.contains($0.socket_path) }
          added.forEach { watching.insert($0.socket_path) }
          lock.unlock()
          removed.forEach { $0.cancel() }
          for session in added { DispatchQueue.global().async { self.watch(session) } }
        } catch { if running { onError?(error.localizedDescription) } }
        for _ in 0..<30 {
          if !running { break }
          Thread.sleep(forTimeInterval: 0.1)
        }
      }
    }
  }
  private func watch(_ session: Session) {
    defer {
      lock.lock()
      watching.remove(session.socket_path)
      connections.removeValue(forKey: session.socket_path)
      lock.unlock()
    }
    while running {
      do {
        let snap = try backend.snapshot(session)
        if !running { return }
        onSnapshot?(session, snap)
        let connection = try SocketConnection(path: session.socket_path, timeout: 10)
        lock.lock()
        connections[session.socket_path] = connection
        lock.unlock()
        if !running {
          connection.cancel()
          return
        }
        var subscriptions: [[String: Any]] = [
          "pane.created", "pane.closed", "pane.updated", "pane.exited", "pane.moved",
          "workspace.renamed", "tab.renamed",
        ].map { ["type": $0] }
        subscriptions += snap.panes.map {
          ["type": "pane.agent_status_changed", "pane_id": $0.pane_id]
        }
        try connection.send([
          "id": "events", "method": "events.subscribe", "params": ["subscriptions": subscriptions],
        ])
        let ack = try connection.read()
        guard ack["result"] is [String: Any] else {
          throw HudError.message("Invalid Herdr subscription acknowledgement.")
        }
        while running {
          let event = try connection.read()
          if !running { return }
          guard event["event"] != nil else { continue }
          onEvent?(session, event)
          let next = try backend.snapshot(session)
          onSnapshot?(session, next)
          if Set(next.panes.map(\.pane_id)) != Set(snap.panes.map(\.pane_id)) { break }
        }
      } catch {
        if !running { return }
        if !error.localizedDescription.contains("timed out") {
          onError?("Reconnecting to " + session.name + ": " + error.localizedDescription)
        }
        // Timeout reconciliation also rediscovers vanished/restarted sockets.
        if (try? backend.sessions().contains(where: { $0.socket_path == session.socket_path }))
          != true
        {
          return
        }
        Thread.sleep(forTimeInterval: 0.5)
      }
    }
  }
}
