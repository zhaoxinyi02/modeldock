import Foundation

enum BackendError: LocalizedError {
    case missingHelper
    case failed(String)
    case invalidResponse

    var errorDescription: String? {
        switch self {
        case .missingHelper: "未找到 ModelDock 本地后端。"
        case .failed(let message): message
        case .invalidResponse: "本地后端返回了无法解析的数据。"
        }
    }
}

private struct Envelope<T: Decodable>: Decodable {
    let ok: Bool
    let result: T
}

enum Backend {
    @MainActor
    static func call<T: Decodable & Sendable>(
        _ command: String,
        payload: [String: Any] = [:],
        as type: T.Type = T.self
    ) async throws -> T {
        let payloadData = try JSONSerialization.data(withJSONObject: payload)
        return try await Task.detached(priority: .userInitiated) {
            try run(command, payloadData: payloadData, as: type)
        }.value
    }

    private static func helperURL() -> URL? {
        let fm = FileManager.default
        let candidates = [
            Bundle.main.resourceURL?.appending(path: "Backend/ModelDockBackend"),
            URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
                .appending(path: "dist-native/ModelDockBackend/ModelDockBackend"),
        ].compactMap { $0 }
        return candidates.first { fm.isExecutableFile(atPath: $0.path) }
    }

    private static func run<T: Decodable>(
        _ command: String,
        payloadData: Data,
        as type: T.Type
    ) throws -> T {
        guard let helper = helperURL() else { throw BackendError.missingHelper }
        let process = Process()
        let stdout = Pipe()
        let stderr = Pipe()
        let stdin = Pipe()
        process.executableURL = helper
        process.arguments = [command]
        process.standardOutput = stdout
        process.standardError = stderr
        process.standardInput = stdin
        var environment = ProcessInfo.processInfo.environment
        environment.removeValue(forKey: "QT_PLUGIN_PATH")
        process.environment = environment
        try process.run()
        stdin.fileHandleForWriting.write(payloadData)
        try? stdin.fileHandleForWriting.close()
        let output = stdout.fileHandleForReading.readDataToEndOfFile()
        let errorOutput = stderr.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()

        guard let root = try? JSONSerialization.jsonObject(with: output) as? [String: Any] else {
            let detail = String(data: errorOutput, encoding: .utf8) ?? ""
            throw BackendError.failed(detail.isEmpty ? "本地后端没有返回数据。" : detail)
        }
        if root["ok"] as? Bool != true {
            throw BackendError.failed(root["error"] as? String ?? "操作失败。")
        }
        do {
            return try JSONDecoder().decode(Envelope<T>.self, from: output).result
        } catch {
            throw BackendError.invalidResponse
        }
    }
}
