using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.UI;
using Microsoft.UI.Text;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Muxc = Microsoft.UI.Xaml.Controls;
using Windows.Graphics;
using Windows.System;
using NexRemote.Models;
using NexRemote.Services;
using NexRemote.ViewModels;
using Serilog;
using WinRT.Interop;

namespace NexRemote;

public sealed partial class MainWindow : Window
{
    private const int MinimumWindowWidth = 800;
    private const int MinimumWindowHeight = 600;

    private readonly IAppSettingsService _settingsService;
    private readonly IThemeService _themeService;
    private readonly ITrayIconService _trayIconService;
    private readonly IServerCoordinator _serverCoordinator;
    private readonly IConnectionApprovalService _approvalService;
    private readonly ICameraPermissionService _cameraPermissionService;
    private readonly IGamepadDriverService _gamepadDriverService;
    private readonly IGamepadTransportService _gamepadTransportService;
    private readonly IAdbBridgeService _adbBridgeService;
    private readonly AppWindow _appWindow;
    private readonly List<Window> _secondaryWindows = new();

    private bool _allowClose;
    private bool _customTitleBarEnabled;
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
        _gamepadDriverService = services.GetRequiredService<IGamepadDriverService>();
        _gamepadTransportService = services.GetRequiredService<IGamepadTransportService>();
        _adbBridgeService = services.GetRequiredService<IAdbBridgeService>();
        ViewModel = services.GetRequiredService<MainWindowViewModel>();

        InitializeComponent();
        Title = "NexRemote";
        SystemBackdrop = CreateMicaAltBackdrop();

        ThemeBox.Items.Add(new ComboBoxItem { Content = "System" });
        ThemeBox.Items.Add(new ComboBoxItem { Content = "Light" });
        ThemeBox.Items.Add(new ComboBoxItem { Content = "Dark" });
        FirewallProfileBox.Items.Add(new ComboBoxItem { Content = "Private only" });
        FirewallProfileBox.Items.Add(new ComboBoxItem { Content = "Public only" });
        FirewallProfileBox.Items.Add(new ComboBoxItem { Content = "All profiles" });

        RootGrid.ActualThemeChanged += OnRootGridActualThemeChanged;
        RootGrid.Loaded += OnLoaded;
        Closed += OnClosed;

