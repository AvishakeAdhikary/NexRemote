using System;
using System.Collections.ObjectModel;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Media.Imaging;
using Windows.System;
using NexRemote.Models;
using NexRemote.Services;

namespace NexRemote.ViewModels;

public sealed class MainWindowViewModel : ObservableObject
{
    private readonly IAppSettingsService _settingsService;
    private readonly IServerCoordinator _serverCoordinator;
    private readonly ILocalNetworkService _localNetworkService;
    private readonly IQrCodeService _qrCodeService;
    private readonly ILegalDocumentService _legalDocumentService;
    private readonly ITrustedDeviceService _trustedDeviceService;
    private readonly IGamepadDriverService _gamepadDriverService;
    private BitmapImage? _qrCodeImage;
    private string _termsOfServiceText = string.Empty;
    private string _termsAndConditionsText = string.Empty;
    private string _privacyPolicyText = string.Empty;
    private string _pcName = string.Empty;
    private bool _enableRemoteAccess;
    private bool _autoStart;
    private bool _minimizeToTray;
    private bool _showNotifications;
    private bool _requireApproval;
    private bool _auditLogging;
    private bool _inputValidation;
    private string _serverPortText = ProtocolConstants.DefaultSecurePort.ToString();
    private string _serverPortInsecureText = ProtocolConstants.DefaultInsecurePort.ToString();
    private string _discoveryPortText = ProtocolConstants.DefaultDiscoveryPort.ToString();
    private int _themeSelectionIndex;
    private int _firewallProfileSelectionIndex;
    private string _serverStatusText = "Server stopped";
    private string _serverPortsText = string.Empty;
    private string _lanIpText = string.Empty;
    private string _qrPayloadPreview = string.Empty;
    private string _deviceIdPreview = string.Empty;
    private bool _gamepadDriverInstalled;
    private bool _gamepadTransportReady;

    public MainWindowViewModel(
        IAppSettingsService settingsService,
        IServerCoordinator serverCoordinator,
        ILocalNetworkService localNetworkService,
        IQrCodeService qrCodeService,
        ILegalDocumentService legalDocumentService,
        ITrustedDeviceService trustedDeviceService,
        IGamepadDriverService gamepadDriverService)
    {
        _settingsService = settingsService;
        _serverCoordinator = serverCoordinator;
        _localNetworkService = localNetworkService;
        _qrCodeService = qrCodeService;
        _legalDocumentService = legalDocumentService;
        _trustedDeviceService = trustedDeviceService;
        _gamepadDriverService = gamepadDriverService;

        ConnectedClients = new ObservableCollection<ClientConnectionViewModel>();
        TrustedDevices = new ObservableCollection<TrustedDeviceViewModel>();
    }

    public ObservableCollection<ClientConnectionViewModel> ConnectedClients { get; }

    public ObservableCollection<TrustedDeviceViewModel> TrustedDevices { get; }

    public string BrandingText => "NexRemote by Neural Nexus Studios";

    public string PermissionSummaryText
    {
        get
        {
            var network = _settingsService.Current.RemoteControlConsentGranted
                ? (_settingsService.Current.EnableRemoteAccess ? "LAN remote control is approved and enabled" : "LAN remote control is approved but disabled")
                : "LAN remote control is not approved";
            var camera = _settingsService.Current.CameraAccessConsentGranted
                ? "camera streaming is approved"
                : "camera streaming is blocked until you consent";
            return $"{network}; {camera}. Sensitive actions still require local review or Windows prompts.";
        }
    }

    public string GamepadStatusText => _gamepadDriverInstalled ? "ViGEmBus detected" : "ViGEmBus not detected";

    public string GamepadSupportText => _gamepadDriverInstalled
        ? _gamepadTransportReady
            ? "ViGEmBus and the NexRemote companion are installed. Native gamepad transport is ready."
            : "ViGEmBus is installed. Add the NexRemote gamepad companion to activate native controller transport."
        : "Install ViGEmBus to enable native virtual gamepad compatibility.";

    public Visibility GamepadBannerVisibility => _gamepadTransportReady ? Visibility.Collapsed : Visibility.Visible;

    public string ServerButtonText => IsServerRunning ? "Stop Server" : "Start Server";

    public bool IsServerRunning => _serverCoordinator.IsRunning;

    public string ServerStatusText
    {
        get => _serverStatusText;
        private set => SetProperty(ref _serverStatusText, value);
    }

    public string ServerPortsText
    {
        get => _serverPortsText;
        private set => SetProperty(ref _serverPortsText, value);
    }

    public string LanIpText
    {
        get => _lanIpText;
        private set => SetProperty(ref _lanIpText, value);
    }

    public string QrPayloadPreview
    {
        get => _qrPayloadPreview;
        private set
        {
            if (SetProperty(ref _qrPayloadPreview, value))
            {
                OnPropertyChanged(nameof(QrPlaceholderVisibility));
            }
        }
    }

