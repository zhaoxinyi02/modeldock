import AppKit
import Combine
import Foundation

@MainActor
final class AppModel: ObservableObject {
    @Published var snapshot: Snapshot?
    @Published var isBusy = false
    @Published var errorMessage: String?
    @Published var noticeMessage: String?
    @Published var selectedModelID: Int?

    func refresh(showBusy: Bool = false) {
        if showBusy { isBusy = true }
        Task {
            defer { if showBusy { isBusy = false } }
            do {
                snapshot = try await Backend.call("snapshot", as: Snapshot.self)
                if selectedModelID == nil {
                    selectedModelID = snapshot?.models.first(where: { !$0.builtIn })?.id
                }
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }

    func perform<T: Decodable & Sendable>(
        _ command: String,
        payload: [String: Any] = [:],
        as type: T.Type,
        success: String? = nil
    ) {
        isBusy = true
        Task {
            defer { isBusy = false }
            do {
                _ = try await Backend.call(command, payload: payload, as: type)
                if let success { noticeMessage = success }
                snapshot = try await Backend.call("snapshot", as: Snapshot.self)
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }

    func openUsage() {
        NSWorkspace.shared.open(URL(string: "https://chatgpt.com/codex/settings/usage")!)
    }
}
