import SwiftUI

private enum ModelSheet: Identifiable {
    case add
    case edit(ModelEntry)
    var id: String {
        switch self {
        case .add: "add"
        case .edit(let model): "edit-\(model.id)"
        }
    }
}

struct ModelsView: View {
    @EnvironmentObject private var model: AppModel
    @State private var sheet: ModelSheet?
    @State private var deleting: ModelEntry?

    private var selected: ModelEntry? {
        model.snapshot?.models.first { $0.id == model.selectedModelID }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            PageHeader(title: "配置管理", subtitle: "双击模型进行编辑；序号固定，移动只改变 Codex 中的排列顺序")
            if let models = model.snapshot?.models {
                Table(models, selection: $model.selectedModelID) {
                    TableColumn("序号") { Text("\($0.number)").monospacedDigit() }.width(44)
                    TableColumn("名称", value: \.displayName).width(min: 140, ideal: 165)
                    TableColumn("上游模型", value: \.upstream).width(min: 110, ideal: 130)
                    TableColumn("类型") { Text($0.typeLabel) }.width(min: 112, ideal: 125)
                    TableColumn("URL") { Text($0.baseURL).lineLimit(1).truncationMode(.middle).help($0.baseURL) }.width(min: 160, ideal: 205)
                    TableColumn("上下文") { Text($0.contextWindow.map(String.init) ?? "—").monospacedDigit() }.width(72)
                    TableColumn("最大输出") { Text($0.maxOutputTokens.map(String.init) ?? "—").monospacedDigit() }.width(72)
                }
                .onTapGesture(count: 2) {
                    if let selected, !selected.builtIn { sheet = .edit(selected) }
                }
                .contextMenu(forSelectionType: Int.self) { _ in
                    Button("编辑") { if let selected, !selected.builtIn { sheet = .edit(selected) } }
                    Divider()
                    Button("上移") { move(-1) }
                    Button("下移") { move(1) }
                } primaryAction: { ids in
                    if let id = ids.first, let entry = models.first(where: { $0.id == id }), !entry.builtIn {
                        sheet = .edit(entry)
                    }
                }
            } else {
                ContentUnavailableView("正在读取模型", systemImage: "cpu")
            }

            GlassEffectContainer(spacing: 8) {
                HStack {
                    Button("添加模型", systemImage: "plus") { sheet = .add }.buttonStyle(.glassProminent)
                    Button("编辑", systemImage: "pencil") {
                        if let selected, !selected.builtIn { sheet = .edit(selected) }
                    }.buttonStyle(.glass).disabled(selected == nil || selected?.builtIn == true)
                    Button("上移", systemImage: "arrow.up") { move(-1) }.buttonStyle(.glass).disabled(selected == nil || selected?.builtIn == true)
                    Button("下移", systemImage: "arrow.down") { move(1) }.buttonStyle(.glass).disabled(selected == nil || selected?.builtIn == true)
                    Spacer()
                    Button("删除", systemImage: "trash", role: .destructive) { deleting = selected }
                        .buttonStyle(.glass).disabled(selected == nil || selected?.builtIn == true)
                }
            }
        }
        .sheet(item: $sheet) { mode in
            switch mode {
            case .add:
                ModelEditor(entry: nil) { payload in
                    model.perform("add_model", payload: payload, as: ActionResult.self, success: "模型已添加。")
                }
            case .edit(let entry):
                ModelEditor(entry: entry) { payload in
                    var data = payload
                    data["number"] = entry.number
                    model.perform("modify_model", payload: data, as: ActionResult.self, success: "模型已修改。")
                }
            }
        }
        .confirmationDialog("确认删除模型？", isPresented: Binding(
            get: { deleting != nil }, set: { if !$0 { deleting = nil } }
        )) {
            Button("删除 \(deleting?.displayName ?? "")", role: .destructive) {
                if let deleting {
                    model.perform("remove_model", payload: ["number": deleting.number], as: ActionResult.self, success: "模型已删除。")
                }
                deleting = nil
            }
        }
    }

    private func move(_ direction: Int) {
        guard let selected, !selected.builtIn else { return }
        model.perform("move_model", payload: ["number": selected.number, "direction": direction], as: MoveResult.self)
    }
}

