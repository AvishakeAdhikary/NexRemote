using System;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using NexRemote.Helpers;
using NexRemote.Models;

namespace NexRemote.Services;

public interface IAppSettingsService
{
    AppSettings Current { get; }
    Task InitializeAsync(CancellationToken cancellationToken = default);
    Task SaveAsync(CancellationToken cancellationToken = default);
    void Update(Action<AppSettings> updater);
}

public sealed class AppSettingsService : IAppSettingsService
{
    private readonly string _filePath = PathHelper.GetSettingsPath();
    private readonly SemaphoreSlim _gate = new(1, 1);

    public AppSettings Current { get; private set; } = AppSettings.CreateDefault();

    public AppSettingsService()
    {
    }

    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            Current = await LoadOrCreateAsync(cancellationToken).ConfigureAwait(false);
            await SaveCoreAsync(cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _gate.Release();
        }
    }

    public async Task SaveAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            await SaveCoreAsync(cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _gate.Release();
        }
    }

    public void Update(Action<AppSettings> updater)
    {
        updater(Current);
    }

    private async Task<AppSettings> LoadOrCreateAsync(CancellationToken cancellationToken)
    {
        if (File.Exists(_filePath))
        {
            var json = await File.ReadAllTextAsync(_filePath, cancellationToken).ConfigureAwait(false);
            var loaded = JsonSerializer.Deserialize<AppSettings>(json, ProtocolJson.SharedOptions);
            if (loaded is not null)
            {
                Normalize(loaded);
                return loaded;
            }
        }

        var defaults = AppSettings.CreateDefault();
        Normalize(defaults);
        return defaults;
    }

    private async Task SaveCoreAsync(CancellationToken cancellationToken)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(_filePath)!);
        var json = JsonSerializer.Serialize(Current, ProtocolJson.SharedOptions);
        await File.WriteAllTextAsync(_filePath, json, cancellationToken).ConfigureAwait(false);
    }

    private static void Normalize(AppSettings settings)
    {
        if (string.IsNullOrWhiteSpace(settings.PcName))
        {
            settings.PcName = Environment.MachineName;
        }

        if (string.IsNullOrWhiteSpace(settings.DeviceId))
        {
            settings.DeviceId = Guid.NewGuid().ToString();
        }

        if (settings.ServerPort <= 0)
        {
            settings.ServerPort = ProtocolConstants.DefaultSecurePort;
        }

        if (settings.ServerPortInsecure <= 0)
        {
            settings.ServerPortInsecure = ProtocolConstants.DefaultInsecurePort;
        }

        if (settings.DiscoveryPort <= 0)
        {
            settings.DiscoveryPort = ProtocolConstants.DefaultDiscoveryPort;
        }

        if (string.IsNullOrWhiteSpace(settings.FirewallProfile))
        {
            settings.FirewallProfile = "private";
        }

        if (settings.SchemaVersion < AppSettings.CurrentSchemaVersion)
        {
            if (settings.RemoteControlConsentGranted &&
                !settings.EnableRemoteAccess &&
                settings.TermsOfServiceAccepted &&
                settings.TermsAndConditionsAccepted &&
                settings.PrivacyPolicyAccepted)
            {
                settings.EnableRemoteAccess = true;
            }

            settings.SchemaVersion = AppSettings.CurrentSchemaVersion;
        }
    }
}
