using System;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using NexRemote.Services;
using NexRemote.ViewModels;

namespace NexRemote.Bootstrap;

public static class AppBootstrapper
{
    public static IHost Build()
    {
        return Host.CreateDefaultBuilder()
            .ConfigureServices(services =>
            {
                services.AddSingleton<IAppSettingsService, AppSettingsService>();
                services.AddSingleton<ITrustedDeviceService, TrustedDeviceService>();
                services.AddSingleton<IMessageEncryptionService, MessageEncryptionService>();
                services.AddSingleton<IAuthenticationService, AuthenticationService>();
                services.AddSingleton<ICertificateService, CertificateService>();
                services.AddSingleton<IConnectionApprovalService, ConnectionApprovalService>();
                services.AddSingleton<IGamepadDriverService, GamepadDriverService>();
                services.AddSingleton<IDiscoveryModelFactory, DiscoveryModelFactory>();
                services.AddSingleton<IDiscoveryService, DiscoveryService>();
                services.AddSingleton<IServerCapabilitiesFactory, ServerCapabilitiesFactory>();
                services.AddSingleton<IRemoteServer, RemoteServerHost>();
                services.AddSingleton<IThemeService, ThemeService>();
                services.AddSingleton<ILocalNetworkService, LocalNetworkService>();
                services.AddSingleton<IQrCodeService, QrCodeService>();
                services.AddSingleton<ILegalDocumentService, LegalDocumentService>();
                services.AddSingleton<ICameraPermissionService, CameraPermissionService>();
                services.AddSingleton<ITrayIconService, TrayIconService>();
                services.AddSingleton<MainWindowViewModel>();
            })
            .Build();
    }

    public static async Task InitializeAsync(IServiceProvider services)
    {
        var settings = services.GetRequiredService<IAppSettingsService>();
        await settings.InitializeAsync();

        var trustedDevices = services.GetRequiredService<ITrustedDeviceService>();
        await trustedDevices.InitializeAsync();

        var certificates = services.GetRequiredService<ICertificateService>();
        await certificates.EnsureCertificateAsync();
        var thumbprint = await certificates.GetThumbprintAsync();
        if (!string.IsNullOrWhiteSpace(thumbprint))
        {
            settings.Update(current => current.CertificateThumbprint = thumbprint);
            await settings.SaveAsync();
        }
    }
}
