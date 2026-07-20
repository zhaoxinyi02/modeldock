using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Windows.UI;

namespace ModelDock;

public sealed partial class MainWindow
{
    private NavigationView Navigation = null!;
    private Grid HomePage = null!, ModelsPage = null!, RestoresPage = null!, SettingsPage = null!;
    private TextBlock ModeTitle = null!, ModeDescription = null!, ModeBadgeText = null!;
    private Border ModeBadge = null!;
    private FontIcon GatewayStatusIcon = null!, CodexStatusIcon = null!;
    private TextBlock GatewayStatusText = null!, GatewayUrlText = null!, GatewayModelsText = null!;
    private TextBlock CodexStatusText = null!, CodexProcessesText = null!;
    private TextBlock AccountEmailText = null!, AccountPlanText = null!, AccountRefreshText = null!, ThirdPartyCountText = null!;
    private ListView ModelsList = null!, RestoresList = null!;
    private TextBlock LoginStatusText = null!, ConversationText = null!, AboutVersionText = null!;
    private ComboBox ModeCombo = null!;
    private ToggleSwitch AutostartToggle = null!;
    private NumberBox PortBox = null!;
    private ProgressRing BusyRing = null!;
    private InfoBar NoticeBar = null!;

    private static readonly Brush CardBrush = new SolidColorBrush(Color.FromArgb(28, 128, 128, 128));
    private static readonly Brush CardStroke = new SolidColorBrush(Color.FromArgb(55, 128, 128, 128));

    private void BuildInterface()
    {
        Navigation = new NavigationView
        {
            PaneDisplayMode = NavigationViewPaneDisplayMode.Left,
            IsBackButtonVisible = NavigationViewBackButtonVisible.Collapsed,
            IsSettingsVisible = false,
            OpenPaneLength = 230,
            PaneHeader = new TextBlock { Text = "ModelDock", FontSize = 20, FontWeight = Microsoft.UI.Text.FontWeights.SemiBold, Margin = new Thickness(10, 18, 0, 16) }
        };
        Navigation.MenuItems.Add(Nav("首页", "home", Symbol.Home, true));
        Navigation.MenuItems.Add(Nav("配置管理", "models", Symbol.Library));
        Navigation.MenuItems.Add(Nav("回退点", "restores", Symbol.Clock));
        Navigation.MenuItems.Add(Nav("设置", "settings", Symbol.Setting));
        Navigation.SelectionChanged += Navigation_SelectionChanged;

        var host = new Grid();
        HomePage = BuildHome();
        ModelsPage = BuildModels(); ModelsPage.Visibility = Visibility.Collapsed;
        RestoresPage = BuildRestores(); RestoresPage.Visibility = Visibility.Collapsed;
        SettingsPage = BuildSettings(); SettingsPage.Visibility = Visibility.Collapsed;
        host.Children.Add(HomePage); host.Children.Add(ModelsPage); host.Children.Add(RestoresPage); host.Children.Add(SettingsPage);
        Navigation.Content = host;

        BusyRing = new ProgressRing { Width = 46, Height = 46, HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center };
        NoticeBar = new InfoBar { IsOpen = false, IsClosable = true, Margin = new Thickness(20), VerticalAlignment = VerticalAlignment.Top, HorizontalAlignment = HorizontalAlignment.Stretch };
        RootGrid.Children.Add(Navigation); RootGrid.Children.Add(BusyRing); RootGrid.Children.Add(NoticeBar);
    }

    private static NavigationViewItem Nav(string text, string tag, Symbol symbol, bool selected = false) => new()
    {
        Content = text, Tag = tag, Icon = new SymbolIcon(symbol), IsSelected = selected
    };

