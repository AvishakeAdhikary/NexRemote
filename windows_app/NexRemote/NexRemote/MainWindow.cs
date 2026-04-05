using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.UI;
using Microsoft.UI.Text;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using NexRemote.Helpers;
using NexRemote.Models;
using NexRemote.Services;
using NexRemote.ViewModels;
using Serilog;
using WinRT.Interop;

namespace NexRemote;

public sealed class MainWindow : Window
{
    private readonly IAppSettingsService _settingsService;
    private readonly IThemeService _themeService;
    private readonly ITrayIconService _trayIconService;
    private readonly IServerCoordinator _serverCoordinator;
    private readonly IConnectionApprovalService _approvalService;
    private readonly ICameraPermissionService _cameraPermissionService;
    private readonly AppWindow _appWindow;

    private readonly Grid _rootGrid;
    private readonly TextBlock _serverStatusText = ValueText();
    private readonly TextBlock _serverPortsText = MutedText();
    private readonly TextBlock _lanIpText = MutedText();
    private readonly TextBlock _deviceIdText = MutedText();
    private readonly TextBlock _permissionSummaryText = MutedText(wrap: true);
    private readonly TextBlock _legalStatusText = MutedText(wrap: true);
    private readonly TextBlock _qrPayloadText = MutedText(wrap: true);
    private readonly TextBox _pcNameBox = new() { Header = "PC Name" };
    private readonly ComboBox _themeBox = new();
    private readonly ToggleSwitch _enableRemoteAccessSwitch = new() { Header = "Allow local network connections" };
    private readonly ToggleSwitch _autoStartSwitch = new() { Header = "Start with Windows" };
    private readonly ToggleSwitch _minimizeToTraySwitch = new() { Header = "Minimize to system tray" };
    private readonly ToggleSwitch _showNotificationsSwitch = new() { Header = "Show notifications" };
    private readonly TextBox _serverPortBox = new() { Header = "Secure port" };
    private readonly TextBox _serverPortInsecureBox = new() { Header = "Fallback port" };
    private readonly TextBox _discoveryPortBox = new() { Header = "Discovery port" };
    private readonly ComboBox _firewallProfileBox = new();
    private readonly ToggleSwitch _requireApprovalSwitch = new() { Header = "Require approval for new devices" };
    private readonly ToggleSwitch _auditLoggingSwitch = new() { Header = "Audit logging" };
    private readonly ToggleSwitch _inputValidationSwitch = new() { Header = "Input validation" };
    private readonly Border _gamepadBannerCard;
    private readonly TextBlock _gamepadSupportText = new() { TextWrapping = TextWrapping.WrapWholeWords };
    private readonly StackPanel _trustedDevicesPanel = new() { Spacing = 10 };
    private readonly StackPanel _connectedDevicesPanel = new() { Spacing = 10 };
    private readonly Image _qrImage = new() { Stretch = Stretch.Uniform };
    private readonly TextBlock _qrPlaceholderText = new()
    {
        Text = "QR will appear when the server is ready.",
        Width = 150,
        HorizontalAlignment = HorizontalAlignment.Center,
        VerticalAlignment = VerticalAlignment.Center,
        TextWrapping = TextWrapping.WrapWholeWords,
        TextAlignment = TextAlignment.Center,
        Opacity = 0.74
    };
    private readonly Button _toggleServerButton = new()
    {
        Background = new SolidColorBrush(ColorHelper.FromArgb(255, 14, 94, 234)),
        Foreground = new SolidColorBrush(Colors.White)
    };
    private readonly List<Window> _secondaryWindows = new();

    private bool _allowClose;
    private bool _initialized;
    private bool _cleanupComplete;
    private int _exitRequested;

    public MainWindow()
        : this(App.Host.Services)
    {
    }

