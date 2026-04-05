using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using NexRemote.Helpers;
using NexRemote.Models;

namespace NexRemote.Services;

public interface ITrustedDeviceService
{
    IReadOnlyDictionary<string, TrustedDeviceRecord> Devices { get; }
    bool IsTrusted(string deviceId);
    TrustedDeviceRecord? Get(string deviceId);
    Task InitializeAsync(CancellationToken cancellationToken = default);
    Task SaveAsync(CancellationToken cancellationToken = default);
    void RecordConnection(string deviceId, string deviceName);
    void Add(string deviceId, string deviceName);
    void Remove(string deviceId);
    void ReplaceAll(IDictionary<string, TrustedDeviceRecord> devices);
}

public sealed class TrustedDeviceService : ITrustedDeviceService
{
    private readonly string _filePath = PathHelper.GetTrustedDevicesPath();
    private readonly SemaphoreSlim _gate = new(1, 1);
    private readonly Dictionary<string, TrustedDeviceRecord> _devices = new(StringComparer.OrdinalIgnoreCase);

    public IReadOnlyDictionary<string, TrustedDeviceRecord> Devices => _devices;

    public bool IsTrusted(string deviceId) => _devices.ContainsKey(deviceId);

    public TrustedDeviceRecord? Get(string deviceId) => _devices.TryGetValue(deviceId, out var record) ? record : null;

    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (File.Exists(_filePath))
            {
                await LoadAsync(_filePath, cancellationToken).ConfigureAwait(false);
                return;
            }

            var legacyPath = GetLegacyTrustedDevicesPath();
            if (!string.IsNullOrWhiteSpace(legacyPath) && File.Exists(legacyPath))
            {
                await LoadAsync(legacyPath, cancellationToken).ConfigureAwait(false);
                Directory.CreateDirectory(Path.GetDirectoryName(_filePath)!);
                var json = JsonSerializer.Serialize(_devices, ProtocolJson.SharedOptions);
                await File.WriteAllTextAsync(_filePath, json, cancellationToken).ConfigureAwait(false);
            }
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
            Directory.CreateDirectory(Path.GetDirectoryName(_filePath)!);
            var json = JsonSerializer.Serialize(_devices, ProtocolJson.SharedOptions);
            await File.WriteAllTextAsync(_filePath, json, cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _gate.Release();
        }
    }

    public void RecordConnection(string deviceId, string deviceName)
    {
        var now = DateTimeOffset.UtcNow;
        if (_devices.TryGetValue(deviceId, out var existing))
        {
            existing.Name = deviceName;
            existing.LastConnected = now;
        }
        else
        {
            _devices[deviceId] = new TrustedDeviceRecord
            {
                Name = deviceName,
                FirstConnected = now,
                LastConnected = now
            };
        }
    }

    public void Add(string deviceId, string deviceName)
    {
        var now = DateTimeOffset.UtcNow;
        _devices[deviceId] = new TrustedDeviceRecord
        {
            Name = deviceName,
            FirstConnected = now,
            LastConnected = now
        };
    }

    public void Remove(string deviceId) => _devices.Remove(deviceId);

    public void ReplaceAll(IDictionary<string, TrustedDeviceRecord> devices)
    {
        _devices.Clear();
        foreach (var pair in devices)
        {
            _devices[pair.Key] = pair.Value;
        }
    }

    private async Task LoadAsync(string path, CancellationToken cancellationToken)
    {
        var json = await File.ReadAllTextAsync(path, cancellationToken).ConfigureAwait(false);
        if (string.IsNullOrWhiteSpace(json))
        {
            return;
        }

        using var document = JsonDocument.Parse(json);
        if (document.RootElement.ValueKind != JsonValueKind.Object)
        {
            return;
        }

        _devices.Clear();
        foreach (var pair in document.RootElement.EnumerateObject())
        {
            var element = pair.Value;
            var record = new TrustedDeviceRecord
            {
                Name = element.TryGetProperty("name", out var nameProp) ? nameProp.GetString() ?? string.Empty : string.Empty,
                FirstConnected = ReadTimestamp(element, "first_connected"),
                LastConnected = ReadTimestamp(element, "last_connected")
            };
            _devices[pair.Name] = record;
        }
    }

    private static DateTimeOffset ReadTimestamp(JsonElement element, string propertyName)
    {
        if (!element.TryGetProperty(propertyName, out var property))
        {
            return DateTimeOffset.UtcNow;
        }

        if (property.ValueKind == JsonValueKind.Number && property.TryGetDouble(out var unixSeconds))
        {
            return DateTimeOffset.FromUnixTimeSeconds((long)unixSeconds);
        }

        if (property.ValueKind == JsonValueKind.String &&
            DateTimeOffset.TryParse(property.GetString(), out var parsed))
        {
            return parsed;
        }

        return DateTimeOffset.UtcNow;
    }

    private static string? GetLegacyTrustedDevicesPath()
    {
        try
        {
            var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var legacyPath = Path.Combine(localAppData, "NexRemote", "trusted_devices.json");
            var currentPath = PathHelper.GetTrustedDevicesPath();
            return string.Equals(
                    Path.GetFullPath(legacyPath),
                    Path.GetFullPath(currentPath),
                    StringComparison.OrdinalIgnoreCase)
                ? null
                : legacyPath;
        }
        catch
        {
            return null;
        }
    }
}