    private Grid BuildHome()
    {
        var root = PageGrid();
        var stack = new StackPanel { Spacing = 18 };
        stack.Children.Add(Header("Codex Gateway", "官方订阅与第三方模型的 Windows 原生控制中心", Refresh_Click));
        ModeTitle = Text("正在读取", 22, true); ModeDescription = Text(""); ModeDescription.TextWrapping = TextWrapping.Wrap;
        ModeBadgeText = Text(""); ModeBadge = new Border { CornerRadius = new CornerRadius(16), Padding = new Thickness(14, 7, 14, 7), Background = new SolidColorBrush(Color.FromArgb(65, 0, 120, 215)), Child = ModeBadgeText, VerticalAlignment = VerticalAlignment.Center };
        var heroGrid = Columns("*", "Auto"); heroGrid.Children.Add(new StackPanel { Spacing = 5, Children = { ModeTitle, ModeDescription } }); Grid.SetColumn(ModeBadge, 1); heroGrid.Children.Add(ModeBadge);
        stack.Children.Add(Card(heroGrid));

        GatewayStatusIcon = Dot(); GatewayStatusText = Text(""); GatewayUrlText = Text(""); GatewayModelsText = Text("");
        var gateway = new StackPanel { Spacing = 11, Children = { Text("本地网关", 16, true), StatusLine(GatewayStatusIcon, GatewayStatusText), GatewayUrlText, GatewayModelsText } };
        gateway.Children.Add(ButtonRow(Action("启动", "start", GatewayAction_Click), Action("停止", "stop", GatewayAction_Click), Action("重启", "restart", GatewayAction_Click)));
        CodexStatusIcon = Dot(); CodexStatusText = Text(""); CodexProcessesText = Text("");
        var codex = new StackPanel { Spacing = 11, Children = { Text("Codex Desktop", 16, true), StatusLine(CodexStatusIcon, CodexStatusText), CodexProcessesText } };
        codex.Children.Add(ButtonRow(Action("打开", "start", CodexAction_Click), Action("停止", "stop", CodexAction_Click), Action("重启", "restart", CodexAction_Click)));
        var status = Columns("*", "*"); status.ColumnSpacing = 16; status.Children.Add(Card(gateway)); var codexCard = Card(codex); Grid.SetColumn(codexCard, 1); status.Children.Add(codexCard); stack.Children.Add(status);

        AccountEmailText = Text(""); AccountPlanText = Text(""); AccountRefreshText = Text(""); ThirdPartyCountText = Text("");
        var account = new StackPanel { Spacing = 9, Children = { Text("官方账号", 16, true), LabelValue("邮箱", AccountEmailText), LabelValue("套餐", AccountPlanText), LabelValue("凭据更新时间", AccountRefreshText), LabelValue("第三方模型", ThirdPartyCountText) } };
        stack.Children.Add(Card(account));
        root.Children.Add(new ScrollViewer { Content = stack }); return root;
    }

    private Grid BuildModels()
    {
        var root = PageGrid(); AddRows(root, "Auto", "*", "Auto");
        root.Children.Add(TitleBlock("配置管理", "双击模型进行编辑；序号固定，移动只改变 Codex 中的排列顺序"));
        var body = new Grid(); AddRows(body, "Auto", "*");
        body.Children.Add(ModelRow("序号", "名称", "上游模型", "类型", "URL", "上下文", "最大输出", true));
        ModelsList = new ListView { SelectionMode = ListViewSelectionMode.Single }; ModelsList.DoubleTapped += ModelsList_DoubleTapped; Grid.SetRow(ModelsList, 1); body.Children.Add(ModelsList);
        var card = Card(body); card.Padding = new Thickness(8); Grid.SetRow(card, 1); root.Children.Add(card);
        var buttons = ButtonRow(Action("添加模型", null, AddModel_Click), Action("编辑", null, EditModel_Click), Action("上移", "-1", MoveModel_Click), Action("下移", "1", MoveModel_Click), Action("删除", null, DeleteModel_Click));
        buttons.Margin = new Thickness(0, 14, 0, 0); Grid.SetRow(buttons, 2); root.Children.Add(buttons); return root;
    }

    private Grid BuildRestores()
    {
        var root = PageGrid(); AddRows(root, "Auto", "*", "Auto"); root.Children.Add(TitleBlock("回退点", "恢复网关、Codex provider、模型目录和登录配置"));
        RestoresList = new ListView { SelectionMode = ListViewSelectionMode.Single }; Grid.SetRow(RestoresList, 1); root.Children.Add(RestoresList);
        var buttons = ButtonRow(Action("创建手动回退点", null, CreateRestore_Click), Action("恢复所选回退点", null, Restore_Click)); buttons.Margin = new Thickness(0, 14, 0, 0); Grid.SetRow(buttons, 2); root.Children.Add(buttons); return root;
    }

    private Grid BuildSettings()
    {
        var root = PageGrid(); var stack = new StackPanel { Spacing = 16 }; stack.Children.Add(TitleBlock("设置", "模式、官方凭据、会话保护与网关"));
        LoginStatusText = Text(""); LoginStatusText.TextWrapping = TextWrapping.Wrap;
        ModeCombo = new ComboBox { Header = "运行模式", HorizontalAlignment = HorizontalAlignment.Stretch };
        ModeCombo.Items.Add(Combo("纯官方订阅", "pure_official")); ModeCombo.Items.Add(Combo("官方订阅 + 第三方 API", "official_plus_api")); ModeCombo.Items.Add(Combo("纯 API + 第三方模型", "api_only")); ModeCombo.SelectionChanged += ModeCombo_SelectionChanged;
        var login = new StackPanel { Spacing = 11, Children = { Text("Codex 登录状态", 16, true), LoginStatusText, ButtonRow(Action("重新登录 / 刷新凭据", null, Login_Click), Action("打开官方 Usage", null, Usage_Click)), ModeCombo } }; stack.Children.Add(Card(login));
        ConversationText = Text(""); var conversation = new StackPanel { Spacing = 11, Children = { Text("会话保护", 16, true), ConversationText, ButtonRow(Action("创建会话索引快照", null, ConversationSnapshot_Click), Action("修复并统一会话列表", null, ConversationRepair_Click)) } }; stack.Children.Add(Card(conversation));
        AutostartToggle = new ToggleSwitch { Header = "登录后自动启动本地网关" }; AutostartToggle.Toggled += AutostartToggle_Toggled;
        PortBox = new NumberBox { Header = "端口", Minimum = 1, Maximum = 65535, Width = 160, SpinButtonPlacementMode = NumberBoxSpinButtonPlacementMode.Inline };
        var portRow = ButtonRow(PortBox, Action("应用端口并重启", null, ApplyPort_Click));
        var gateway = new StackPanel { Spacing = 11, Children = { Text("开机自启与端口", 16, true), AutostartToggle, portRow } }; stack.Children.Add(Card(gateway));
        AboutVersionText = Text(""); var about = new StackPanel { Spacing = 7, Children = { Text("关于", 16, true), AboutVersionText, Text("WinUI 3 · Windows App SDK · Mica"), Text("本地网关 CLIProxyAPI 7.2.92") } }; stack.Children.Add(Card(about));
        root.Children.Add(new ScrollViewer { Content = stack }); return root;
    }

