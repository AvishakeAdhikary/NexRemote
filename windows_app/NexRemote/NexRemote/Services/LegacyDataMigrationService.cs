using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using NexRemote.Helpers;
using NexRemote.Models;

namespace NexRemote.Services;

public sealed record LegacyMigrationResult(
    bool MigratedSettings,
    bool MigratedTrustedDevices,
    bool MigratedCertificates,
    bool MigratedLogs);

public interface ILegacyDataMigrationService
{
    Task<LegacyMigrationResult> MigrateAsync(AppSettings currentSettings, CancellationToken cancellationToken = default);
}

public sealed class LegacyDataMigrationService : ILegacyDataMigrationService
{
    public async Task<LegacyMigrationResult> MigrateAsync(AppSettings currentSettings, CancellationToken cancellationToken = default)
    {
        var migratedSettings = await TryMigrateSettingsAsync(currentSettings, cancellationToken).ConfigureAwait(false);
        var migratedTrustedDevices = await TryMigrateTrustedDevicesAsync(cancellationToken).ConfigureAwait(false);
        var migratedCertificates = await TryMigrateCertificatesAsync(cancellationToken).ConfigureAwait(false);
        var migratedLogs = await TryMigrateLogsAsync(cancellationToken).ConfigureAwait(false);

        return new LegacyMigrationResult(migratedSettings, migratedTrustedDevices, migratedCertificates, migratedLogs);
    }

    private static async Task<bool> TryMigrateSettingsAsync(AppSettings currentSettings, CancellationToken cancellationToken)
    {
        foreach (var candidate in PathHelper.GetLegacySettingsCandidates())
        {
            if (!File.Exists(candidate))
            {
                continue;
            }

            var json = await File.ReadAllTextAsync(candidate, cancellationToken).ConfigureAwait(false);
            if (string.IsNullOrWhiteSpace(json))
            {
                continue;
            }

            using var document = JsonDocument.Parse(json);
            var root = document.RootElement;

            currentSettings.PcName = ReadString(root, "pc_name", currentSettings.PcName);
            currentSettings.DeviceId = ReadString(root, "device_id", currentSettings.DeviceId);
            currentSettings.ServerPort = ReadInt(root, "server_port", currentSettings.ServerPort);
            currentSettings.ServerPortInsecure = ReadInt(root, "server_port_insecure", currentSettings.ServerPortInsecure);
            currentSettings.DiscoveryPort = ReadInt(root, "discovery_port", currentSettings.DiscoveryPort);
            currentSettings.EnableRemoteAccess = ReadBool(root, "enable_remote_access", currentSettings.EnableRemoteAccess);
            currentSettings.MaxClients = ReadInt(root, "max_clients", currentSettings.MaxClients);
            currentSettings.LogLevel = ReadString(root, "log_level", currentSettings.LogLevel);
            currentSettings.AutoStart = ReadBool(root, "auto_start", currentSettings.AutoStart);
            currentSettings.MinimizeToTray = ReadBool(root, "minimize_to_tray", currentSettings.MinimizeToTray);
            currentSettings.RequireApproval = ReadBool(root, "require_approval", currentSettings.RequireApproval);
            currentSettings.TermsAccepted = ReadBool(root, "terms_accepted", currentSettings.TermsAccepted);
            currentSettings.FirewallConfigured = ReadBool(root, "firewall_configured", currentSettings.FirewallConfigured);
            currentSettings.FirewallProfile = ReadString(root, "firewall_profile", currentSettings.FirewallProfile);

            if (TryReadString(root, "terms_accepted_at", out var acceptedAt) &&
                DateTimeOffset.TryParse(acceptedAt, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var accepted))
            {
                currentSettings.TermsAcceptedAt = accepted;
            }

            return true;
        }

        return false;
    }

