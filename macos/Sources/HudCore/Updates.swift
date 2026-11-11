import Foundation
import CryptoKit

public struct HudRelease: Codable {
  public struct Asset: Codable {
    public let name: String
    public let browser_download_url: String
    public let size: Int
    public let digest: String?
  }
  public let tag_name: String
  public let draft: Bool
  public let assets: [Asset]
}

public enum HudUpdates {
  public static let interval: TimeInterval = 6 * 60 * 60
  private static let api = URL(string: "https://api.github.com/repos/alex-jax/jax-herdr-hud/releases?per_page=100")!
  public static func filename(_ tag: String) -> String {
    "jax-herdr-hud-" + tag.replacingOccurrences(of: "^v", with: "", options: .regularExpression) + "-macos-arm64.dmg"
  }
  public static func version(_ value: String) -> [Int]? {
    let text = value.hasPrefix("v") ? String(value.dropFirst()) : value
    guard text.range(of: "^[0-9]+\\.[0-9]+$", options: .regularExpression) != nil else { return nil }
    let parts = text.split(separator: ".").compactMap { Int($0) }
    return parts.count == 2 ? parts : nil
  }
  public static func newer(_ candidate: String, than installed: String) -> Bool {
    guard let a = version(candidate), let b = version(installed) else { return false }
    return b.lexicographicallyPrecedes(a)
  }
  public static func choose(_ releases: [HudRelease], current: String) -> HudRelease? {
    releases.filter { release in !release.draft && newer(release.tag_name, than: current)
      && release.assets.contains(where: { $0.name == filename(release.tag_name) }) }
      .max { newer($1.tag_name, than: $0.tag_name) }
  }
  private static func download(_ url: URL, maximum: Int) throws -> URL {
    let semaphore = DispatchSemaphore(value: 0)
    let lock = NSLock()
    var result: Result<URL, Error>?
    var request = URLRequest(url: url); request.timeoutInterval = 60
    request.setValue("Herdr-Hud-update", forHTTPHeaderField: "User-Agent")
    let task = URLSession.shared.downloadTask(with: request) { temporary, response, error in
      let outcome: Result<URL, Error> = Result {
        if let error { throw error }
        guard let temporary, let response = response as? HTTPURLResponse, response.statusCode == 200 else {
          throw HudError.message("GitHub update request failed")
        }
        let attributes = try FileManager.default.attributesOfItem(atPath: temporary.path)
        guard let size = attributes[.size] as? Int, size > 0, size <= maximum else {
          throw HudError.message("Update response exceeds the expected size")
        }
        let destination = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.moveItem(at: temporary, to: destination)
        return destination
      }
      lock.lock(); result = outcome; lock.unlock(); semaphore.signal()
    }
    task.resume()
    guard semaphore.wait(timeout: .now() + 120) == .success else {
      task.cancel(); throw HudError.message("Update download timed out")
    }
    lock.lock(); defer { lock.unlock() }
    return try result!.get()
  }
  public static func releases() throws -> [HudRelease] {
    let file = try download(api, maximum: 1024 * 1024)
    defer { try? FileManager.default.removeItem(at: file) }
    return try JSONDecoder().decode([HudRelease].self, from: Data(contentsOf: file))
  }
  public static func installer(_ release: HudRelease) throws -> URL {
    guard version(release.tag_name) != nil, !release.draft,
      let asset = release.assets.first(where: { $0.name == filename(release.tag_name) }),
      asset.size > 0, asset.size <= 512 * 1024 * 1024,
      let digest = asset.digest, digest.range(of: "^sha256:[0-9a-fA-F]{64}$", options: .regularExpression) != nil else {
      throw HudError.message("Release has no valid Mac installer or checksum")
    }
    let expected = "https://github.com/alex-jax/jax-herdr-hud/releases/download/" + release.tag_name + "/" + asset.name
    guard asset.browser_download_url == expected, let url = URL(string: expected) else {
      throw HudError.message("Unexpected installer URL")
    }
    let file = try download(url, maximum: asset.size)
    defer { try? FileManager.default.removeItem(at: file) }
    let data = try Data(contentsOf: file, options: .mappedIfSafe)
    let actual = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    guard data.count == asset.size, actual == String(digest.dropFirst(7)).lowercased() else {
      throw HudError.message("Installer checksum failed; nothing was installed")
    }
    _ = try Host.run("/usr/bin/hdiutil", ["verify", file.path], timeout: 120)
    let directory = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
      .appendingPathComponent("io.github.herdr.Hud/updates")
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let destination = directory.appendingPathComponent(asset.name)
    try data.write(to: destination, options: .atomic)
    return destination
  }
}
