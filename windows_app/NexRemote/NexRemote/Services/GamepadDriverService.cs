using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using Microsoft.Win32;
using NexRemote.Helpers;

namespace NexRemote.Services;

public interface IGamepadDriverService
{
    bool IsViGEmBusInstalled();
    Task<bool> IsViGEmBusInstalledAsync();
    bool IsNativeTransportReady();
    Task<bool> IsNativeTransportReadyAsync();
}

public sealed class GamepadDriverService : IGamepadDriverService
{
    public bool IsViGEmBusInstalled() => QueryViGEmBusInstalled();

    public Task<bool> IsViGEmBusInstalledAsync() => Task.Run(QueryViGEmBusInstalled);

    public bool IsNativeTransportReady() => QueryViGEmBusInstalled() && !string.IsNullOrWhiteSpace(ResolveCompanionPath());

    public Task<bool> IsNativeTransportReadyAsync() => Task.Run(IsNativeTransportReady);

    private static bool QueryViGEmBusInstalled()
    {
        if (TryQueryService())
        {
            return true;
        }

        if (TryReadServiceRegistry())
        {
            return true;
        }

        if (TryEnumerateDrivers())
        {
            return true;
        }

        return false;
    }

    private static bool TryQueryService()
    {
        try
        {
            using var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "sc.exe",
                    Arguments = "query ViGEmBus",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                }
            };

            process.Start();
            process.WaitForExit(5000);
            return process.ExitCode == 0;
        }
        catch
        {
            return false;
        }
    }

    private static bool TryReadServiceRegistry()
    {
        try
        {
            using var key = Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Services\ViGEmBus");
            return key is not null;
        }
        catch
        {
            return false;
        }
    }

    private static bool TryEnumerateDrivers()
    {
        try
        {
            using var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "pnputil.exe",
                    Arguments = "/enum-drivers",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                }
            };

            process.Start();
            var output = process.StandardOutput.ReadToEnd();
            process.WaitForExit(5000);
            if (process.ExitCode != 0)
            {
                return false;
            }

            return output.Contains("vigembus.inf", StringComparison.OrdinalIgnoreCase) ||
                   output.Contains("Nefarius", StringComparison.OrdinalIgnoreCase);
        }
        catch
        {
            return false;
        }
    }

    private static string ResolveCompanionPath()
    {
        var candidates = new[]
        {
            Path.Combine(PathHelper.GetToolsDirectory(), "gamepad-companion", "NexRemote.GamepadCompanion.exe"),
            Path.Combine(AppContext.BaseDirectory, "gamepad-companion", "NexRemote.GamepadCompanion.exe")
        };

        foreach (var candidate in candidates)
        {
            if (File.Exists(candidate))
            {
                return candidate;
            }
        }

        return string.Empty;
    }
}
