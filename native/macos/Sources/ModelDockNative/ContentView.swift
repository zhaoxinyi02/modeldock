import AppKit
import SwiftUI

enum SidebarPage: String, CaseIterable, Identifiable {
    case home, models, restores, settings
    var id: String { rawValue }
    var title: String {
        switch self {
        case .home: "首页"
        case .models: "配置管理"
        case .restores: "回退点"
        case .settings: "设置"
        }
    }
    var icon: String {
        switch self {
        case .home: "square.grid.2x2"
        case .models: "cpu"
        case .restores: "clock.arrow.trianglehead.counterclockwise.rotate.90"
        case .settings: "gearshape"
        }
    }
}

struct ContentView: View {
    @EnvironmentObject private var model: AppModel
    @State private var page: SidebarPage = .home

    var body: some View {
        NavigationSplitView {
            List(SidebarPage.allCases, selection: $page) { item in
                Label(item.title, systemImage: item.icon)
                    .tag(item)
            }
            .navigationTitle("ModelDock")
            .navigationSplitViewColumnWidth(min: 188, ideal: 218, max: 250)
        } detail: {
            ZStack {
                DetailBackground()
                Group {
                    switch page {
                    case .home: HomeView()
                    case .models: ModelsView()
                    case .restores: RestorePointsView()
                    case .settings: SettingsView()
                    }
                }
                .padding(24)
                if model.isBusy {
                    ZStack {
                        Rectangle().fill(.black.opacity(0.08)).ignoresSafeArea()
                        ProgressView().controlSize(.large).padding(26)
                            .glassEffect(.regular, in: .rect(cornerRadius: 18))
                    }
                }
            }
            .backgroundExtensionEffect()
        }
        .frame(minWidth: 1080, minHeight: 680)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { model.refresh(showBusy: true) } label: {
                    Label("刷新", systemImage: "arrow.clockwise")
                }
                .help("刷新全部状态")
            }
        }
        .alert("操作失败", isPresented: Binding(
            get: { model.errorMessage != nil },
            set: { if !$0 { model.errorMessage = nil } }
        )) { Button("好", role: .cancel) {} } message: { Text(model.errorMessage ?? "") }
        .alert("ModelDock", isPresented: Binding(
            get: { model.noticeMessage != nil },
            set: { if !$0 { model.noticeMessage = nil } }
        )) { Button("好", role: .cancel) {} } message: { Text(model.noticeMessage ?? "") }
        .task {
            model.refresh(showBusy: true)
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(8))
                model.refresh()
            }
        }
    }
}

struct DetailBackground: View {
    var body: some View {
        ZStack {
            Color(nsColor: .windowBackgroundColor)
            RadialGradient(colors: [.blue.opacity(0.12), .clear], center: .topTrailing, startRadius: 10, endRadius: 560)
            RadialGradient(colors: [.orange.opacity(0.08), .clear], center: .bottomLeading, startRadius: 20, endRadius: 520)
        }
        .ignoresSafeArea()
    }
}

struct PageHeader: View {
    let title: String
    let subtitle: String
    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title).font(.largeTitle.bold())
            Text(subtitle).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct NativeCard<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    init(_ title: String, @ViewBuilder content: () -> Content) {
        self.title = title
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 13) {
            Text(title).font(.headline)
            content
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.background.opacity(0.82), in: .rect(cornerRadius: 18))
        .overlay { RoundedRectangle(cornerRadius: 18).stroke(.separator.opacity(0.45)) }
    }
}

struct StatusPill: View {
    let text: String
    let color: Color
    var body: some View {
        Label(text, systemImage: "circle.fill")
            .font(.callout.weight(.semibold))
            .symbolRenderingMode(.monochrome)
            .foregroundStyle(color)
            .padding(.horizontal, 12).padding(.vertical, 7)
            .glassEffect(.regular.tint(color.opacity(0.18)), in: .capsule)
    }
}