    public MainWindow(IServiceProvider services)
    {
        _settingsService = services.GetRequiredService<IAppSettingsService>();
        _themeService = services.GetRequiredService<IThemeService>();
        _trayIconService = services.GetRequiredService<ITrayIconService>();
        _serverCoordinator = services.GetRequiredService<IServerCoordinator>();
        _approvalService = services.GetRequiredService<IConnectionApprovalService>();
        _cameraPermissionService = services.GetRequiredService<ICameraPermissionService>();
        ViewModel = services.GetRequiredService<MainWindowViewModel>();

        Title = "NexRemote";
        SystemBackdrop = CreateMicaAltBackdrop();

        _themeBox.Items.Add(new ComboBoxItem { Content = "System" });
        _themeBox.Items.Add(new ComboBoxItem { Content = "Light" });
        _themeBox.Items.Add(new ComboBoxItem { Content = "Dark" });
        _themeBox.SelectionChanged += OnThemeSelectionChanged;
        _firewallProfileBox.Items.Add(new ComboBoxItem { Content = "Private only" });
        _firewallProfileBox.Items.Add(new ComboBoxItem { Content = "Public only" });
        _firewallProfileBox.Items.Add(new ComboBoxItem { Content = "All profiles" });
        _toggleServerButton.Click += OnToggleServerClick;

        _rootGrid = new Grid
        {
            Background = (Brush)Application.Current.Resources["ApplicationPageBackgroundThemeBrush"],
            Padding = new Thickness(24),
            RowSpacing = 20
        };
        _rootGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        _rootGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        _rootGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        _rootGrid.Children.Add(new StackPanel
        {
            Spacing = 6,
            Children =
            {
                new TextBlock { Text = "NexRemote by Neural Nexus Studios", FontSize = 28, FontWeight = FontWeights.SemiBold },
                new TextBlock
                {
                    Text = "Native WinUI desktop host that preserves the existing NexRemote client protocol and local-first consent flow.",
                    Opacity = 0.74,
                    TextWrapping = TextWrapping.WrapWholeWords
                }
            }
        });

        var scroll = new ScrollViewer();
        Grid.SetRow(scroll, 1);
        _rootGrid.Children.Add(scroll);
        var content = new StackPanel { Spacing = 20 };
        scroll.Content = content;

        content.Children.Add(BuildDashboardCard());
        content.Children.Add(BuildQrCard());
        content.Children.Add(BuildSettingsGrid());
        content.Children.Add(BuildDevicesGrid());
        content.Children.Add(BuildLegalCard());

        _gamepadBannerCard = new Border
        {
            Background = new SolidColorBrush(ColorHelper.FromArgb(38, 198, 138, 0)),
            BorderBrush = new SolidColorBrush(ColorHelper.FromArgb(96, 198, 138, 0)),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(20),
            Padding = new Thickness(20),
            Child = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                Spacing = 12,
                Children =
                {
                    new TextBlock { Text = "Gamepad compatibility", FontWeight = FontWeights.SemiBold },
                    _gamepadSupportText,
                    Button("Open ViGEm Guide", OnOpenViGemGuideClick),
                    Button("Open Support", OnOpenSupportClick)
                }
            }
        };
        Grid.SetRow(_gamepadBannerCard, 2);
        _rootGrid.Children.Add(_gamepadBannerCard);
        Content = _rootGrid;

