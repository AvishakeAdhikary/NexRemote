using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Threading.Tasks;

namespace NexRemote.Services;

internal sealed class TaskManagerService
{
    private readonly object _sampleGate = new();
    private readonly Dictionary<int, ProcessSample> _processSamples = new();
    private CpuSample? _systemCpuSample;

    public Task<object> HandleRequestAsync(JsonElement data)
    {
        try
        {
            var action = GetString(data, "action");
            object response = action switch
            {
                "list_processes" => ListProcesses(),
                "end_process" => EndProcess(ReadInt32(data, "pid")),
                "system_info" => GetSystemInfo(),
                _ => new { type = "task_manager", action = "error", message = $"Unknown action: {action}" }
            };

            return Task.FromResult(response);
        }
        catch (Exception ex)
        {
            return Task.FromResult<object>(new { type = "task_manager", action = "error", message = ex.Message });
        }
    }

    private object ListProcesses()
    {
        try
        {
            var processes = new List<object>();
            foreach (var process in Process.GetProcesses())
            {
                try
                {
                    processes.Add(new
                    {
                        pid = process.Id,
                        name = SafeProcessName(process),
                        cpu = Math.Round(GetProcessCpuUsage(process), 1),
                        memory = process.WorkingSet64
                    });
                }
                catch
                {
                    // Skip inaccessible process.
                }
                finally
                {
                    process.Dispose();
                }
            }

            var ordered = processes
                .Cast<dynamic>()
                .OrderByDescending(item => (double)item.cpu)
                .ThenBy(item => ((string)item.name).ToLowerInvariant())
                .Cast<object>()
                .ToList();

            return new
            {
                type = "task_manager",
                action = "list_processes",
                processes = ordered
            };
        }
        catch (Exception ex)
        {
            return Error($"Failed to list processes: {ex.Message}");
        }
    }

    private object EndProcess(int pid)
    {
        try
        {
            using var process = Process.GetProcessById(pid);
            var name = SafeProcessName(process);
            process.Kill(entireProcessTree: true);
            process.WaitForExit(3000);

            return new
            {
                type = "task_manager",
                action = "process_ended",
                pid,
                name
            };
        }
        catch (ArgumentException)
        {
            return Error("Process not found");
        }
        catch (UnauthorizedAccessException)
        {
            return new
            {
                type = "task_manager",
                action = "error",
                message = "Elevation required",
                elevation_required = true
            };
        }
        catch (Exception ex)
        {
            return Error($"Failed to end process: {ex.Message}");
        }
    }

    private object GetSystemInfo()
    {
        try
        {
            var memory = new MemoryStatusEx();
            memory.Init();
            if (!GlobalMemoryStatusEx(ref memory))
            {
                throw new InvalidOperationException("GlobalMemoryStatusEx failed");
            }

            var disk = DriveInfo.GetDrives()
                .FirstOrDefault(drive => drive.IsReady && string.Equals(drive.Name, @"C:\", StringComparison.OrdinalIgnoreCase));

            var diskPercent = 0.0;
            if (disk is not null && disk.TotalSize > 0)
            {
                diskPercent = (disk.TotalSize - disk.AvailableFreeSpace) * 100.0 / disk.TotalSize;
            }

            return new
            {
                type = "task_manager",
                action = "system_info",
                cpu_usage = Math.Round(GetCpuUsage(), 1),
                memory_usage = Math.Round((double)memory.MemoryLoad, 1),
                disk_usage = Math.Round(diskPercent, 1),
                memory_total = memory.TotalPhys,
                memory_available = memory.AvailPhys
            };
        }
        catch (Exception ex)
        {
            return Error($"Failed to get system info: {ex.Message}");
        }
    }

    private static string SafeProcessName(Process process)
    {
        try
        {
            return process.ProcessName;
        }
        catch
        {
            return string.Empty;
        }
    }

    private static object Error(string message)
        => new { type = "task_manager", action = "error", message };

    private static string GetString(JsonElement element, string propertyName, string fallback = "")
    {
        if (element.ValueKind == JsonValueKind.Object &&
            element.TryGetProperty(propertyName, out var prop) &&
            prop.ValueKind == JsonValueKind.String)
        {
            return prop.GetString() ?? fallback;
        }

        return fallback;
    }

    private static int ReadInt32(JsonElement element, string propertyName, int fallback = 0)
    {
        if (element.ValueKind == JsonValueKind.Object &&
            element.TryGetProperty(propertyName, out var prop) &&
            prop.TryGetInt32(out var value))
        {
            return value;
        }

        return fallback;
    }

    private double GetProcessCpuUsage(Process process)
    {
        try
        {
            var now = DateTimeOffset.UtcNow;
            var totalProcessorTime = process.TotalProcessorTime;

            lock (_sampleGate)
            {
                if (_processSamples.TryGetValue(process.Id, out var previous))
                {
                    var elapsedMs = Math.Max(1, (now - previous.Timestamp).TotalMilliseconds);
                    var cpuDeltaMs = Math.Max(0, (totalProcessorTime - previous.TotalProcessorTime).TotalMilliseconds);
                    _processSamples[process.Id] = new ProcessSample(totalProcessorTime, now);
                    return Math.Clamp(cpuDeltaMs / (elapsedMs * Environment.ProcessorCount) * 100.0, 0.0, 100.0);
                }

                _processSamples[process.Id] = new ProcessSample(totalProcessorTime, now);
                return 0.0;
            }
        }
        catch
        {
            return 0.0;
        }
    }

    private double GetCpuUsage()
    {
        if (!GetSystemTimes(out var idleTime, out var kernelTime, out var userTime))
        {
            return 0.0;
        }

        var now = new CpuSample(ToUInt64(idleTime), ToUInt64(kernelTime), ToUInt64(userTime));
        lock (_sampleGate)
        {
            if (_systemCpuSample is null)
            {
                _systemCpuSample = now;
                return 0.0;
            }

            var previous = _systemCpuSample.Value;
            _systemCpuSample = now;

            var idle = now.Idle - previous.Idle;
            var kernel = now.Kernel - previous.Kernel;
            var user = now.User - previous.User;
            var total = kernel + user;
            if (total <= 0)
            {
                return 0.0;
            }

            return Math.Clamp((total - idle) * 100.0 / total, 0.0, 100.0);
        }
    }

    private static ulong ToUInt64(FILETIME time)
        => ((ulong)time.dwHighDateTime << 32) | time.dwLowDateTime;

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GlobalMemoryStatusEx(ref MemoryStatusEx buffer);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetSystemTimes(out FILETIME idleTime, out FILETIME kernelTime, out FILETIME userTime);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
    private struct MemoryStatusEx
    {
        public uint Length;
        public uint MemoryLoad;
        public ulong TotalPhys;
        public ulong AvailPhys;
        public ulong TotalPageFile;
        public ulong AvailPageFile;
        public ulong TotalVirtual;
        public ulong AvailVirtual;
        public ulong AvailExtendedVirtual;

        public void Init()
        {
            Length = (uint)Marshal.SizeOf<MemoryStatusEx>();
        }
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct FILETIME
    {
        public uint dwLowDateTime;
        public uint dwHighDateTime;
    }

    private readonly record struct ProcessSample(TimeSpan TotalProcessorTime, DateTimeOffset Timestamp);

    private readonly record struct CpuSample(ulong Idle, ulong Kernel, ulong User);
}