        var hWnd = WindowNative.GetWindowHandle(this);
        _appWindow = AppWindow.GetFromWindowId(Microsoft.UI.Win32Interop.GetWindowIdFromWindow(hWnd));
        _appWindow.Closing += OnAppWindowClosing;
        ConfigureWindowChrome();
    }

    public MainWindowViewModel ViewModel { get; }

    public void RestoreFromActivation()
    {
        _appWindow.Show();
        Activate();
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (_initialized)
        {
            return;
        }

        _initialized = true;
        LogStartup("MainWindow loaded.");
        _themeService.ApplyTheme(this, _settingsService.Current.ThemePreference);
        UpdateTitleBarColors();
        await ViewModel.InitializeAsync();
        LogStartup("ViewModel initialized.");
        RefreshControlsFromViewModel();
        SwitchPage("dashboard");
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
        if (HasAcceptedCurrentLegalDocuments(_settingsService.Current))
        {
            return;
        }

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
            XamlRoot = RootGrid.XamlRoot
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
                new TextBlock
                {
                    Text = "Review the legal documents in their dedicated reader windows before using NexRemote for the first time.",
                    TextWrapping = TextWrapping.WrapWholeWords,
                    Width = 420
                },
                new StackPanel
                {
                    Orientation = Orientation.Horizontal,
                    Spacing = 12,
                    Children =
                    {
                        DialogButton("View Terms of Service", () =>
                        {
                            tosViewed = true;
                            tosCheck.IsEnabled = true;
                            UpdateState();
                            OpenLegalDocumentWindow("Terms of Service", ViewModel.TermsOfServiceText);
                        }),
                        DialogButton("View Terms and Conditions", () =>
                        {
                            conditionsViewed = true;
                            conditionsCheck.IsEnabled = true;
                            UpdateState();
                            OpenLegalDocumentWindow("Terms and Conditions", ViewModel.TermsAndConditionsText);
                        }),
                        DialogButton("View Privacy Policy", () =>
                        {
                            privacyViewed = true;
                            privacyCheck.IsEnabled = true;
                            UpdateState();
                            OpenLegalDocumentWindow("Privacy Policy", ViewModel.PrivacyPolicyText);
                        })
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
        if (_settingsService.Current.RemoteControlConsentGranted && !forcePrompt)
        {
            return;
        }

        var dialog = ConsentDialog(
            "Allow Remote Networking",
            "When enabled, NexRemote can listen on your local network, receive approved client requests, and exchange remote control messages on your configured ports.");
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
        if (_settingsService.Current.CameraAccessConsentGranted && !forcePrompt)
        {
            return;
        }

        var cameraState = await _cameraPermissionService.GetAccessStateAsync();
        if (cameraState is CameraAccessState.DeniedBySystem or CameraAccessState.DeniedByUser)
        {
            await _cameraPermissionService.OpenPrivacySettingsAsync();
        }

        var dialog = ConsentDialog(
            "Allow Camera Streaming",
            "Camera streaming can expose video from cameras attached to this PC. Allow this only if you want approved clients to request camera enumeration and streaming.");
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

    private void OnNavigationSelectionChanged(Muxc.NavigationView sender, Muxc.NavigationViewSelectionChangedEventArgs args)
    {
        if (args.IsSettingsSelected)
        {
            SwitchPage("settings");
            return;
        }

        if (args.SelectedItem is Muxc.NavigationViewItem item && item.Tag is string tag)
        {
            SwitchPage(tag);
        }
    }

    private void SwitchPage(string tag)
    {
        DashboardPanel.Visibility = tag == "dashboard" ? Visibility.Visible : Visibility.Collapsed;
        DevicesPanelRoot.Visibility = tag == "devices" ? Visibility.Visible : Visibility.Collapsed;
        CompatibilityPanelRoot.Visibility = tag == "compatibility" ? Visibility.Visible : Visibility.Collapsed;
        SettingsPanelRoot.Visibility = tag == "settings" ? Visibility.Visible : Visibility.Collapsed;
        LegalPanelRoot.Visibility = tag == "legal" ? Visibility.Visible : Visibility.Collapsed;
        SupportPanelRoot.Visibility = tag == "support" ? Visibility.Visible : Visibility.Collapsed;

        NavigationHeaderText.Text = tag switch
        {
            "devices" => "Devices",
            "compatibility" => "Compatibility",
            "settings" => "Settings",
            "legal" => "Legal",
            "support" => "Support Me",
            _ => "Dashboard"
        };
    }

    private async void OnToggleServerClick(object sender, RoutedEventArgs e)
    {
        await ViewModel.ToggleServerAsync();
        RefreshControlsFromViewModel();
        _trayIconService.UpdateServerState(ViewModel.IsServerRunning, ViewModel.ServerStatusText);
    }

    private async void OnSaveSettingsClick(object sender, RoutedEventArgs e)
    {
        ApplyControlValuesToViewModel();
        await ViewModel.SaveAsync();
        RefreshControlsFromViewModel();
        _themeService.ApplyTheme(this, ViewModel.SelectedThemePreference);
        UpdateTitleBarColors();
        await StartServerIfNeededAsync();
        _trayIconService.ShowMessage("NexRemote", "Settings saved locally.");
    }

    private async void OnReviewPermissionsClick(object sender, RoutedEventArgs e)
    {
        await EnsureServerConsentAsync(true);
        RefreshControlsFromViewModel();
    }

    private async void OnReviewCameraPermissionClick(object sender, RoutedEventArgs e)
    {
        await EnsureCameraConsentAsync(true);
        RefreshControlsFromViewModel();
    }

    private void OnThemeSelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        ViewModel.ThemeSelectionIndex = ThemeBox.SelectedIndex;
        _themeService.ApplyTheme(this, ViewModel.SelectedThemePreference);
        UpdateTitleBarColors();
    }

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

    private async void OnTrayToggleServerRequested(object? sender, EventArgs e)
    {
        await ViewModel.ToggleServerAsync();
        RefreshControlsFromViewModel();
        _trayIconService.UpdateServerState(ViewModel.IsServerRunning, ViewModel.ServerStatusText);
    }

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
            if (!_settingsService.Current.BackgroundConsentGranted)
            {
                _ = AskForBackgroundConsentAndHideAsync();
                return;
            }

            sender.Hide();
            _trayIconService.ShowMessage("NexRemote", "NexRemote is still available in the system tray.");
            return;
        }

        _ = RequestExitAsync();
    }

    private async Task AskForBackgroundConsentAndHideAsync()
    {
        var dialog = ConsentDialog(
            "Keep NexRemote In The Tray?",
            "NexRemote can stay available from the system tray so the server and approval prompts remain reachable in the background.",
            primary: "Keep Running",
            close: "Close App");
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
        if (_cleanupComplete)
        {
            return;
        }

        _cleanupComplete = true;
        RootGrid.Loaded -= OnLoaded;
        RootGrid.ActualThemeChanged -= OnRootGridActualThemeChanged;
        Closed -= OnClosed;
        _appWindow.Closing -= OnAppWindowClosing;
        _trayIconService.ShowRequested -= OnTrayShowRequested;
        _trayIconService.ToggleServerRequested -= OnTrayToggleServerRequested;
        _trayIconService.ExitRequested -= OnTrayExitRequested;
        _serverCoordinator.ClientConnected -= OnRemoteServerClientConnected;
        _serverCoordinator.ClientDisconnected -= OnRemoteServerClientDisconnected;
        _approvalService.ApprovalRequested -= OnApprovalRequested;
        _trayIconService.Dispose();
        foreach (var window in _secondaryWindows.ToArray())
        {
            try
            {
                window.Close();
            }
            catch
            {
                // ignored
            }
        }
        _secondaryWindows.Clear();
    }

    private void OnApprovalRequested(object? sender, PendingApprovalRequestEventArgs e)
        => DispatcherQueue.TryEnqueue(() => _ = ShowApprovalDialogAsync(e.DeviceId, e.DeviceName));

    private async Task ShowApprovalDialogAsync(string deviceId, string deviceName)
    {
        RestoreFromActivation();
        var dialog = new ContentDialog
        {
            Title = "New Connection Request",
            PrimaryButtonText = "Approve",
            CloseButtonText = "Reject",
            DefaultButton = ContentDialogButton.Primary,
            XamlRoot = RootGrid.XamlRoot,
            Content = new TextBlock
            {
                Text = $"Approve this connection only if you recognize the device.\n\nDevice Name: {deviceName}\nDevice ID: {deviceId}\n\nThis request auto-rejects after {ProtocolConstants.ApprovalTimeoutSeconds} seconds so the mobile client can fail fast instead of hanging.",
                TextWrapping = TextWrapping.WrapWholeWords,
                Width = 420
            }
        };
        var dialogTask = dialog.ShowAsync().AsTask();
        var completed = await Task.WhenAny(dialogTask, Task.Delay(TimeSpan.FromSeconds(ProtocolConstants.ApprovalTimeoutSeconds)));
        if (completed == dialogTask)
        {
            _approvalService.CompleteApproval(deviceId, await dialogTask == ContentDialogResult.Primary);
            return;
        }

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

    private void OnRemoteServerClientConnected(object? sender, ClientConnectionEventArgs e)
        => DispatcherQueue.TryEnqueue(() =>
        {
            ViewModel.UpsertConnectedClient(e.ClientId, e.DeviceName, "Connected");
            ViewModel.RefreshTrustedDevices();
            RefreshControlsFromViewModel();
        });

    private void OnRemoteServerClientDisconnected(object? sender, ClientConnectionEventArgs e)
        => DispatcherQueue.TryEnqueue(() =>
        {
            ViewModel.RemoveConnectedClient(e.ClientId);
            RefreshControlsFromViewModel();
        });

    private void ApplyControlValuesToViewModel()
    {
        ViewModel.PcName = PcNameBox.Text;
        ViewModel.ThemeSelectionIndex = ThemeBox.SelectedIndex;
        ViewModel.EnableRemoteAccess = EnableRemoteAccessSwitch.IsOn;
        ViewModel.AutoStart = AutoStartSwitch.IsOn;
        ViewModel.MinimizeToTray = MinimizeToTraySwitch.IsOn;
        ViewModel.ShowNotifications = ShowNotificationsSwitch.IsOn;
        ViewModel.ServerPortText = ServerPortBox.Text;
        ViewModel.ServerPortInsecureText = ServerPortInsecureBox.Text;
        ViewModel.DiscoveryPortText = DiscoveryPortBox.Text;
        ViewModel.FirewallProfileSelectionIndex = FirewallProfileBox.SelectedIndex;
        ViewModel.RequireApproval = RequireApprovalSwitch.IsOn;
        ViewModel.AuditLogging = AuditLoggingSwitch.IsOn;
        ViewModel.InputValidation = InputValidationSwitch.IsOn;
    }

    private void RefreshControlsFromViewModel()
    {
        ServerStatusTextBlock.Text = ViewModel.ServerStatusText;
        ServerPortsTextBlock.Text = ViewModel.ServerPortsText;
        LanIpTextBlock.Text = ViewModel.LanIpText;
        DeviceIdTextBlock.Text = ViewModel.DeviceIdPreview;
        PermissionSummaryTextBlock.Text = ViewModel.PermissionSummaryText;
        LegalStatusTextBlock.Text = GetLegalStatusText(_settingsService.Current);
        QrPayloadTextBlock.Text = ViewModel.QrPayloadPreview;
        PcNameBox.Text = ViewModel.PcName;
        ThemeBox.SelectedIndex = ViewModel.ThemeSelectionIndex;
        EnableRemoteAccessSwitch.IsOn = ViewModel.EnableRemoteAccess;
        AutoStartSwitch.IsOn = ViewModel.AutoStart;
        MinimizeToTraySwitch.IsOn = ViewModel.MinimizeToTray;
        ShowNotificationsSwitch.IsOn = ViewModel.ShowNotifications;
        ServerPortBox.Text = ViewModel.ServerPortText;
        ServerPortInsecureBox.Text = ViewModel.ServerPortInsecureText;
        DiscoveryPortBox.Text = ViewModel.DiscoveryPortText;
        FirewallProfileBox.SelectedIndex = ViewModel.FirewallProfileSelectionIndex;
        RequireApprovalSwitch.IsOn = ViewModel.RequireApproval;
        AuditLoggingSwitch.IsOn = ViewModel.AuditLogging;
        InputValidationSwitch.IsOn = ViewModel.InputValidation;
        ToggleServerButton.Content = ViewModel.ServerButtonText;
        QrImage.Source = ViewModel.QrCodeImage;
        QrPlaceholderText.Visibility = ViewModel.QrCodeImage is null ? Visibility.Visible : Visibility.Collapsed;
        RebuildClients();
        RebuildTrustedDevices();
        RebuildCompatibility();
    }

    private void RebuildClients()
    {
        ConnectedDevicesPanel.Children.Clear();
        if (ViewModel.ConnectedClients.Count == 0)
        {
            ConnectedDevicesPanel.Children.Add(EmptyState("No clients are currently connected."));
            return;
        }

        foreach (var client in ViewModel.ConnectedClients)
        {
            ConnectedDevicesPanel.Children.Add(CreateActionRow(client.DisplayName, $"{client.Summary} | {client.Status}", "Disconnect", client.ClientId, OnDisconnectClientClick));
        }
    }

    private void RebuildTrustedDevices()
    {
        TrustedDevicesPanel.Children.Clear();
        if (ViewModel.TrustedDevices.Count == 0)
        {
            TrustedDevicesPanel.Children.Add(EmptyState("No trusted devices have been recorded yet."));
            return;
        }

        foreach (var device in ViewModel.TrustedDevices)
        {
            TrustedDevicesPanel.Children.Add(CreateActionRow(device.Name, device.Summary, "Forget", device.DeviceId, OnForgetTrustedDeviceClick));
        }
    }

    private void RebuildCompatibility()
    {
        CompatibilityStatusPanel.Children.Clear();
        var adbStatus = _adbBridgeService.CurrentStatus;
        var gamepadDriverInstalled = _gamepadDriverService.IsViGEmBusInstalled();
        var gamepadBackendReady = gamepadDriverInstalled && _gamepadTransportService.IsReady;

        CompatibilityStatusPanel.Children.Add(CreateCompatibilityRow("Server Running", ViewModel.IsServerRunning, ViewModel.ServerStatusText));
        CompatibilityStatusPanel.Children.Add(CreateCompatibilityRow("Certificate Ready", !string.IsNullOrWhiteSpace(_settingsService.Current.CertificateFingerprint), string.IsNullOrWhiteSpace(_settingsService.Current.CertificateFingerprint) ? "The secure certificate is still missing." : "Secure certificate fingerprint is available for pairing."));
        CompatibilityStatusPanel.Children.Add(CreateCompatibilityRow("Remote Access Consent", _settingsService.Current.RemoteControlConsentGranted && _settingsService.Current.EnableRemoteAccess, _settingsService.Current.RemoteControlConsentGranted ? "LAN access is approved." : "LAN access still requires local approval."));
        CompatibilityStatusPanel.Children.Add(CreateCompatibilityRow("Camera Permission", _settingsService.Current.CameraAccessConsentGranted, _settingsService.Current.CameraAccessConsentGranted ? "Camera streaming permission is granted." : "Camera streaming needs local consent."));
        CompatibilityStatusPanel.Children.Add(CreateCompatibilityRow("ViGEmBus", gamepadDriverInstalled, gamepadDriverInstalled ? "Virtual gamepad driver detected." : "Install ViGEmBus to enable native controller transport."));
        CompatibilityStatusPanel.Children.Add(CreateCompatibilityRow("Gamepad Backend", gamepadBackendReady, ViewModel.GamepadSupportText));
        CompatibilityStatusPanel.Children.Add(CreateCompatibilityRow("ADB Bridge", adbStatus.ToolAvailable, adbStatus.Reason));
        CompatibilityStatusPanel.Children.Add(CreateCompatibilityRow("ADB Reverse", adbStatus.ReverseActive, adbStatus.Reason));
        CompatibilityViGemGuideButton.Visibility = gamepadBackendReady ? Visibility.Collapsed : Visibility.Visible;
    }

    private async void OnDisconnectClientClick(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string clientId })
        {
            await ViewModel.DisconnectClientAsync(clientId);
        }
    }

    private async void OnForgetTrustedDeviceClick(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string deviceId })
        {
            await ViewModel.ForgetTrustedDeviceAsync(deviceId);
            RefreshControlsFromViewModel();
        }
    }

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
            ? "Legal review is complete for the current NexRemote release."
            : "Terms of Service, Terms and Conditions, and Privacy Policy still need current-release acceptance.";

    private static Button DialogButton(string text, Action action)
    {
        var button = new Button { Content = text };
        button.Click += (_, _) => action();
        return button;
    }

    private static FrameworkElement CreateActionRow(string title, string subtitle, string actionText, string tag, RoutedEventHandler handler)
    {
        var grid = new Grid { ColumnSpacing = 12 };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        grid.Children.Add(new StackPanel
        {
            Spacing = 4,
            Children =
            {
                new TextBlock { Text = title, FontWeight = FontWeights.SemiBold },
                new TextBlock { Text = subtitle, Style = (Style)Application.Current.Resources["MutedBodyTextStyle"], TextWrapping = TextWrapping.WrapWholeWords }
            }
        });
        var button = new Button { Content = actionText, Tag = tag, VerticalAlignment = VerticalAlignment.Center };
        button.Click += handler;
        Grid.SetColumn(button, 1);
        grid.Children.Add(button);
        return new Border
        {
            Padding = new Thickness(12),
            CornerRadius = new CornerRadius(14),
            Background = (Brush)Application.Current.Resources["CardBackgroundFillColorSecondaryBrush"],
            Child = grid
        };
    }

    private static FrameworkElement CreateCompatibilityRow(string title, bool ready, string message)
    {
        var grid = new Grid { ColumnSpacing = 12 };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

        var icon = new TextBlock
        {
            Text = ready ? "\u2713" : "\u2717",
            FontSize = 18,
            FontWeight = FontWeights.Bold,
            VerticalAlignment = VerticalAlignment.Top,
            Foreground = (Brush)Application.Current.Resources[ready ? "StatusOkForegroundBrush" : "StatusWarningForegroundBrush"]
        };
        grid.Children.Add(icon);

        var content = new StackPanel
        {
            Spacing = 4,
            Children =
            {
                new TextBlock { Text = title, FontWeight = FontWeights.SemiBold },
                new TextBlock { Text = message, Style = (Style)Application.Current.Resources["MutedBodyTextStyle"], TextWrapping = TextWrapping.WrapWholeWords }
            }
        };
        Grid.SetColumn(content, 1);
        grid.Children.Add(content);

        return new Border
        {
            Padding = new Thickness(14),
            CornerRadius = new CornerRadius(16),
            Background = (Brush)Application.Current.Resources[ready ? "StatusOkBrush" : "StatusWarningBrush"],
            Child = grid
        };
    }

    private static FrameworkElement EmptyState(string text)
        => new Border
        {
            Padding = new Thickness(14),
            CornerRadius = new CornerRadius(14),
            Background = (Brush)Application.Current.Resources["CardBackgroundFillColorSecondaryBrush"],
            Child = new TextBlock
            {
                Text = text,
                Style = (Style)Application.Current.Resources["MutedBodyTextStyle"],
                TextWrapping = TextWrapping.WrapWholeWords
            }
        };

    private ContentDialog ConsentDialog(string title, string message, string primary = "Allow", string close = "Not Now")
        => new()
        {
            Title = title,
            PrimaryButtonText = primary,
            CloseButtonText = close,
            DefaultButton = ContentDialogButton.Primary,
            XamlRoot = RootGrid.XamlRoot,
            Content = new TextBlock { Text = message, TextWrapping = TextWrapping.WrapWholeWords, Width = 420 }
        };

    private void ConfigureWindowChrome()
    {
        if (_appWindow.Presenter is OverlappedPresenter presenter)
        {
            presenter.PreferredMinimumWidth = MinimumWindowWidth;
            presenter.PreferredMinimumHeight = MinimumWindowHeight;
        }

        if (!AppWindowTitleBar.IsCustomizationSupported())
        {
            TitleBarHost.Visibility = Visibility.Collapsed;
            return;
        }

        _customTitleBarEnabled = true;
        TitleBarHost.Visibility = Visibility.Visible;
        ExtendsContentIntoTitleBar = true;
        SetTitleBar(AppTitleBar);

        var titleBar = _appWindow.TitleBar;
        titleBar.PreferredHeightOption = TitleBarHeightOption.Tall;
        UpdateTitleBarColors();
    }

    private void OnRootGridActualThemeChanged(FrameworkElement sender, object args)
    {
        UpdateTitleBarColors();
    }

    private void UpdateTitleBarColors()
    {
        if (!_customTitleBarEnabled)
        {
            return;
        }

        var darkTheme = RootGrid.ActualTheme == ElementTheme.Dark ||
                        (RootGrid.ActualTheme == ElementTheme.Default && Application.Current.RequestedTheme == ApplicationTheme.Dark);

        var foreground = darkTheme ? Colors.White : ColorHelper.FromArgb(0xFF, 0x1F, 0x23, 0x28);
        var mutedForeground = darkTheme ? ColorHelper.FromArgb(0xCC, 0xFF, 0xFF, 0xFF) : ColorHelper.FromArgb(0xCC, 0x38, 0x3A, 0x40);
        var hoverBackground = darkTheme ? ColorHelper.FromArgb(0x20, 0xFF, 0xFF, 0xFF) : ColorHelper.FromArgb(0x12, 0x00, 0x00, 0x00);
        var pressedBackground = darkTheme ? ColorHelper.FromArgb(0x30, 0xFF, 0xFF, 0xFF) : ColorHelper.FromArgb(0x1E, 0x00, 0x00, 0x00);

        var titleBar = _appWindow.TitleBar;
        titleBar.BackgroundColor = Colors.Transparent;
        titleBar.ForegroundColor = foreground;
        titleBar.InactiveBackgroundColor = Colors.Transparent;
        titleBar.InactiveForegroundColor = mutedForeground;
        titleBar.ButtonBackgroundColor = Colors.Transparent;
        titleBar.ButtonForegroundColor = foreground;
        titleBar.ButtonHoverBackgroundColor = hoverBackground;
        titleBar.ButtonHoverForegroundColor = foreground;
        titleBar.ButtonPressedBackgroundColor = pressedBackground;
        titleBar.ButtonPressedForegroundColor = foreground;
        titleBar.ButtonInactiveBackgroundColor = Colors.Transparent;
        titleBar.ButtonInactiveForegroundColor = mutedForeground;
    }

    private static MicaBackdrop CreateMicaAltBackdrop()
    {
        var backdrop = new MicaBackdrop();
        var kindProperty = backdrop.GetType().GetProperty("Kind");
        if (kindProperty is not null && kindProperty.PropertyType.IsEnum)
        {
            try
            {
                kindProperty.SetValue(backdrop, Enum.Parse(kindProperty.PropertyType, "BaseAlt"));
            }
            catch
            {
                // ignored
            }
        }

        return backdrop;
    }
}

internal static class FrameworkElementExtensions
{
    public static T Also<T>(this T value, Action<T> configure)
    {
        configure(value);
        return value;
    }
}
