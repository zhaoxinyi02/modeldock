import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var model: AppModel
    @State private var port = "8317"

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                PageHeader(title: "设置", subtitle: "模式、官方凭据、会话保护与网关")
                if let snapshot = model.snapshot {
                    NativeCard("Codex 登录状态") {
                        LabeledContent("当前模式", value: snapshot.account.mode)
                        LabeledContent("账号", value: snapshot.account.email)
                        LabeledContent("套餐", value: snapshot.account.plan + "（凭据返回）")
                        LabeledContent("实际 provider", value: snapshot.provider.modelProvider)
                        Divider()
                        GlassEffectContainer(spacing: 8) {
                            HStack {
                                Button("重新登录 / 刷新凭据", systemImage: "person.crop.circle.badge.arrow.trianglehead.counterclockwise") {
                                    model.perform("login", as: ActionResult.self, success: "已启动浏览器授权，请完成登录。")
                                }.buttonStyle(.glassProminent)
                                Button("打开官方 Usage", systemImage: "chart.bar") { model.openUsage() }.buttonStyle(.glass)
                            }
                        }
                        Picker("运行模式", selection: Binding(
                            get: { snapshot.account.modeKey },
                            set: { switchMode($0) }
                        )) {
                            Text("纯官方订阅").tag("pure_official")
                            Text("官方订阅 + 第三方 API").tag("official_plus_api")
                            Text("纯 API + 第三方模型").tag("api_only")
                        }
                        .pickerStyle(.segmented)
                    }

                    NativeCard("会话保护") {
                        HStack(spacing: 24) {
                            metric("活动", snapshot.conversation.activeSessions)
                            metric("归档", snapshot.conversation.archivedSessions)
                            metric("侧栏索引", snapshot.conversation.indexedThreads)
                            metric("索引快照", snapshot.conversation.snapshots)
                        }
                        GlassEffectContainer(spacing: 8) {
                            HStack {
                                Button("创建会话索引快照", systemImage: "camera") {
                                    model.perform("conversation_snapshot", as: ActionResult.self, success: "已创建会话索引快照。")
                                }.buttonStyle(.glass)
                                Button("修复并统一会话列表", systemImage: "wrench.and.screwdriver") {
                                    model.perform("conversation_repair", as: ActionResult.self, success: "会话列表修复完成。")
                                }.buttonStyle(.glass)
                            }
                        }
                    }

                    NativeCard("开机自启与端口") {
                        Toggle("登录后自动启动本地网关", isOn: Binding(
                            get: { snapshot.autostart == "ready" || snapshot.autostart == "running" },
                            set: { enabled in model.perform("autostart", payload: ["enabled": enabled], as: ActionResult.self) }
                        ))
                        HStack {
                            TextField("端口", text: $port).frame(width: 110)
                            Button("应用端口并重启") {
                                guard let value = Int(port), (1...65535).contains(value) else {
                                    model.errorMessage = "端口必须是 1–65535 的整数。"; return
                                }
                                model.perform("set_port", payload: ["port": value], as: ActionResult.self, success: "端口已更新。")
                            }.buttonStyle(.glassProminent)
                        }
                    }

                    NativeCard("关于") {
                        LabeledContent("版本", value: snapshot.version)
                        LabeledContent("界面", value: "SwiftUI · macOS 26 Liquid Glass")
                        LabeledContent("本地网关", value: "CLIProxyAPI 7.2.92")
                    }
                }
            }
        }
        .onChange(of: model.snapshot?.port, initial: true) { _, value in
            if let value { port = String(value) }
        }
    }

    private func metric(_ title: String, _ value: Int) -> some View {
        VStack(alignment: .leading) {
            Text("\(value)").font(.title2.bold()).monospacedDigit()
            Text(title).foregroundStyle(.secondary)
        }
    }

    private func switchMode(_ mode: String) {
        model.perform("switch_mode", payload: ["mode": mode], as: MessageResult.self, success: "模式切换完成。")
    }
}