    private void PopulateModels(IEnumerable<ModelEntry> models)
    {
        ModelsList.Items.Clear();
        foreach (var model in models)
            ModelsList.Items.Add(new ListViewItem { Tag = model, Content = ModelRow(model.Number.ToString(), model.DisplayName, model.Upstream, model.TypeLabel, model.BaseUrl, model.ContextText, model.OutputText) });
    }

    private void PopulateRestores(IEnumerable<RestorePoint> restores)
    {
        RestoresList.Items.Clear();
        foreach (var point in restores)
        {
            var grid = Columns("*", "Auto");
            grid.Children.Add(new StackPanel { Spacing = 4, Children = { Text(point.Name, 15, true), Text(point.Notes) } });
            var time = Text(point.CreatedAt); Grid.SetColumn(time, 1); grid.Children.Add(time);
            RestoresList.Items.Add(new ListViewItem { Tag = point, Content = Card(grid), Margin = new Thickness(0, 0, 0, 7) });
        }
    }

    private static Grid ModelRow(string a, string b, string c, string d, string e, string f, string g, bool bold = false)
    {
        var grid = Columns("52", "1.25*", "1*", "1*", "1.5*", "92", "92"); grid.Padding = new Thickness(8, 9, 8, 9);
        var values = new[] { a, b, c, d, e, f, g };
        for (var i = 0; i < values.Length; i++) { var text = Text(values[i], 14, bold); text.TextTrimming = TextTrimming.CharacterEllipsis; Grid.SetColumn(text, i); grid.Children.Add(text); }
        return grid;
    }

    private static Grid PageGrid() => new() { Padding = new Thickness(28, 22, 28, 26) };
    private static Border Card(UIElement child) => new() { Child = child, Background = CardBrush, BorderBrush = CardStroke, BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(12), Padding = new Thickness(20) };
    private static TextBlock Text(string value, double size = 14, bool bold = false) => new() { Text = value, FontSize = size, FontWeight = bold ? Microsoft.UI.Text.FontWeights.SemiBold : Microsoft.UI.Text.FontWeights.Normal, VerticalAlignment = VerticalAlignment.Center };
    private static FontIcon Dot() => new() { Glyph = "\uE73E", FontSize = 11 };
    private static StackPanel StatusLine(FontIcon icon, TextBlock text) => new() { Orientation = Orientation.Horizontal, Spacing = 8, Children = { icon, text } };
    private static StackPanel ButtonRow(params UIElement[] controls) { var row = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8 }; foreach (var item in controls) row.Children.Add(item); return row; }
    private static Button Action(string text, string? tag, RoutedEventHandler handler) { var button = new Button { Content = text, Tag = tag }; button.Click += handler; return button; }
    private static ComboBoxItem Combo(string text, string tag) => new() { Content = text, Tag = tag };
    private static Grid LabelValue(string label, TextBlock value) { var grid = Columns("135", "*"); grid.Children.Add(Text(label)); Grid.SetColumn(value, 1); grid.Children.Add(value); return grid; }
    private static StackPanel TitleBlock(string title, string subtitle) => new() { Spacing = 5, Margin = new Thickness(0, 0, 0, 16), Children = { Text(title, 30, true), Text(subtitle) } };
    private static Grid Header(string title, string subtitle, RoutedEventHandler refresh)
    {
        var grid = Columns("*", "Auto"); grid.Children.Add(TitleBlock(title, subtitle)); var button = Action("刷新", null, refresh); button.VerticalAlignment = VerticalAlignment.Center; Grid.SetColumn(button, 1); grid.Children.Add(button); return grid;
    }
    private static Grid Columns(params string[] widths) { var grid = new Grid(); foreach (var width in widths) grid.ColumnDefinitions.Add(new ColumnDefinition { Width = ParseLength(width) }); return grid; }
    private static void AddRows(Grid grid, params string[] heights) { foreach (var height in heights) grid.RowDefinitions.Add(new RowDefinition { Height = ParseLength(height) }); }
    private static GridLength ParseLength(string value) => value == "*" ? new GridLength(1, GridUnitType.Star) : value == "Auto" ? GridLength.Auto : value.EndsWith('*') ? new GridLength(double.Parse(value.TrimEnd('*')), GridUnitType.Star) : new GridLength(double.Parse(value));
}
