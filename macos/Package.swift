// swift-tools-version: 6.2
import PackageDescription

let package = Package(
  name: "HerdrHud", platforms: [.macOS("27.0")],
  products: [.executable(name: "HerdrHud", targets: ["HerdrHud"])],
  dependencies: [
    .package(
      url: "https://github.com/migueldeicaza/SwiftTerm.git",
      revision: "73b27f5679d847a4ef9d574c09e2b2264804b506")
  ],
  targets: [
    .target(name: "HudCore"),
    .executableTarget(
      name: "HerdrHud", dependencies: ["HudCore", "SwiftTerm"], resources: [.copy("Resources")]),
    .executableTarget(name: "HudCoreChecks", dependencies: ["HudCore"], path: "Tests/HudCoreTests"),
  ], swiftLanguageModes: [.v5])