    public string DeviceIdPreview
    {
        get => _deviceIdPreview;
        private set => SetProperty(ref _deviceIdPreview, value);
    }

    public BitmapImage? QrCodeImage
    {
        get => _qrCodeImage;
        private set
        {
            if (SetProperty(ref _qrCodeImage, value))
            {
                OnPropertyChanged(nameof(QrPlaceholderVisibility));
            }
        }
    }

    public Visibility QrPlaceholderVisibility => QrCodeImage is null ? Visibility.Visible : Visibility.Collapsed;

    public string TermsOfServiceText
    {
        get => _termsOfServiceText;
        private set => SetProperty(ref _termsOfServiceText, value);
    }

    public string TermsAndConditionsText
    {
        get => _termsAndConditionsText;
        private set => SetProperty(ref _termsAndConditionsText, value);
    }

    public string PrivacyPolicyText
    {
        get => _privacyPolicyText;
        private set => SetProperty(ref _privacyPolicyText, value);
    }

    public string PcName
    {
        get => _pcName;
        set => SetProperty(ref _pcName, value);
    }

    public bool AutoStart
    {
        get => _autoStart;
        set => SetProperty(ref _autoStart, value);
    }

    public bool EnableRemoteAccess
    {
        get => _enableRemoteAccess;
        set => SetProperty(ref _enableRemoteAccess, value);
    }

    public bool MinimizeToTray
    {
        get => _minimizeToTray;
        set => SetProperty(ref _minimizeToTray, value);
    }

    public bool ShowNotifications
    {
        get => _showNotifications;
        set => SetProperty(ref _showNotifications, value);
    }

    public bool RequireApproval
    {
        get => _requireApproval;
        set => SetProperty(ref _requireApproval, value);
    }

    public bool AuditLogging
    {
        get => _auditLogging;
        set => SetProperty(ref _auditLogging, value);
    }

    public bool InputValidation
    {
        get => _inputValidation;
        set => SetProperty(ref _inputValidation, value);
    }

    public string ServerPortText
    {
        get => _serverPortText;
        set => SetProperty(ref _serverPortText, value);
    }

    public string ServerPortInsecureText
    {
        get => _serverPortInsecureText;
        set => SetProperty(ref _serverPortInsecureText, value);
    }

    public string DiscoveryPortText
    {
        get => _discoveryPortText;
        set => SetProperty(ref _discoveryPortText, value);
    }

    public int ThemeSelectionIndex
    {
        get => _themeSelectionIndex;
        set => SetProperty(ref _themeSelectionIndex, value);
    }

    public int FirewallProfileSelectionIndex
    {
        get => _firewallProfileSelectionIndex;
        set => SetProperty(ref _firewallProfileSelectionIndex, value);
    }

    public ThemePreference SelectedThemePreference => ThemeSelectionIndex switch
    {
        1 => ThemePreference.Light,
        2 => ThemePreference.Dark,
        _ => ThemePreference.System
    };

    public async Task InitializeAsync()
    {
        var settings = _settingsService.Current;
        PcName = settings.PcName;
        EnableRemoteAccess = settings.EnableRemoteAccess;
        AutoStart = settings.AutoStart;
        MinimizeToTray = settings.MinimizeToTray;
        ShowNotifications = settings.ShowNotifications;
        RequireApproval = settings.RequireApproval;
        AuditLogging = settings.AuditLogging;
        InputValidation = settings.InputValidation;
        ServerPortText = settings.ServerPort.ToString();
        ServerPortInsecureText = settings.ServerPortInsecure.ToString();
        DiscoveryPortText = settings.DiscoveryPort.ToString();
        ThemeSelectionIndex = settings.ThemePreference switch
        {
            ThemePreference.Light => 1,
            ThemePreference.Dark => 2,
            _ => 0
        };
        FirewallProfileSelectionIndex = settings.FirewallProfile switch
        {
            "public" => 1,
            "all" => 2,
            _ => 0
        };

        var termsTask = _legalDocumentService.LoadTermsOfServiceAsync();
        var conditionsTask = _legalDocumentService.LoadTermsAndConditionsAsync();
        var privacyTask = _legalDocumentService.LoadPrivacyPolicyAsync();
        var gamepadTask = _gamepadDriverService.IsViGEmBusInstalledAsync();
        var gamepadTransportTask = _gamepadDriverService.IsNativeTransportReadyAsync();

        await Task.WhenAll(termsTask, conditionsTask, privacyTask, gamepadTask, gamepadTransportTask);
        TermsOfServiceText = termsTask.Result;
        TermsAndConditionsText = conditionsTask.Result;
        PrivacyPolicyText = privacyTask.Result;
        _gamepadDriverInstalled = gamepadTask.Result;
        _gamepadTransportReady = gamepadTransportTask.Result;
        _serverCoordinator.RefreshCapabilities();

        var lanIp = _localNetworkService.GetLanIpAddress();
        LanIpText = $"LAN IP: {lanIp}";
        DeviceIdPreview = $"Device ID: {settings.DeviceId}";
        ServerPortsText = $"Ports: {settings.ServerPort} secure / {settings.ServerPortInsecure} fallback / {settings.DiscoveryPort} discovery";
        ServerStatusText = _serverCoordinator.IsRunning ? "Server running" : "Server stopped";

        var qrPayload = _serverCoordinator.CreateQrPayload(lanIp);
        var qrJson = JsonSerializer.Serialize(qrPayload, ProtocolJson.SharedOptions);
        QrPayloadPreview = qrJson;
        QrCodeImage = await _qrCodeService.CreateAsync(qrJson);

        RefreshTrustedDevices();
        OnPropertyChanged(nameof(ServerButtonText));
        OnPropertyChanged(nameof(IsServerRunning));
        OnPropertyChanged(nameof(PermissionSummaryText));
        OnPropertyChanged(nameof(GamepadStatusText));
        OnPropertyChanged(nameof(GamepadSupportText));
        OnPropertyChanged(nameof(GamepadBannerVisibility));
    }

