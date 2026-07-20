using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace ModelDock;

public sealed class BackendClient
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    private static string HelperPath
    {
        get
        {
            var packaged = Path.Combine(AppContext.BaseDirectory, "Backend", "ModelDockBackend.exe");
            if (File.Exists(packaged)) return packaged;
            var development = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "build", "native-backend-dist", "ModelDockBackend", "ModelDockBackend.exe"));
            return development;
        }
    }

    public async Task<T> CallAsync<T>(string command, object? payload = null)
    {
        if (!File.Exists(HelperPath))
            throw new FileNotFoundException("未找到 ModelDock 本地后端。", HelperPath);

        var start = new ProcessStartInfo
        {
            FileName = HelperPath,
            Arguments = command,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardInputEncoding = Encoding.UTF8,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
        };
        start.Environment.Remove("QT_PLUGIN_PATH");

        using var process = new Process { StartInfo = start };
        process.Start();
        var outputTask = process.StandardOutput.ReadToEndAsync();
        var errorTask = process.StandardError.ReadToEndAsync();
        await process.StandardInput.WriteAsync(JsonSerializer.Serialize(payload ?? new { }, JsonOptions));
        process.StandardInput.Close();
        await process.WaitForExitAsync();
        var output = await outputTask;
        var error = await errorTask;

        if (string.IsNullOrWhiteSpace(output))
            throw new InvalidOperationException(string.IsNullOrWhiteSpace(error) ? "本地后端没有返回数据。" : error.Trim());

        using var document = JsonDocument.Parse(output);
        var root = document.RootElement;
        if (!root.TryGetProperty("ok", out var ok) || !ok.GetBoolean())
        {
            var message = root.TryGetProperty("error", out var value) ? value.GetString() : null;
            throw new InvalidOperationException(message ?? "操作失败。");
        }
        if (!root.TryGetProperty("result", out var result))
            throw new InvalidOperationException("本地后端返回格式不正确。");
        return JsonSerializer.Deserialize<T>(result.GetRawText(), JsonOptions)
               ?? throw new InvalidOperationException("无法解析本地后端数据。");
    }
}
