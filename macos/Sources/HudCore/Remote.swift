import Foundation
import Darwin

public struct MachineProfile: Decodable, Equatable {
  public let id, label, target, session: String
  public let enabled: Bool
}

public enum RemoteSSH {
  public static func quote(_ argument: String) -> String {
    "'" + argument.replacingOccurrences(of: "'", with: "'\\''") + "'"
  }
  public static func arguments(_ target: String) throws -> [String] {
    guard !target.isEmpty, !target.hasPrefix("-"), !target.contains("\0") else {
      throw HudError.message("Invalid SSH target")
    }
    return ["-o", "ControlMaster=no", "-o", "ControlPath=none", "-o", "BatchMode=yes",
      "-o", "ConnectTimeout=5", "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2", target]
  }
  public static func attach(_ session: Session, terminal: String, executable: String) throws -> (String, [String]) {
    guard let target = session.remoteTarget else {
      return (executable, ["--session", session.name, "terminal", "attach", terminal])
    }
    guard let remote = session.remoteExecutable, let name = session.remoteSession else {
      throw HudError.message("Remote machine is not connected yet")
    }
    let base = try arguments(target)
    return ("/usr/bin/ssh", Array(base.dropLast()) + ["-tt", target,
      [remote, "--session", name, "terminal", "attach", terminal].map(quote).joined(separator: " ")])
  }
}

public final class RemoteMachine {
  public let profile: MachineProfile
  private let lock = NSLock()
  private var stopped = false
  private var process: Process?
  private var executable: String?
  private var label: String
  private let directory: URL
  private let backend: Backend
  public var onSnapshot: ((Session, Snapshot) -> Void)?
  public var onError: ((Session, String) -> Void)?
  public var session: Session {
    lock.lock(); defer { lock.unlock() }
    return Session(name: label + "/" + profile.session,
      socket_path: directory.appendingPathComponent("api.sock").path, running: true,
      remoteTarget: profile.target, remoteSession: profile.session, remoteExecutable: executable)
  }
  public init(profile: MachineProfile, backend: Backend) throws {
    self.profile = profile; self.backend = backend; self.label = profile.label
    directory = URL(fileURLWithPath: "/tmp/hud-ssh-" + UUID().uuidString)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
      attributes: [.posixPermissions: 0o700])
  }
  public func rename(_ label: String) { lock.lock(); self.label = label; lock.unlock() }
  private var running: Bool { lock.lock(); defer { lock.unlock() }; return !stopped }
  public func stop() {
    lock.lock(); stopped = true; let child = process; lock.unlock()
    if let child, child.isRunning { child.terminate() }
  }
  private func pause(_ seconds: Int) {
    for _ in 0..<(seconds * 10) { if !running { return }; Thread.sleep(forTimeInterval: 0.1) }
  }
  public func start() {
    DispatchQueue.global().async { [self] in
      defer { try? FileManager.default.removeItem(at: directory) }
      while running {
        autoreleasepool {
          var tunnel: Process?
          defer {
            if let tunnel, tunnel.isRunning {
              tunnel.terminate()
              let deadline = Date().addingTimeInterval(2)
              while tunnel.isRunning && Date() < deadline { Thread.sleep(forTimeInterval: 0.05) }
              if tunnel.isRunning { kill(tunnel.processIdentifier, SIGKILL) }
              tunnel.waitUntilExit()
            }
            try? FileManager.default.removeItem(atPath: session.socket_path)
          }
          do {
            let script = "if [ -x \"$HOME/.local/bin/herdr\" ]; then h=\"$HOME/.local/bin/herdr\"; else h=$(command -v herdr) || exit 127; fi; printf '%s\\n' \"$h\"; \"$h\" session list --json"
            let output = try Host.run("/usr/bin/ssh", RemoteSSH.arguments(profile.target) + [script], timeout: 10)
            let parts = String(decoding: output, as: UTF8.self).split(separator: "\n", maxSplits: 1)
            guard parts.count == 2, parts[0].hasPrefix("/") else { throw HudError.message("Remote Herdr executable was not found") }
            struct Inventory: Decodable { let sessions: [Session] }
            let inventory = try JSONDecoder().decode(Inventory.self, from: Data(parts[1].utf8))
            guard let remote = inventory.sessions.first(where: { $0.name == profile.session && $0.running }),
              remote.socket_path.hasPrefix("/"), !remote.socket_path.contains(":"),
              !remote.socket_path.contains("\n"), !remote.socket_path.contains("\0") else {
              throw HudError.message("Start the selected Herdr session on the remote machine first")
            }
            lock.lock(); executable = String(parts[0]); lock.unlock()
            let path = session.socket_path
            try? FileManager.default.removeItem(atPath: path)
            let child = Process(); child.executableURL = URL(fileURLWithPath: "/usr/bin/ssh")
            let args = try RemoteSSH.arguments(profile.target)
            child.arguments = Array(args.dropLast()) + ["-N", "-o", "ExitOnForwardFailure=yes", "-L", path + ":" + remote.socket_path, profile.target]
            child.environment = Host.environment(); child.standardInput = FileHandle.nullDevice
            child.standardOutput = FileHandle.nullDevice; child.standardError = FileHandle.nullDevice
            lock.lock()
            if stopped { lock.unlock(); return }
            do { try child.run() } catch { lock.unlock(); throw error }
            process = child; tunnel = child; lock.unlock()
            let deadline = Date().addingTimeInterval(8)
            while running && child.isRunning && !FileManager.default.fileExists(atPath: path) && Date() < deadline { Thread.sleep(forTimeInterval: 0.1) }
            while running {
              guard child.isRunning else { throw HudError.message("SSH tunnel disconnected; check authentication and socket forwarding") }
              let current = session
              let snapshot = try backend.snapshot(current)
              if running { onSnapshot?(current, snapshot) }
              pause(3)
            }
          } catch { if running { onError?(session, error.localizedDescription) } }
        }
        pause(5)
      }
    }
  }
}
