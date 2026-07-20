using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace ModelDock;

public sealed class ModelEditorDialog : ContentDialog
{
    private readonly BackendClient _backend;
    private readonly ModelEntry? _entry;
    private readonly ComboBox _type = new() { Header = "接口类型", HorizontalAlignment = HorizontalAlignment.Stretch };
    private readonly TextBox _baseUrl = new() { Header = "API Base URL", PlaceholderText = "https://api.example.com/v1" };
    private readonly PasswordBox _apiKey = new() { Header = "API Key", PasswordRevealMode = PasswordRevealMode.Peek };
    private readonly TextBox _upstream = new() { Header = "上游模型 ID" };
    private readonly ComboBox _modelOptions = new() { Header = "接口返回的模型", HorizontalAlignment = HorizontalAlignment.Stretch, Visibility = Visibility.Collapsed };
    private readonly TextBox _name = new() { Header = "名称" };
    private readonly TextBox _provider = new() { Header = "供应商名称" };
    private readonly NumberBox _context = new() { Header = "上下文 token", Minimum = 1, SpinButtonPlacementMode = NumberBoxSpinButtonPlacementMode.Compact };
    private readonly NumberBox _output = new() { Header = "最大输出 token", Minimum = 1, SpinButtonPlacementMode = NumberBoxSpinButtonPlacementMode.Compact };
    private readonly Button _fetch = new() { Content = "获取模型列表", HorizontalAlignment = HorizontalAlignment.Left };

    public Dictionary<string, object>? Payload { get; private set; }

    public ModelEditorDialog(BackendClient backend, ModelEntry? entry)
    {
        _backend = backend;
        _entry = entry;
        Title = entry is null ? "添加模型" : "编辑模型";
        PrimaryButtonText = "保存";
        CloseButtonText = "取消";
        DefaultButton = ContentDialogButton.Primary;

        _type.Items.Add(new ComboBoxItem { Content = "OpenAI Responses", Tag = "responses" });
        _type.Items.Add(new ComboBoxItem { Content = "OpenAI 兼容", Tag = "openai" });
        _type.Items.Add(new ComboBoxItem { Content = "Anthropic 兼容", Tag = "claude" });
        _type.SelectedIndex = entry?.Section switch { "openai-compatibility" => 1, "claude-api-key" => 2, _ => 0 };
        _type.IsEnabled = entry is null;

        if (entry is not null)
        {
            _baseUrl.Text = entry.BaseUrl;
            _apiKey.Password = entry.ApiKey;
            _upstream.Text = entry.Upstream;
            _name.Text = entry.DisplayName;
            _provider.Text = entry.ProviderName;
            _context.Value = entry.ContextWindow ?? double.NaN;
            _output.Value = entry.MaxOutputTokens ?? double.NaN;
        }

        _fetch.Click += Fetch_Click;
        _modelOptions.SelectionChanged += (_, _) =>
        {
            if (_modelOptions.SelectedItem is string value) _upstream.Text = value;
        };
        PrimaryButtonClick += Save_Click;
        var panel = new StackPanel { Spacing = 13, Width = 680 };
        panel.Children.Add(_type);
        panel.Children.Add(_baseUrl);
        panel.Children.Add(_apiKey);
        panel.Children.Add(_upstream);
        panel.Children.Add(_fetch);
        panel.Children.Add(_modelOptions);
        panel.Children.Add(_name);
        panel.Children.Add(_provider);
        var tokenGrid = new Grid { ColumnSpacing = 12 };
        tokenGrid.ColumnDefinitions.Add(new ColumnDefinition()); tokenGrid.ColumnDefinitions.Add(new ColumnDefinition());
        tokenGrid.Children.Add(_context); Grid.SetColumn(_output, 1); tokenGrid.Children.Add(_output);
        panel.Children.Add(tokenGrid);
        Content = new ScrollViewer { Content = panel, MaxHeight = 620 };
    }

    private string TypeValue => (_type.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "responses";

    private async void Fetch_Click(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(_baseUrl.Text) || string.IsNullOrWhiteSpace(_apiKey.Password)) return;
        _fetch.IsEnabled = false;
        _fetch.Content = "正在获取…";
        try
        {
            var result = await _backend.CallAsync<ModelsResult>("fetch_models", new { base_url = _baseUrl.Text, api_key = _apiKey.Password, api_type = TypeValue });
            _modelOptions.Items.Clear();
            foreach (var model in result.Models) _modelOptions.Items.Add(model);
            _modelOptions.Visibility = result.Models.Count > 0 ? Visibility.Visible : Visibility.Collapsed;
            if (string.IsNullOrWhiteSpace(_upstream.Text) && result.Models.Count > 0) _upstream.Text = result.Models[0];
        }
        catch (Exception error)
        {
            App.MainWindowInstance?.ShowError(error.Message);
        }
        finally { _fetch.Content = "获取模型列表"; _fetch.IsEnabled = true; }
    }

    private void Save_Click(ContentDialog sender, ContentDialogButtonClickEventArgs args)
    {
        var upstream = _upstream.Text.Trim();
        if (string.IsNullOrWhiteSpace(_baseUrl.Text) || string.IsNullOrWhiteSpace(_apiKey.Password) || string.IsNullOrWhiteSpace(upstream))
        {
            args.Cancel = true;
            App.MainWindowInstance?.ShowError("API Base URL、API Key 和上游模型 ID 必须填写。");
            return;
        }
        var name = string.IsNullOrWhiteSpace(_name.Text) ? upstream : _name.Text.Trim();
        Payload = new Dictionary<string, object>
        {
            ["base_url"] = _baseUrl.Text.Trim(), ["api_key"] = _apiKey.Password.Trim(),
            ["alias"] = name, ["display_name"] = name,
            ["provider_name"] = string.IsNullOrWhiteSpace(_provider.Text) ? "Custom" : _provider.Text.Trim(),
        };
        if (!double.IsNaN(_context.Value)) Payload["context_window"] = (int)_context.Value;
        if (!double.IsNaN(_output.Value)) Payload["max_output_tokens"] = (int)_output.Value;
        if (_entry is null)
        {
            Payload["api_type"] = TypeValue;
            Payload["model_id"] = upstream;
        }
        else Payload["upstream"] = upstream;
    }
}
