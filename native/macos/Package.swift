// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "ModelDockNative",
    platforms: [.macOS(.v26)],
    products: [.executable(name: "ModelDockNative", targets: ["ModelDockNative"])],
    targets: [
        .executableTarget(
            name: "ModelDockNative",
            path: "Sources/ModelDockNative"
        )
    ]
)
