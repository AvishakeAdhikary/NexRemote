using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using NexRemote.Helpers;

namespace NexRemote.Services;

public sealed class AdbBridgeStatus
{
    public bool ToolAvailable { get; init; }
    public string ToolPath { get; init; } = string.Empty;
    public bool DeviceDetected { get; init; }
    public bool DeviceAuthorized { get; init; }
    public bool ReverseActive { get; init; }
    public string State { get; init; } = "unavailable";
    public string Reason { get; init; } = "ADB platform-tools are not available.";
}

public interface IAdbBridgeService
{
    AdbBridgeStatus CurrentStatus { get; }
    event EventHandler<AdbBridgeStatus>? StatusChanged;
    Task InitializeAsync(CancellationToken cancellationToken = default);
    Task StopAsync(CancellationToken cancellationToken = default);
}

public sealed class AdbBridgeService : IAdbBridgeService
{
    private readonly SemaphoreSlim _gate = new(1, 1);
    private CancellationTokenSource? _workerCts;
    private Task? _workerTask;
    private AdbBridgeStatus _currentStatus = new();

    public AdbBridgeStatus CurrentStatus => _currentStatus;

    public event EventHandler<AdbBridgeStatus>? StatusChanged;

    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (_workerTask is { IsCompleted: false })
            {
                return;
            }

            _workerCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            _workerTask = Task.Run(() => RunAsync(_workerCts.Token), _workerCts.Token);
        }
        finally
        {
            _gate.Release();
        }
    }

    public async Task StopAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (_workerCts is not null)
            {
                _workerCts.Cancel();
                _workerCts.Dispose();
                _workerCts = null;
            }

            if (_workerTask is not null)
            {
                try
                {
                    await _workerTask.ConfigureAwait(false);
                }
                catch
                {
                    // ignored
                }
            }

            _workerTask = null;
            UpdateStatus(new AdbBridgeStatus());
        }
        finally
        {
            _gate.Release();
        }
    }

    private async Task RunAsync(CancellationToken cancellationToken)
    {
        while (!cancellationToken.IsCancellationRequested)
        {
            var toolPath = ResolveAdbPath();
            if (string.IsNullOrWhiteSpace(toolPath))
            {
                UpdateStatus(new AdbBridgeStatus());
                await Task.Delay(TimeSpan.FromSeconds(5), cancellationToken).ConfigureAwait(false);
                continue;
            }

            await EnsureServerStartedAsync(toolPath, cancellationToken).ConfigureAwait(false);
            var devices = await QueryDevicesAsync(toolPath, cancellationToken).ConfigureAwait(false);
            var authorizedDevices = devices.Where(static device => device.State == "device").ToArray();
            var unauthorized = devices.Any(static device => device.State == "unauthorized");
            var reverseActive = false;

            foreach (var device in authorizedDevices)
            {
                reverseActive |= await EnsureReverseAsync(toolPath, device.Serial, cancellationToken).ConfigureAwait(false);
            }

            UpdateStatus(new AdbBridgeStatus
            {
                ToolAvailable = true,
                ToolPath = toolPath,
                DeviceDetected = devices.Count > 0,
                DeviceAuthorized = authorizedDevices.Length > 0,
                ReverseActive = reverseActive,
                State = reverseActive
                    ? "reverse_active"
                    : unauthorized
                        ? "device_unauthorized"
                        : devices.Count > 0
                            ? "device_detected"
                            : "idle",
                Reason = reverseActive
                    ? "ADB reverse is active for an attached device."
                    : unauthorized
                        ? "USB debugging is connected, but the device still needs RSA authorization."
                        : devices.Count > 0
                            ? "ADB sees a device, but reverse is not active yet."
                            : "ADB is ready. Connect a device with USB debugging to enable USB mode."
            });

            await Task.Delay(TimeSpan.FromSeconds(5), cancellationToken).ConfigureAwait(false);
        }
    }

    private void UpdateStatus(AdbBridgeStatus next)
    {
        _currentStatus = next;
        StatusChanged?.Invoke(this, next);
    }

    private static string ResolveAdbPath()
    {
        var candidates = new[]
        {
            Path.Combine(PathHelper.GetToolsDirectory(), "platform-tools", "adb.exe"),
            Path.Combine(AppContext.BaseDirectory, "platform-tools", "adb.exe"),
            Path.Combine(AppContext.BaseDirectory, "tools", "platform-tools", "adb.exe")
        };

        foreach (var candidate in candidates)
        {
            if (File.Exists(candidate))
            {
                return candidate;
            }
        }

        try
        {
            using var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "where.exe",
                    Arguments = "adb",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                }
            };

            process.Start();
            var path = process.StandardOutput.ReadLine();
            process.WaitForExit(5000);
            if (process.ExitCode == 0 && !string.IsNullOrWhiteSpace(path) && File.Exists(path))
            {
                return path;
            }
        }
        catch
        {
            // ignored
        }

        return string.Empty;
    }

    private static async Task EnsureServerStartedAsync(string toolPath, CancellationToken cancellationToken)
    {
        await RunProcessAsync(toolPath, "start-server", cancellationToken).ConfigureAwait(false);
    }

    private static async Task<IReadOnlyList<AdbDevice>> QueryDevicesAsync(string toolPath, CancellationToken cancellationToken)
    {
        var output = await RunProcessAsync(toolPath, "devices", cancellationToken).ConfigureAwait(false);
        return output
            .Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries)
            .Skip(1)
            .Select(line =>
            {
                var parts = line.Split('\t', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
                return parts.Length >= 2 ? new AdbDevice(parts[0], parts[1]) : new AdbDevice(string.Empty, string.Empty);
            })
            .Where(device => !string.IsNullOrWhiteSpace(device.Serial))
            .ToArray();
    }

    private static async Task<bool> EnsureReverseAsync(string toolPath, string serial, CancellationToken cancellationToken)
    {
        var output = await RunProcessAsync(toolPath, $"-s {serial} reverse tcp:8766 tcp:8766", cancellationToken).ConfigureAwait(false);
        return !output.Contains("error", StringComparison.OrdinalIgnoreCase);
    }

    private static async Task<string> RunProcessAsync(string fileName, string arguments, CancellationToken cancellationToken)
    {
        using var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = fileName,
                Arguments = arguments,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8
            }
        };

        process.Start();
        var outputTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var errorTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        return (await outputTask.ConfigureAwait(false)) + Environment.NewLine + (await errorTask.ConfigureAwait(false));
    }

    private sealed record AdbDevice(string Serial, string State);
}
