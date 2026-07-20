using System.Text.Json.Serialization;

namespace ModelDock;

public sealed class Snapshot
{
    [JsonPropertyName("app_name")] public string AppName { get; set; } = "ModelDock";
    [JsonPropertyName("version")] public string Version { get; set; } = "";
    [JsonPropertyName("account")] public AccountInfo Account { get; set; } = new();
    [JsonPropertyName("gateway")] public GatewayInfo Gateway { get; set; } = new();
    [JsonPropertyName("codex")] public CodexInfo Codex { get; set; } = new();
    [JsonPropertyName("conversation")] public ConversationInfo Conversation { get; set; } = new();
    [JsonPropertyName("provider")] public ProviderInfo Provider { get; set; } = new();
    [JsonPropertyName("autostart")] public string Autostart { get; set; } = "";
    [JsonPropertyName("port")] public int Port { get; set; } = 8317;
    [JsonPropertyName("models")] public List<ModelEntry> Models { get; set; } = [];
    [JsonPropertyName("restore_points")] public List<RestorePoint> RestorePoints { get; set; } = [];
}

public sealed class AccountInfo
{
    [JsonPropertyName("logged_in")] public bool LoggedIn { get; set; }
    [JsonPropertyName("gateway_logged_in")] public bool GatewayLoggedIn { get; set; }
    [JsonPropertyName("email")] public string Email { get; set; } = "未读取到";
    [JsonPropertyName("plan")] public string Plan { get; set; } = "未知";
    [JsonPropertyName("refreshed_at")] public string RefreshedAt { get; set; } = "";
    [JsonPropertyName("expired")] public string Expired { get; set; } = "";
    [JsonPropertyName("mode")] public string Mode { get; set; } = "";
    [JsonPropertyName("mode_key")] public string ModeKey { get; set; } = "pure_official";
    [JsonPropertyName("third_party_count")] public int ThirdPartyCount { get; set; }
    [JsonPropertyName("usage")] public string Usage { get; set; } = "";
}

public sealed class GatewayInfo
{
    [JsonPropertyName("running")] public bool Running { get; set; }
    [JsonPropertyName("responding")] public bool Responding { get; set; }
    [JsonPropertyName("pid")] public int? Pid { get; set; }
    [JsonPropertyName("url")] public string Url { get; set; } = "";
    [JsonPropertyName("models")] public List<string> Models { get; set; } = [];
}

public sealed class CodexInfo
{
    [JsonPropertyName("running")] public bool Running { get; set; }
    [JsonPropertyName("count")] public int Count { get; set; }
}

public sealed class ConversationInfo
{
    [JsonPropertyName("active_sessions")] public int ActiveSessions { get; set; }
    [JsonPropertyName("archived_sessions")] public int ArchivedSessions { get; set; }
    [JsonPropertyName("indexed_threads")] public int IndexedThreads { get; set; }
    [JsonPropertyName("snapshots")] public int Snapshots { get; set; }
}

public sealed class ProviderInfo
{
    [JsonPropertyName("model_provider")] public string ModelProvider { get; set; } = "";
    [JsonPropertyName("uses_gateway")] public bool UsesGateway { get; set; }
}

public sealed class ModelEntry
{
    [JsonPropertyName("number")] public int Number { get; set; }
    [JsonPropertyName("order")] public int Order { get; set; }
    [JsonPropertyName("section")] public string Section { get; set; } = "";
    [JsonPropertyName("alias")] public string Alias { get; set; } = "";
    [JsonPropertyName("upstream")] public string Upstream { get; set; } = "";
    [JsonPropertyName("base_url")] public string BaseUrl { get; set; } = "";
    [JsonPropertyName("api_key")] public string ApiKey { get; set; } = "";
    [JsonPropertyName("built_in")] public bool BuiltIn { get; set; }
    [JsonPropertyName("display_name")] public string DisplayName { get; set; } = "";
    [JsonPropertyName("provider_name")] public string ProviderName { get; set; } = "";
    [JsonPropertyName("context_window")] public int? ContextWindow { get; set; }
    [JsonPropertyName("max_output_tokens")] public int? MaxOutputTokens { get; set; }

    public string TypeLabel => Section switch
    {
        "codex-api-key" => "OpenAI Responses",
        "openai-compatibility" => "OpenAI 兼容",
        "claude-api-key" => "Anthropic 兼容",
        _ => Section
    };
    public string ContextText => ContextWindow?.ToString("N0") ?? "—";
    public string OutputText => MaxOutputTokens?.ToString("N0") ?? "—";
}

public sealed class RestorePoint
{
    [JsonPropertyName("id")] public string Id { get; set; } = "";
    [JsonPropertyName("kind")] public string Kind { get; set; } = "";
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("notes")] public string Notes { get; set; } = "";
    [JsonPropertyName("created_at")] public string CreatedAt { get; set; } = "";
    [JsonPropertyName("items")] public int Items { get; set; }
    public string KindLabel => Kind == "manual" ? "手动" : "自动";
}

public sealed class ActionResult { [JsonPropertyName("ok")] public bool? Ok { get; set; } }
public sealed class MessageResult { [JsonPropertyName("message")] public string Message { get; set; } = ""; }
public sealed class MoveResult { [JsonPropertyName("moved")] public bool Moved { get; set; } }
public sealed class ModelsResult { [JsonPropertyName("models")] public List<string> Models { get; set; } = []; }