        var hWnd = WindowNative.GetWindowHandle(this);
        _appWindow = AppWindow.GetFromWindowId(Microsoft.UI.Win32Interop.GetWindowIdFromWindow(hWnd));
        _appWindow.Closing += OnAppWindowClosing;
        _rootGrid.Loaded += OnLoaded;
        Closed += OnClosed;
    }

    public MainWindowViewModel ViewModel { get; }

    public void RestoreFromActivation()
    {
        _appWindow.Show();
        Activate();
    }

    private Border BuildDashboardCard()
    {
        var stack = new StackPanel { Spacing = 12 };
        stack.Children.Add(new TextBlock { Text = "Dashboard", FontSize = 20, FontWeight = FontWeights.SemiBold });
        stack.Children.Add(_serverStatusText);
        stack.Children.Add(_serverPortsText);
        stack.Children.Add(_lanIpText);
        stack.Children.Add(_deviceIdText);
        stack.Children.Add(_permissionSummaryText);
        stack.Children.Add(_legalStatusText);
        stack.Children.Add(_qrPayloadText);
        var buttons = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 12 };
        buttons.Children.Add(_toggleServerButton);
        buttons.Children.Add(Button("Save Settings", OnSaveSettingsClick));
        buttons.Children.Add(Button("Review Network Permission", OnReviewPermissionsClick));
        buttons.Children.Add(Button("Review Camera Permission", OnReviewCameraPermissionClick));
        stack.Children.Add(buttons);
        return Card(stack);
    }

    private Border BuildQrCard()
    {
        var qrGrid = new Grid();
        qrGrid.Children.Add(_qrImage);
        qrGrid.Children.Add(_qrPlaceholderText);
        var stack = new StackPanel { Spacing = 12, HorizontalAlignment = HorizontalAlignment.Center };
        stack.Children.Add(new TextBlock { Text = "Quick Connect", FontSize = 20, FontWeight = FontWeights.SemiBold });
        stack.Children.Add(new Border
        {
            Width = 220,
            Height = 220,
            CornerRadius = new CornerRadius(18),
            BorderThickness = new Thickness(1),
            BorderBrush = (Brush)Application.Current.Resources["CardStrokeColorDefaultBrush"],
            Background = (Brush)Application.Current.Resources["CardBackgroundFillColorSecondaryBrush"],
            Child = qrGrid
        });
        return Card(stack);
    }

    private Grid BuildSettingsGrid()
    {
        var grid = TwoColumnGrid();
        grid.Children.Add(BuildGeneralCard());
        var network = BuildNetworkCard();
        Grid.SetColumn(network, 1);
        grid.Children.Add(network);
        return grid;
    }

    private Border BuildGeneralCard()
    {
        var stack = new StackPanel { Spacing = 12 };
        stack.Children.Add(new TextBlock { Text = "Appearance And General", FontSize = 20, FontWeight = FontWeights.SemiBold });
        stack.Children.Add(_pcNameBox);
        stack.Children.Add(_themeBox);
        stack.Children.Add(_autoStartSwitch);
        stack.Children.Add(_minimizeToTraySwitch);
        stack.Children.Add(_showNotificationsSwitch);
        return Card(stack);
    }

    private Border BuildNetworkCard()
    {
        var stack = new StackPanel { Spacing = 12 };
        stack.Children.Add(new TextBlock { Text = "Network And Privacy", FontSize = 20, FontWeight = FontWeights.SemiBold });
        stack.Children.Add(_enableRemoteAccessSwitch);
        stack.Children.Add(_serverPortBox);
        stack.Children.Add(_serverPortInsecureBox);
        stack.Children.Add(_discoveryPortBox);
        stack.Children.Add(_firewallProfileBox);
        stack.Children.Add(_requireApprovalSwitch);
        stack.Children.Add(_auditLoggingSwitch);
        stack.Children.Add(_inputValidationSwitch);
        return Card(stack);
    }

    private Grid BuildDevicesGrid()
    {
        var grid = TwoColumnGrid();
        grid.Children.Add(Card(new StackPanel
        {
            Spacing = 12,
            Children =
            {
                new TextBlock { Text = "Connected Devices", FontSize = 20, FontWeight = FontWeights.SemiBold },
                _connectedDevicesPanel
            }
        }));
        var trusted = Card(new StackPanel
        {
            Spacing = 12,
            Children =
            {
                new TextBlock { Text = "Trusted Devices", FontSize = 20, FontWeight = FontWeights.SemiBold },
                _trustedDevicesPanel
            }
        });
        Grid.SetColumn(trusted, 1);
        grid.Children.Add(trusted);
        return grid;
    }

    private Border BuildLegalCard()
    {
        var buttons = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 12 };
        buttons.Children.Add(Button("View Terms of Service", OnViewTermsOfServiceClick));
        buttons.Children.Add(Button("View Terms and Conditions", OnViewTermsAndConditionsClick));
        buttons.Children.Add(Button("View Privacy Policy", OnViewPrivacyPolicyClick));
        return Card(new StackPanel
        {
            Spacing = 12,
            Children =
            {
                new TextBlock { Text = "Legal", FontSize = 20, FontWeight = FontWeights.SemiBold },
                MutedText("Legal documents open in their own pages so they can be reviewed separately before first use and at any later time.", true),
                buttons
            }
        });
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (_initialized) return;
        _initialized = true;
        LogStartup("MainWindow loaded.");
        _themeService.ApplyTheme(this, _settingsService.Current.ThemePreference);
        await ViewModel.InitializeAsync();
        LogStartup("ViewModel initialized.");
        RefreshControlsFromViewModel();
        InitializeTray();
        LogStartup("Tray initialized.");
        await EnsureLegalAcceptanceAsync();
        LogStartup("Legal acceptance checked.");
        await EnsureServerConsentAsync(false);
        LogStartup("Server consent checked.");
        await StartServerIfNeededAsync();
    }

    private void InitializeTray()
    {
        _trayIconService.ShowRequested += OnTrayShowRequested;
        _trayIconService.ToggleServerRequested += OnTrayToggleServerRequested;
        _trayIconService.ExitRequested += OnTrayExitRequested;
        _serverCoordinator.ClientConnected += OnRemoteServerClientConnected;
        _serverCoordinator.ClientDisconnected += OnRemoteServerClientDisconnected;
        _approvalService.ApprovalRequested += OnApprovalRequested;
        _trayIconService.Initialize();
        _trayIconService.UpdateServerState(ViewModel.IsServerRunning, ViewModel.ServerStatusText);
    }

    private async Task EnsureLegalAcceptanceAsync()
    {
        if (HasAcceptedCurrentLegalDocuments(_settingsService.Current)) return;
        var tosCheck = new CheckBox { Content = "I accept the Terms of Service.", IsEnabled = false };
        var conditionsCheck = new CheckBox { Content = "I accept the Terms and Conditions.", IsEnabled = false };
        var privacyCheck = new CheckBox { Content = "I accept the Privacy Policy.", IsEnabled = false };
        var tosViewed = false;
        var conditionsViewed = false;
        var privacyViewed = false;
        var dialog = new ContentDialog
        {
            Title = "Review Legal Documents",
            PrimaryButtonText = "Continue",
            CloseButtonText = "Exit",
            DefaultButton = ContentDialogButton.Primary,
            IsPrimaryButtonEnabled = false,
            XamlRoot = _rootGrid.XamlRoot
        };
        void UpdateState() => dialog.IsPrimaryButtonEnabled =
            tosViewed &&
            conditionsViewed &&
            privacyViewed &&
            tosCheck.IsChecked == true &&
            conditionsCheck.IsChecked == true &&
            privacyCheck.IsChecked == true;
        tosCheck.Checked += (_, _) => UpdateState();
        tosCheck.Unchecked += (_, _) => UpdateState();
        conditionsCheck.Checked += (_, _) => UpdateState();
        conditionsCheck.Unchecked += (_, _) => UpdateState();
        privacyCheck.Checked += (_, _) => UpdateState();
        privacyCheck.Unchecked += (_, _) => UpdateState();
        dialog.Content = new StackPanel
        {
            Spacing = 12,
            Children =
            {
                new TextBlock { Text = "Review the legal documents in their dedicated pages before using NexRemote for the first time.", TextWrapping = TextWrapping.WrapWholeWords },
                new StackPanel
                {
                    Orientation = Orientation.Horizontal,
                    Spacing = 12,
                    Children =
                    {
                        Button("View Terms of Service", (_, _) => { tosViewed = true; tosCheck.IsEnabled = true; UpdateState(); OpenLegalDocumentWindow("Terms of Service", ViewModel.TermsOfServiceText); }),
                        Button("View Terms and Conditions", (_, _) => { conditionsViewed = true; conditionsCheck.IsEnabled = true; UpdateState(); OpenLegalDocumentWindow("Terms and Conditions", ViewModel.TermsAndConditionsText); }),
                        Button("View Privacy Policy", (_, _) => { privacyViewed = true; privacyCheck.IsEnabled = true; UpdateState(); OpenLegalDocumentWindow("Privacy Policy", ViewModel.PrivacyPolicyText); })
                    }
                },
                tosCheck,
                conditionsCheck,
                privacyCheck
            }
        };
        if (await dialog.ShowAsync() != ContentDialogResult.Primary)
        {
            _allowClose = true;
            Close();
            return;
        }

        var acceptedAt = DateTimeOffset.Now;
        _settingsService.Update(settings =>
        {
            settings.TermsAccepted = true;
            settings.TermsAcceptedAt = acceptedAt;
            settings.TermsOfServiceAccepted = true;
            settings.TermsOfServiceAcceptedAt = acceptedAt;
            settings.TermsOfServiceVersionAccepted = AppSettings.CurrentTermsOfServiceVersion;
            settings.TermsAndConditionsAccepted = true;
            settings.TermsAndConditionsAcceptedAt = acceptedAt;
            settings.TermsAndConditionsVersionAccepted = AppSettings.CurrentTermsAndConditionsVersion;
            settings.PrivacyPolicyAccepted = true;
            settings.PrivacyPolicyAcceptedAt = acceptedAt;
            settings.PrivacyPolicyReviewedAt = acceptedAt;
            settings.PrivacyPolicyVersionAccepted = AppSettings.CurrentPrivacyPolicyVersion;
        });
        await _settingsService.SaveAsync();
        await ViewModel.InitializeAsync();
        RefreshControlsFromViewModel();
    }

    private async Task EnsureServerConsentAsync(bool forcePrompt)
    {
        if (_settingsService.Current.RemoteControlConsentGranted && !forcePrompt) return;
        var dialog = ConsentDialog("Allow Remote Networking", "When enabled, NexRemote can listen on your local network, receive approved client requests, and exchange remote control messages on your configured ports.");
        if (await dialog.ShowAsync() == ContentDialogResult.Primary)
        {
            _settingsService.Update(settings =>
            {
                settings.RemoteControlConsentGranted = true;
                settings.EnableRemoteAccess = true;
            });
            await _settingsService.SaveAsync();
            await ViewModel.InitializeAsync();
            RefreshControlsFromViewModel();
            await StartServerIfNeededAsync();
        }
    }

    private async Task EnsureCameraConsentAsync(bool forcePrompt)
    {
        if (_settingsService.Current.CameraAccessConsentGranted && !forcePrompt) return;
        var cameraState = await _cameraPermissionService.GetAccessStateAsync();
        if (cameraState is CameraAccessState.DeniedBySystem or CameraAccessState.DeniedByUser)
        {
            await _cameraPermissionService.OpenPrivacySettingsAsync();
        }
        var dialog = ConsentDialog("Allow Camera Streaming", "Camera streaming can expose video from cameras attached to this PC. Allow this only if you want approved clients to request camera enumeration and streaming.");
        if (await dialog.ShowAsync() == ContentDialogResult.Primary)
        {
            _settingsService.Update(settings =>
            {
                settings.CameraAccessConsentGranted = cameraState is not CameraAccessState.DeniedBySystem and not CameraAccessState.DeniedByUser;
                settings.PrivacyPolicyReviewedAt ??= DateTimeOffset.Now;
            });
            await _settingsService.SaveAsync();
            await ViewModel.InitializeAsync();
            RefreshControlsFromViewModel();
        }
    }

    private async void OnToggleServerClick(object sender, RoutedEventArgs e) { await ViewModel.ToggleServerAsync(); RefreshControlsFromViewModel(); _trayIconService.UpdateServerState(ViewModel.IsServerRunning, ViewModel.ServerStatusText); }
    private async void OnSaveSettingsClick(object sender, RoutedEventArgs e) { ApplyControlValuesToViewModel(); await ViewModel.SaveAsync(); RefreshControlsFromViewModel(); _themeService.ApplyTheme(this, ViewModel.SelectedThemePreference); await StartServerIfNeededAsync(); _trayIconService.ShowMessage("NexRemote", "Settings saved locally."); }
    private async void OnReviewPermissionsClick(object sender, RoutedEventArgs e) { await EnsureServerConsentAsync(true); RefreshControlsFromViewModel(); }
    private async void OnReviewCameraPermissionClick(object sender, RoutedEventArgs e) { await EnsureCameraConsentAsync(true); RefreshControlsFromViewModel(); }
    private void OnThemeSelectionChanged(object sender, SelectionChangedEventArgs e) { ViewModel.ThemeSelectionIndex = _themeBox.SelectedIndex; _themeService.ApplyTheme(this, ViewModel.SelectedThemePreference); }
    private async void OnOpenSupportClick(object sender, RoutedEventArgs e) => await ViewModel.OpenSupportAsync();
    private async void OnOpenViGemGuideClick(object sender, RoutedEventArgs e) => await ViewModel.OpenViGemGuideAsync();
    private void OnViewTermsOfServiceClick(object sender, RoutedEventArgs e) => OpenLegalDocumentWindow("Terms of Service", ViewModel.TermsOfServiceText);
    private void OnViewTermsAndConditionsClick(object sender, RoutedEventArgs e) => OpenLegalDocumentWindow("Terms and Conditions", ViewModel.TermsAndConditionsText);
    private void OnViewPrivacyPolicyClick(object sender, RoutedEventArgs e) => OpenLegalDocumentWindow("Privacy Policy", ViewModel.PrivacyPolicyText);

    private void OpenLegalDocumentWindow(string title, string body)
    {
        var window = new LegalDocumentWindow(title, body, _themeService, _settingsService.Current.ThemePreference);
        window.Closed += (_, _) => _secondaryWindows.Remove(window);
        _secondaryWindows.Add(window);
        window.Activate();
    }

    private void OnTrayShowRequested(object? sender, EventArgs e) => RestoreFromActivation();
    private async void OnTrayToggleServerRequested(object? sender, EventArgs e) { await ViewModel.ToggleServerAsync(); RefreshControlsFromViewModel(); _trayIconService.UpdateServerState(ViewModel.IsServerRunning, ViewModel.ServerStatusText); }
    private async void OnTrayExitRequested(object? sender, EventArgs e) => await RequestExitAsync();

    private void OnAppWindowClosing(AppWindow sender, AppWindowClosingEventArgs args)
    {
        if (_allowClose)
        {
            return;
        }

        args.Cancel = true;
        if (_settingsService.Current.MinimizeToTray)
        {
            if (!_settingsService.Current.BackgroundConsentGranted) { _ = AskForBackgroundConsentAndHideAsync(); return; }
            sender.Hide();
            _trayIconService.ShowMessage("NexRemote", "NexRemote is still available in the system tray.");
            return;
        }

        _ = RequestExitAsync();
    }

    private async Task AskForBackgroundConsentAndHideAsync()
    {
        var dialog = ConsentDialog("Keep NexRemote In The Tray?", "NexRemote can stay available from the system tray so the server and approval prompts remain reachable in the background.", primary: "Keep Running", close: "Close App");
        if (await dialog.ShowAsync() == ContentDialogResult.Primary)
        {
            _settingsService.Update(settings => settings.BackgroundConsentGranted = true);
            await _settingsService.SaveAsync();
            _appWindow.Hide();
            _trayIconService.ShowMessage("NexRemote", "NexRemote is now running from the system tray.");
            return;
        }

        _allowClose = true;
        Close();
    }

    private void OnClosed(object sender, WindowEventArgs args)
    {
        if (_cleanupComplete) return;
        _cleanupComplete = true;
        _rootGrid.Loaded -= OnLoaded;
        Closed -= OnClosed;
        _appWindow.Closing -= OnAppWindowClosing;
        _trayIconService.ShowRequested -= OnTrayShowRequested;
        _trayIconService.ToggleServerRequested -= OnTrayToggleServerRequested;
        _trayIconService.ExitRequested -= OnTrayExitRequested;
        _serverCoordinator.ClientConnected -= OnRemoteServerClientConnected;
        _serverCoordinator.ClientDisconnected -= OnRemoteServerClientDisconnected;
        _approvalService.ApprovalRequested -= OnApprovalRequested;
        _trayIconService.Dispose();
        foreach (var window in _secondaryWindows.ToArray()) { try { window.Close(); } catch { } }
        _secondaryWindows.Clear();
    }

    private void OnApprovalRequested(object? sender, PendingApprovalRequestEventArgs e) => DispatcherQueue.TryEnqueue(() => _ = ShowApprovalDialogAsync(e.DeviceId, e.DeviceName));

    private async Task ShowApprovalDialogAsync(string deviceId, string deviceName)
    {
        RestoreFromActivation();
        var dialog = new ContentDialog
        {
            Title = "New Connection Request",
            PrimaryButtonText = "Approve",
            CloseButtonText = "Reject",
            DefaultButton = ContentDialogButton.Primary,
            XamlRoot = _rootGrid.XamlRoot,
            Content = new TextBlock
            {
                Text = $"Approve this connection only if you recognize the device.\n\nDevice Name: {deviceName}\nDevice ID: {deviceId}\n\nThis request auto-rejects after {ProtocolConstants.ApprovalTimeoutSeconds} seconds so the mobile client can fail fast instead of hanging.",
                TextWrapping = TextWrapping.WrapWholeWords,
                Width = 420
            }
        };
        var dialogTask = dialog.ShowAsync().AsTask();
        var completed = await Task.WhenAny(dialogTask, Task.Delay(TimeSpan.FromSeconds(ProtocolConstants.ApprovalTimeoutSeconds)));
        if (completed == dialogTask) { _approvalService.CompleteApproval(deviceId, await dialogTask == ContentDialogResult.Primary); return; }
        dialog.Hide();
        _approvalService.CompleteApproval(deviceId, false);
    }

    private async Task StartServerIfNeededAsync()
    {
        if (ViewModel.IsServerRunning)
        {
            LogStartup("Server already running.");
            _trayIconService.UpdateServerState(ViewModel.IsServerRunning, ViewModel.ServerStatusText);
            return;
        }

        var settings = _settingsService.Current;
        LogStartup($"Auto-start evaluation: remote={settings.EnableRemoteAccess}, consent={settings.RemoteControlConsentGranted}, legal={HasAcceptedCurrentLegalDocuments(settings)}.");
        if (!settings.EnableRemoteAccess || !settings.RemoteControlConsentGranted || !HasAcceptedCurrentLegalDocuments(settings))
        {
            LogStartup("Auto-start skipped because prerequisites were not met.");
            return;
        }

        try
        {
            await ViewModel.ToggleServerAsync();
            LogStartup($"Auto-start completed. Running={ViewModel.IsServerRunning}. Status={ViewModel.ServerStatusText}");
            RefreshControlsFromViewModel();
            _trayIconService.UpdateServerState(ViewModel.IsServerRunning, ViewModel.ServerStatusText);
        }
        catch (Exception ex)
        {
            LogStartup("Auto-start failed.", ex);
            throw;
        }
    }

    private static void LogStartup(string message, Exception? exception = null)
    {
        if (exception is null)
        {
            Log.Information("{Message}", message);
        }
        else
        {
            Log.Error(exception, "{Message}", message);
        }
    }

    private async Task RequestExitAsync()
    {
        if (System.Threading.Interlocked.Exchange(ref _exitRequested, 1) == 1)
        {
            return;
        }

        try
        {
            await App.ShutdownAsync();
        }
        finally
        {
            _allowClose = true;
            Close();
        }
    }

    private void OnRemoteServerClientConnected(object? sender, ClientConnectionEventArgs e) => DispatcherQueue.TryEnqueue(() => { ViewModel.UpsertConnectedClient(e.ClientId, e.DeviceName, "Connected"); ViewModel.RefreshTrustedDevices(); RefreshControlsFromViewModel(); });
    private void OnRemoteServerClientDisconnected(object? sender, ClientConnectionEventArgs e) => DispatcherQueue.TryEnqueue(() => { ViewModel.RemoveConnectedClient(e.ClientId); RefreshControlsFromViewModel(); });

    private void ApplyControlValuesToViewModel()
    {
        ViewModel.PcName = _pcNameBox.Text;
        ViewModel.ThemeSelectionIndex = _themeBox.SelectedIndex;
        ViewModel.EnableRemoteAccess = _enableRemoteAccessSwitch.IsOn;
        ViewModel.AutoStart = _autoStartSwitch.IsOn;
        ViewModel.MinimizeToTray = _minimizeToTraySwitch.IsOn;
        ViewModel.ShowNotifications = _showNotificationsSwitch.IsOn;
        ViewModel.ServerPortText = _serverPortBox.Text;
        ViewModel.ServerPortInsecureText = _serverPortInsecureBox.Text;
        ViewModel.DiscoveryPortText = _discoveryPortBox.Text;
        ViewModel.FirewallProfileSelectionIndex = _firewallProfileBox.SelectedIndex;
        ViewModel.RequireApproval = _requireApprovalSwitch.IsOn;
        ViewModel.AuditLogging = _auditLoggingSwitch.IsOn;
        ViewModel.InputValidation = _inputValidationSwitch.IsOn;
    }

    private void RefreshControlsFromViewModel()
    {
        _serverStatusText.Text = ViewModel.ServerStatusText;
        _serverPortsText.Text = ViewModel.ServerPortsText;
        _lanIpText.Text = ViewModel.LanIpText;
        _deviceIdText.Text = ViewModel.DeviceIdPreview;
        _permissionSummaryText.Text = ViewModel.PermissionSummaryText;
        _legalStatusText.Text = GetLegalStatusText(_settingsService.Current);
        _qrPayloadText.Text = ViewModel.QrPayloadPreview;
        _pcNameBox.Text = ViewModel.PcName;
        _themeBox.SelectedIndex = ViewModel.ThemeSelectionIndex;
        _enableRemoteAccessSwitch.IsOn = ViewModel.EnableRemoteAccess;
        _autoStartSwitch.IsOn = ViewModel.AutoStart;
        _minimizeToTraySwitch.IsOn = ViewModel.MinimizeToTray;
        _showNotificationsSwitch.IsOn = ViewModel.ShowNotifications;
        _serverPortBox.Text = ViewModel.ServerPortText;
        _serverPortInsecureBox.Text = ViewModel.ServerPortInsecureText;
        _discoveryPortBox.Text = ViewModel.DiscoveryPortText;
        _firewallProfileBox.SelectedIndex = ViewModel.FirewallProfileSelectionIndex;
        _requireApprovalSwitch.IsOn = ViewModel.RequireApproval;
        _auditLoggingSwitch.IsOn = ViewModel.AuditLogging;
        _inputValidationSwitch.IsOn = ViewModel.InputValidation;
        _gamepadSupportText.Text = ViewModel.GamepadSupportText;
        _gamepadBannerCard.Visibility = ViewModel.GamepadBannerVisibility;
        _toggleServerButton.Content = ViewModel.ServerButtonText;
        _qrImage.Source = ViewModel.QrCodeImage;
        _qrPlaceholderText.Visibility = ViewModel.QrCodeImage is null ? Visibility.Visible : Visibility.Collapsed;
        RebuildClients();
        RebuildTrustedDevices();
    }

    private void RebuildClients()
    {
        _connectedDevicesPanel.Children.Clear();
        if (ViewModel.ConnectedClients.Count == 0) { _connectedDevicesPanel.Children.Add(EmptyState("No clients are currently connected.")); return; }
        foreach (var client in ViewModel.ConnectedClients) _connectedDevicesPanel.Children.Add(Row(client.DisplayName, $"{client.Summary} | {client.Status}", "Disconnect", client.ClientId, OnDisconnectClientClick));
    }

    private void RebuildTrustedDevices()
    {
        _trustedDevicesPanel.Children.Clear();
        if (ViewModel.TrustedDevices.Count == 0) { _trustedDevicesPanel.Children.Add(EmptyState("No trusted devices have been recorded yet.")); return; }
        foreach (var device in ViewModel.TrustedDevices) _trustedDevicesPanel.Children.Add(Row(device.Name, device.Summary, "Forget", device.DeviceId, OnForgetTrustedDeviceClick));
    }

    private async void OnDisconnectClientClick(object sender, RoutedEventArgs e) { if (sender is Button { Tag: string clientId }) await ViewModel.DisconnectClientAsync(clientId); }
    private async void OnForgetTrustedDeviceClick(object sender, RoutedEventArgs e) { if (sender is Button { Tag: string deviceId }) { await ViewModel.ForgetTrustedDeviceAsync(deviceId); RefreshControlsFromViewModel(); } }

    private static bool HasAcceptedCurrentLegalDocuments(AppSettings settings)
    {
        return settings.TermsOfServiceAccepted &&
               settings.TermsOfServiceVersionAccepted == AppSettings.CurrentTermsOfServiceVersion &&
               settings.TermsAndConditionsAccepted &&
               settings.TermsAndConditionsVersionAccepted == AppSettings.CurrentTermsAndConditionsVersion &&
               settings.PrivacyPolicyAccepted &&
               settings.PrivacyPolicyVersionAccepted == AppSettings.CurrentPrivacyPolicyVersion;
    }

    private static string GetLegalStatusText(AppSettings settings)
        => HasAcceptedCurrentLegalDocuments(settings)
            ? "Legal review complete for the current NexRemote release."
            : "Terms of Service, Terms and Conditions, and Privacy Policy still need current-release acceptance.";

    private static Border Row(string title, string subtitle, string actionText, string tag, RoutedEventHandler handler)
    {
        var grid = new Grid { ColumnSpacing = 12 };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        grid.Children.Add(new StackPanel { Spacing = 4, Children = { new TextBlock { Text = title, FontWeight = FontWeights.SemiBold }, MutedText(subtitle, true) } });
        var button = new Button { Content = actionText, Tag = tag, VerticalAlignment = VerticalAlignment.Center };
        button.Click += handler;
        Grid.SetColumn(button, 1);
        grid.Children.Add(button);
        return new Border { Padding = new Thickness(12), CornerRadius = new CornerRadius(14), Background = (Brush)Application.Current.Resources["CardBackgroundFillColorSecondaryBrush"], Child = grid };
    }

    private static Border EmptyState(string text) => new() { Padding = new Thickness(12), CornerRadius = new CornerRadius(12), Background = (Brush)Application.Current.Resources["CardBackgroundFillColorSecondaryBrush"], Child = MutedText(text, true) };
    private static Border Card(UIElement child) => new() { BorderBrush = (Brush)Application.Current.Resources["CardStrokeColorDefaultBrush"], BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(20), Padding = new Thickness(20), Background = (Brush)Application.Current.Resources["CardBackgroundFillColorDefaultBrush"], Child = child };
    private static Grid TwoColumnGrid() { var g = new Grid { ColumnSpacing = 20 }; g.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) }); g.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) }); return g; }
    private static Button Button(string text, RoutedEventHandler handler) { var button = new Button { Content = text }; button.Click += handler; return button; }
    private static TextBlock MutedText(string text = "", bool wrap = false) => new() { Text = text, Opacity = 0.74, TextWrapping = wrap ? TextWrapping.WrapWholeWords : TextWrapping.NoWrap };
    private static TextBlock ValueText() => new() { FontSize = 18, FontWeight = FontWeights.SemiBold };

    private ContentDialog ConsentDialog(string title, string message, string primary = "Allow", string close = "Not Now") => new()
    {
        Title = title,
        PrimaryButtonText = primary,
        CloseButtonText = close,
        DefaultButton = ContentDialogButton.Primary,
        XamlRoot = _rootGrid.XamlRoot,
        Content = new TextBlock { Text = message, TextWrapping = TextWrapping.WrapWholeWords, Width = 420 }
    };

    private static MicaBackdrop CreateMicaAltBackdrop()
    {
        var backdrop = new MicaBackdrop();
        var kindProperty = backdrop.GetType().GetProperty("Kind");
        if (kindProperty is not null && kindProperty.PropertyType.IsEnum)
        {
            try { kindProperty.SetValue(backdrop, Enum.Parse(kindProperty.PropertyType, "BaseAlt")); } catch { }
        }
        return backdrop;
    }
}
