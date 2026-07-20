import Foundation

struct Snapshot: Codable, Sendable {
    let appName: String
    let version: String
    let account: AccountInfo
    let gateway: GatewayInfo
    let codex: CodexInfo
    let conversation: ConversationInfo
    let provider: ProviderInfo
    let autostart: String
    let port: Int
    let models: [ModelEntry]
    let restorePoints: [RestorePoint]

    enum CodingKeys: String, CodingKey {
        case appName = "app_name", version, account, gateway, codex, conversation, provider, autostart, port, models
        case restorePoints = "restore_points"
    }
}

struct AccountInfo: Codable, Sendable {
    let loggedIn: Bool
    let gatewayLoggedIn: Bool
    let email: String
    let plan: String
    let refreshedAt: String
    let expired: String
    let mode: String
    let modeKey: String
    let thirdPartyCount: Int
    let usage: String

    enum CodingKeys: String, CodingKey {
        case email, plan, expired, mode, usage
        case loggedIn = "logged_in", gatewayLoggedIn = "gateway_logged_in"
        case refreshedAt = "refreshed_at", modeKey = "mode_key", thirdPartyCount = "third_party_count"
    }
}

struct GatewayInfo: Codable, Sendable {
    let running: Bool
    let responding: Bool
    let pid: Int?
    let url: String
    let models: [String]
}

struct CodexInfo: Codable, Sendable {
    let running: Bool
    let count: Int
}

struct ConversationInfo: Codable, Sendable {
    let activeSessions: Int
    let archivedSessions: Int
    let indexedThreads: Int
    let snapshots: Int

    enum CodingKeys: String, CodingKey {
        case activeSessions = "active_sessions", archivedSessions = "archived_sessions"
        case indexedThreads = "indexed_threads", snapshots
    }
}

struct ProviderInfo: Codable, Sendable {
    let modelProvider: String
    let requiresOpenAIAuth: Bool?
    let usesGateway: Bool

    enum CodingKeys: String, CodingKey {
        case modelProvider = "model_provider", requiresOpenAIAuth = "requires_openai_auth", usesGateway = "uses_gateway"
    }
}

struct ModelEntry: Codable, Identifiable, Hashable, Sendable {
    let number: Int
    let order: Int
    let section: String
    let alias: String
    let upstream: String
    let baseURL: String
    let apiKey: String
    let builtIn: Bool
    let displayName: String
    let providerName: String
    let contextWindow: Int?
    let maxOutputTokens: Int?

    var id: Int { number }
    var typeLabel: String {
        switch section {
        case "codex-api-key": "OpenAI Responses"
        case "openai-compatibility": "OpenAI 兼容"
        case "claude-api-key": "Anthropic 兼容"
        default: section
        }
    }
    var apiType: APIType {
        switch section {
        case "openai-compatibility": .openAI
        case "claude-api-key": .anthropic
        default: .responses
        }
    }

    enum CodingKeys: String, CodingKey {
        case number, order, section, alias, upstream
        case baseURL = "base_url", apiKey = "api_key", builtIn = "built_in"
        case displayName = "display_name", providerName = "provider_name"
        case contextWindow = "context_window", maxOutputTokens = "max_output_tokens"
    }
}

struct RestorePoint: Codable, Identifiable, Hashable, Sendable {
    let id: String
    let kind: String
    let name: String
    let notes: String
    let createdAt: String
    let items: Int

    enum CodingKeys: String, CodingKey {
        case id, kind, name, notes, items
        case createdAt = "created_at"
    }
}

enum APIType: String, CaseIterable, Identifiable, Sendable {
    case responses, openAI = "openai", anthropic = "claude"
    var id: String { rawValue }
    var label: String {
        switch self {
        case .responses: "OpenAI Responses"
        case .openAI: "OpenAI 兼容"
        case .anthropic: "Anthropic 兼容"
        }
    }
}

struct ActionResult: Codable, Sendable { let ok: Bool? }
struct MessageResult: Codable, Sendable { let message: String }
struct MoveResult: Codable, Sendable { let moved: Bool }
struct TextResult: Codable, Sendable { let text: String }
struct PathResult: Codable, Sendable { let path: String }
struct ModelsResult: Codable, Sendable { let models: [String] }
