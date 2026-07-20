import SwiftUI

struct HomeView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            PageHeader(title: "Codex Gateway", subtitle: "官方订阅与第三方模型的原生控制中心")
            if let snapshot = model.snapshot {
                VStack(alignment: .leading, spacing: 10) {
                    HStack {
                        VStack(alignment: .leading, spacing: 5) {
                            Text(snapshot.account.mode).font(.title.bold())
                            Text(modeDescription(snapshot.account.modeKey)).foregroundStyle(.secondary)
                        }
                        Spacer()
                        StatusPill(
                            text: snapshot.account.modeKey == "pure_official" ? "官方直连" : "本地网关",
                            color: snapshot.account.modeKey == "pure_official" ? .blue : .green
                        )
                    }
                }
                .padding(22)
                .glassEffect(.regular.interactive(), in: .rect(cornerRadius: 24))

                HStack(alignment: .top, spacing: 16) {
                    NativeCard("本地网关") {
                        StatusPill(
                            text: snapshot.gateway.running ? (snapshot.gateway.responding ? "运行中 · 正常响应" : "运行中") : "已停止",
                            color: snapshot.gateway.responding ? .green : .secondary
                        )
                        LabeledContent("地址", value: snapshot.gateway.url)
                        LabeledContent("模型数量", value: "\(snapshot.gateway.models.count)")
                        GlassEffectContainer(spacing: 8) {
                            HStack {
                                Button("启动") { action("start") }.disabled(snapshot.gateway.running || snapshot.account.modeKey == "pure_official")
                                Button("停止") { action("stop") }.disabled(!snapshot.gateway.running)
                                Button("重启") { action("restart") }.disabled(snapshot.account.modeKey == "pure_official")
                            }.buttonStyle(.glass)
                        }
                    }
                    NativeCard("Codex Desktop") {
                        StatusPill(text: snapshot.codex.running ? "运行中" : "未运行", color: snapshot.codex.running ? .green : .secondary)
                        LabeledContent("进程数", value: "\(snapshot.codex.count)")
                        GlassEffectContainer(spacing: 8) {
                            HStack {
                                Button(snapshot.codex.running ? "停止 Codex" : "打开 Codex") {
                                    codexAction(snapshot.codex.running ? "stop" : "start")
                                }.buttonStyle(.glassProminent)
                                Button("重启 Codex") { codexAction("restart") }.buttonStyle(.glass).disabled(!snapshot.codex.running)
                            }
                        }
                    }
                }

                NativeCard("官方账号") {
                    Grid(alignment: .leading, horizontalSpacing: 26, verticalSpacing: 9) {
                        GridRow { Text("邮箱").foregroundStyle(.secondary); Text(snapshot.account.email) }
                        GridRow { Text("套餐").foregroundStyle(.secondary); Text("\(snapshot.account.plan)（本机最新凭据返回）") }
                        GridRow { Text("更新时间").foregroundStyle(.secondary); Text(snapshot.account.refreshedAt) }
                        GridRow { Text("有效期至").foregroundStyle(.secondary); Text(snapshot.account.expired) }
                        GridRow { Text("第三方模型").foregroundStyle(.secondary); Text("\(snapshot.account.thirdPartyCount)") }
                    }
                }
            } else {
                ContentUnavailableView("正在读取状态", systemImage: "arrow.clockwise")
            }
            Spacer(minLength: 0)
        }
    }

    private func action(_ action: String) {
        model.perform("gateway_action", payload: ["action": action], as: ActionResult.self)
    }
    private func codexAction(_ action: String) {
        model.perform("codex_action", payload: ["action": action], as: ActionResult.self)
    }
    private func modeDescription(_ key: String) -> String {
        switch key {
        case "pure_official": "Codex 直接使用官方 provider，本地网关保持停止。"
        case "official_plus_api": "本地网关同时转发官方订阅凭据和第三方 API。"
        case "api_only": "只使用 API Key 和第三方模型，不依赖官方订阅。"
        default: "请检查 Codex 登录与 provider 配置。"
        }
    }
}
