import SwiftUI

struct RestorePointsView: View {
    @EnvironmentObject private var model: AppModel
    @State private var selected: RestorePoint.ID?
    @State private var creating = false
    @State private var restoring: RestorePoint?

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            PageHeader(title: "回退点", subtitle: "恢复 Codex 与网关配置，不改动会话正文")
            if let points = model.snapshot?.restorePoints {
                Table(points, selection: $selected) {
                    TableColumn("类型") { Text($0.kind == "manual" ? "手动" : "自动") }.width(65)
                    TableColumn("名称", value: \.name).width(min: 190, ideal: 260)
                    TableColumn("时间", value: \.createdAt).width(165)
                    TableColumn("备注", value: \.notes).width(min: 240, ideal: 380)
                    TableColumn("项目") { Text("\($0.items)") }.width(55)
                }
                GlassEffectContainer(spacing: 8) {
                    HStack {
                        Button("新建手动回退点", systemImage: "plus") { creating = true }.buttonStyle(.glassProminent)
                        Button("恢复选中回退点", systemImage: "clock.arrow.trianglehead.counterclockwise.rotate.90") {
                            restoring = points.first { $0.id == selected }
                        }.buttonStyle(.glass).disabled(selected == nil)
                    }
                }
            }
        }
        .sheet(isPresented: $creating) { CreateRestoreSheet() }
        .confirmationDialog("恢复这个回退点？", isPresented: Binding(
            get: { restoring != nil }, set: { if !$0 { restoring = nil } }
        )) {
            Button("恢复 \(restoring?.name ?? "")") {
                if let restoring {
                    model.perform("restore", payload: ["id": restoring.id], as: ActionResult.self, success: "回退完成。")
                }
                restoring = nil
            }
        } message: { Text("恢复前会自动创建保护点。") }
    }
}

private struct CreateRestoreSheet: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var model: AppModel
    @State private var name = ""
    @State private var notes = ""

    var body: some View {
        NavigationStack {
            Form {
                TextField("名称", text: $name)
                TextField("备注", text: $notes, axis: .vertical)
            }.formStyle(.grouped)
            .navigationTitle("新建手动回退点")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("取消") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("创建") {
                        model.perform("create_restore", payload: ["name": name, "notes": notes], as: PathResult.self, success: "回退点已创建。")
                        dismiss()
                    }.buttonStyle(.glassProminent).disabled(name.isEmpty)
                }
            }
        }.frame(width: 520, height: 300)
    }
}