    private static async Task<bool> TryMigrateTrustedDevicesAsync(CancellationToken cancellationToken)
    {
        var target = PathHelper.GetTrustedDevicesPath();
        if (File.Exists(target))
        {
            return false;
        }

        foreach (var candidate in PathHelper.GetLegacyTrustedDeviceCandidates())
        {
            if (!File.Exists(candidate))
            {
                continue;
            }

            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            var json = await File.ReadAllTextAsync(candidate, cancellationToken).ConfigureAwait(false);
            await File.WriteAllTextAsync(target, json, cancellationToken).ConfigureAwait(false);
            return true;
        }

        return false;
    }

    private static async Task<bool> TryMigrateCertificatesAsync(CancellationToken cancellationToken)
    {
        if (!PathHelper.TryFindLegacyCertificatePair(out var legacyCertPath, out var legacyKeyPath))
        {
            return false;
        }

        var certDir = PathHelper.GetCertificatesDirectory();
        var certPath = Path.Combine(certDir, "server.crt");
        var keyPath = Path.Combine(certDir, "server.key");
        var targetExists = File.Exists(certPath) && File.Exists(keyPath);
        Directory.CreateDirectory(certDir);

        if (!targetExists)
        {
            await CopyAsync(legacyCertPath, certPath, cancellationToken).ConfigureAwait(false);
            await CopyAsync(legacyKeyPath, keyPath, cancellationToken).ConfigureAwait(false);
            return true;
        }

        var legacyThumbprint = TryGetThumbprint(legacyCertPath, legacyKeyPath);
        var currentThumbprint = TryGetThumbprint(certPath, keyPath);
        if (string.IsNullOrWhiteSpace(legacyThumbprint) ||
            string.IsNullOrWhiteSpace(currentThumbprint) ||
            string.Equals(legacyThumbprint, currentThumbprint, StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        await CopyAsync(legacyCertPath, certPath, cancellationToken).ConfigureAwait(false);
        await CopyAsync(legacyKeyPath, keyPath, cancellationToken).ConfigureAwait(false);
        return true;
    }

    private static async Task<bool> TryMigrateLogsAsync(CancellationToken cancellationToken)
    {
        var target = PathHelper.GetAuditLogPath();
        if (File.Exists(target))
        {
            return false;
        }

        foreach (var candidate in PathHelper.GetLegacyAuditLogCandidates())
        {
            if (!File.Exists(candidate))
            {
                continue;
            }

            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            await CopyAsync(candidate, target, cancellationToken).ConfigureAwait(false);
            return true;
        }

        return false;
    }

    private static async Task CopyAsync(string source, string destination, CancellationToken cancellationToken)
    {
        var bytes = await File.ReadAllBytesAsync(source, cancellationToken).ConfigureAwait(false);
        await File.WriteAllBytesAsync(destination, bytes, cancellationToken).ConfigureAwait(false);
    }

    private static string? TryGetThumbprint(string certificatePath, string privateKeyPath)
    {
        try
        {
            using var certificate = X509Certificate2.CreateFromPemFile(certificatePath, privateKeyPath);
            return certificate.Thumbprint;
        }
        catch
        {
            return null;
        }
    }

    private static string ReadString(JsonElement root, string name, string fallback)
        => TryReadString(root, name, out var value) ? value : fallback;

    private static bool TryReadString(JsonElement root, string name, out string value)
    {
        value = string.Empty;
        if (root.ValueKind == JsonValueKind.Object &&
            root.TryGetProperty(name, out var prop) &&
            prop.ValueKind == JsonValueKind.String)
        {
            value = prop.GetString() ?? string.Empty;
            return true;
        }

        return false;
    }

    private static int ReadInt(JsonElement root, string name, int fallback)
    {
        if (root.ValueKind == JsonValueKind.Object &&
            root.TryGetProperty(name, out var prop) &&
            prop.TryGetInt32(out var value))
        {
            return value;
        }

        return fallback;
    }

    private static bool ReadBool(JsonElement root, string name, bool fallback)
    {
        if (root.ValueKind == JsonValueKind.Object &&
            root.TryGetProperty(name, out var prop) &&
            prop.ValueKind is JsonValueKind.True or JsonValueKind.False)
        {
            return prop.GetBoolean();
        }

        return fallback;
    }
}
