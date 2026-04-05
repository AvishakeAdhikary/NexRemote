using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Windows.Storage;

namespace NexRemote.Helpers;

public static class PathHelper
{
    private const string AppFolderName = "NexRemote";
    private const string LegacyFolderName = "NexRemote";

    public static string GetAppDataRoot()
    {
        try
        {
            return ApplicationData.Current.LocalFolder.Path;
        }
        catch
        {
            var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var root = Path.Combine(localAppData, AppFolderName);
            Directory.CreateDirectory(root);
            return root;
        }
    }

    public static string GetSettingsPath() => Path.Combine(GetAppDataRoot(), "settings.json");

    public static string GetLogsDirectory()
    {
        var path = Path.Combine(GetAppDataRoot(), "logs");
        Directory.CreateDirectory(path);
        return path;
    }

    public static string GetCertificatesDirectory()
    {
        var path = Path.Combine(GetAppDataRoot(), "certs");
        Directory.CreateDirectory(path);
        return path;
    }

    public static string GetTrustedDevicesPath() => Path.Combine(GetAppDataRoot(), "trusted_devices.json");

    public static string GetAuditLogPath() => Path.Combine(GetLogsDirectory(), "audit.log");

    public static IEnumerable<string> GetLegacyRoots()
    {
        var roots = new List<string>();

        try
        {
            var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var legacyRoot = Path.Combine(localAppData, LegacyFolderName);
            var appRoot = GetAppDataRoot();
            if (!string.Equals(
                    Path.GetFullPath(legacyRoot),
                    Path.GetFullPath(appRoot),
                    StringComparison.OrdinalIgnoreCase))
            {
                TryAddRoot(legacyRoot, roots);
            }
        }
        catch
        {
            // ignored
        }

        return roots
            .Where(path => !string.IsNullOrWhiteSpace(path))
            .Distinct(StringComparer.OrdinalIgnoreCase);
    }

    public static bool TryFindLegacyCertificatePair(out string certificatePath, out string privateKeyPath)
    {
        foreach (var root in GetLegacyRoots())
        {
            var certDir = Path.Combine(root, "certs");
            var certCandidate = Path.Combine(certDir, "server.crt");
            var keyCandidate = Path.Combine(certDir, "server.key");
            if (File.Exists(certCandidate) && File.Exists(keyCandidate))
            {
                certificatePath = certCandidate;
                privateKeyPath = keyCandidate;
                return true;
            }
        }

        certificatePath = string.Empty;
        privateKeyPath = string.Empty;
        return false;
    }

    public static IEnumerable<string> GetLegacySettingsCandidates()
    {
        foreach (var root in GetLegacyRoots())
        {
            yield return Path.Combine(root, "config.json");
            yield return Path.Combine(root, "settings.json");
        }
    }

    public static IEnumerable<string> GetLegacyTrustedDeviceCandidates()
    {
        foreach (var root in GetLegacyRoots())
        {
            yield return Path.Combine(root, "trusted_devices.json");
        }
    }

    public static IEnumerable<string> GetLegacyCertificateCandidates()
    {
        foreach (var root in GetLegacyRoots())
        {
            var certDir = Path.Combine(root, "certs");
            yield return Path.Combine(certDir, "server.crt");
            yield return Path.Combine(certDir, "server.key");
        }
    }

    public static IEnumerable<string> GetLegacyAuditLogCandidates()
    {
        foreach (var root in GetLegacyRoots())
        {
            var logDir = Path.Combine(root, "logs");
            yield return Path.Combine(logDir, "audit.log");
            yield return Path.Combine(logDir, "nexremote.log");
        }
    }

    private static void TryAddRoot(string path, ICollection<string> roots)
    {
        try
        {
            var fullPath = Path.GetFullPath(path);
            if (Directory.Exists(fullPath))
            {
                roots.Add(fullPath);
            }
        }
        catch
        {
            // ignored
        }
    }
}