struct ModelEditor: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var appModel: AppModel
    let entry: ModelEntry?
    let onSave: ([String: Any]) -> Void

    @State private var apiType: APIType
    @State private var baseURL: String
    @State private var apiKey: String
    @State private var upstream: String
    @State private var name: String
    @State private var provider: String
    @State private var context: String
    @State private var maxOutput: String
    @State private var showKey = false
    @State private var fetching = false
    @State private var modelOptions: [String] = []

    init(entry: ModelEntry?, onSave: @escaping ([String: Any]) -> Void) {
        self.entry = entry
        self.onSave = onSave
        _apiType = State(initialValue: entry?.apiType ?? .responses)
        _baseURL = State(initialValue: entry?.baseURL ?? "")
        _apiKey = State(initialValue: entry?.apiKey ?? "")
        _upstream = State(initialValue: entry?.upstream ?? "")
        _name = State(initialValue: entry?.displayName ?? "")
        _provider = State(initialValue: entry?.providerName ?? "")
        _context = State(initialValue: entry?.contextWindow.map(String.init) ?? "")
        _maxOutput = State(initialValue: entry?.maxOutputTokens.map(String.init) ?? "")
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("接口") {
                    Picker("接口类型", selection: $apiType) {
                        ForEach(APIType.allCases) { Text($0.label).tag($0) }
                    }.disabled(entry != nil)
                    TextField("API Base URL", text: $baseURL, prompt: Text("https://api.example.com/v1"))
                    LabeledContent("API Key") {
                        HStack {
                            if showKey { TextField("API Key", text: $apiKey) }
                            else { SecureField("API Key", text: $apiKey) }
                            Button { showKey.toggle() } label: {
                                Image(systemName: showKey ? "eye.slash" : "eye")
                            }.buttonStyle(.borderless).help(showKey ? "隐藏 API Key" : "显示 API Key")
                        }
                    }
                }
                Section("模型") {
                    LabeledContent("上游模型 ID") {
                        HStack {
                            TextField("模型 ID", text: $upstream)
                            Button(fetching ? "正在获取" : "获取模型列表") { fetchModels() }
                                .disabled(fetching || baseURL.isEmpty || apiKey.isEmpty)
                        }
                    }
                    if !modelOptions.isEmpty {
                        Picker("接口返回的模型", selection: $upstream) {
                            ForEach(modelOptions, id: \.self) { Text($0).tag($0) }
                        }
                    }
                    TextField("名称", text: $name)
                    TextField("供应商名称", text: $provider)
                }
                Section("Token") {
                    TextField("上下文 token", text: $context)
                    TextField("最大输出 token", text: $maxOutput)
                }
            }
            .formStyle(.grouped)
            .navigationTitle(entry == nil ? "添加模型" : "编辑模型")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("取消") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("保存") { save() }.buttonStyle(.glassProminent)
                        .disabled(baseURL.isEmpty || apiKey.isEmpty || upstream.isEmpty)
                }
            }
        }
        .frame(minWidth: 720, idealWidth: 760, minHeight: 500, idealHeight: 560)
    }

    private func save() {
        let resolvedName = name.isEmpty ? upstream : name
        var payload: [String: Any] = [
            "base_url": baseURL, "api_key": apiKey, "upstream": upstream,
            "alias": resolvedName, "display_name": resolvedName,
            "provider_name": provider.isEmpty ? "Custom" : provider,
        ]
        if let value = Int(context) { payload["context_window"] = value }
        if let value = Int(maxOutput) { payload["max_output_tokens"] = value }
        if entry == nil {
            payload["api_type"] = apiType.rawValue
            payload["model_id"] = upstream
            payload.removeValue(forKey: "upstream")
        }
        onSave(payload)
        dismiss()
    }

    private func fetchModels() {
        fetching = true
        Task {
            defer { fetching = false }
            do {
                let result = try await Backend.call("fetch_models", payload: [
                    "base_url": baseURL, "api_key": apiKey, "api_type": apiType.rawValue,
                ], as: ModelsResult.self)
                modelOptions = result.models
                if upstream.isEmpty { upstream = result.models.first ?? "" }
            } catch {
                appModel.errorMessage = error.localizedDescription
            }
        }
    }
}