    public async Task ToggleServerAsync()
    {
        if (_serverCoordinator.IsRunning)
        {
            await _serverCoordinator.StopAsync();
        }
        else
        {
            if (!_settingsService.Current.RemoteControlConsentGranted)
            {
                return;
            }

            _serverCoordinator.RefreshCapabilities();
            await _serverCoordinator.StartAsync();
        }

        await InitializeAsync();
    }

    public async Task SaveAsync()
    {
        _settingsService.Update(settings =>
        {
            settings.PcName = PcName.Trim();
            settings.EnableRemoteAccess = EnableRemoteAccess;
            settings.AutoStart = AutoStart;
            settings.MinimizeToTray = MinimizeToTray;
            settings.ShowNotifications = ShowNotifications;
            settings.RequireApproval = RequireApproval;
            settings.AuditLogging = AuditLogging;
            settings.InputValidation = InputValidation;
            settings.ThemePreference = SelectedThemePreference;
            settings.FirewallProfile = FirewallProfileSelectionIndex switch
            {
                1 => "public",
                2 => "all",
                _ => "private"
            };
            settings.ServerPort = ParsePort(ServerPortText, settings.ServerPort);
            settings.ServerPortInsecure = ParsePort(ServerPortInsecureText, settings.ServerPortInsecure);
            settings.DiscoveryPort = ParsePort(DiscoveryPortText, settings.DiscoveryPort);
        });

        await _settingsService.SaveAsync();
        await InitializeAsync();
    }

    public async Task OpenSupportAsync()
    {
        await Launcher.LaunchUriAsync(new Uri("https://buymeacoffee.com/avishake69"));
    }

    public async Task OpenViGemGuideAsync()
    {
        await Launcher.LaunchUriAsync(new Uri("https://vigem.org/projects/ViGEm/How-to-Install/"));
    }

    public async Task ForgetTrustedDeviceAsync(string deviceId)
    {
        if (string.IsNullOrWhiteSpace(deviceId))
        {
            return;
        }

        _trustedDeviceService.Remove(deviceId);
        await _trustedDeviceService.SaveAsync();
        RefreshTrustedDevices();
    }

    public async Task DisconnectClientAsync(string clientId)
    {
        await _serverCoordinator.DisconnectClientAsync(clientId);
    }

    public void RefreshTrustedDevices()
    {
        TrustedDevices.Clear();
        foreach (var pair in _trustedDeviceService.Devices)
        {
            TrustedDevices.Add(new TrustedDeviceViewModel
            {
                DeviceId = pair.Key,
                Name = pair.Value.Name,
                Summary = $"ID: {pair.Key} | First: {pair.Value.FirstConnected.LocalDateTime:g} | Last: {pair.Value.LastConnected.LocalDateTime:g}"
            });
        }
    }

    public void UpsertConnectedClient(string clientId, string deviceName, string status)
    {
        for (var index = 0; index < ConnectedClients.Count; index++)
        {
            if (string.Equals(ConnectedClients[index].ClientId, clientId, StringComparison.OrdinalIgnoreCase))
            {
                ConnectedClients[index] = new ClientConnectionViewModel
                {
                    ClientId = clientId,
                    DisplayName = deviceName,
                    Summary = $"ID: {clientId}",
                    Status = status
                };
                return;
            }
        }

        ConnectedClients.Add(new ClientConnectionViewModel
        {
            ClientId = clientId,
            DisplayName = deviceName,
            Summary = $"ID: {clientId}",
            Status = status
        });
    }

    public void RemoveConnectedClient(string clientId)
    {
        for (var index = ConnectedClients.Count - 1; index >= 0; index--)
        {
            if (string.Equals(ConnectedClients[index].ClientId, clientId, StringComparison.OrdinalIgnoreCase))
            {
                ConnectedClients.RemoveAt(index);
            }
        }
    }

    private static int ParsePort(string text, int fallback)
    {
        return int.TryParse(text, out var value) && value is >= 1024 and <= 65535 ? value : fallback;
    }
}
