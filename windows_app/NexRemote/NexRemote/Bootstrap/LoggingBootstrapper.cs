using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using NexRemote.Helpers;
using Serilog;
using Serilog.Events;

namespace NexRemote.Bootstrap;

public static class LoggingBootstrapper
{
    public static void ConfigureBootstrapLogger()
    {
        var logPath = PathHelper.GetOperationalLogPath();
        CompactOperationalLog(logPath, DateTimeOffset.UtcNow.AddDays(-30));
        Log.Logger = CreateConfiguration(logPath).CreateLogger();
    }

    public static void ConfigureLogger(LoggerConfiguration loggerConfiguration)
    {
        var logPath = PathHelper.GetOperationalLogPath();
        CompactOperationalLog(logPath, DateTimeOffset.UtcNow.AddDays(-30));
        CreateConfiguration(logPath, loggerConfiguration);
    }

    private static LoggerConfiguration CreateConfiguration(string logPath, LoggerConfiguration? loggerConfiguration = null)
    {
        var level = ResolveMinimumLevel();
        return (loggerConfiguration ?? new LoggerConfiguration())
            .MinimumLevel.Is(level)
            .Enrich.FromLogContext()
            .WriteTo.File(
                path: logPath,
                rollingInterval: RollingInterval.Infinite,
                retainedFileCountLimit: 1,
                shared: true,
                outputTemplate: "[{Timestamp:O}] [{Level:u3}] {Message:lj}{NewLine}{Exception}");
    }

    private static LogEventLevel ResolveMinimumLevel()
    {
        if (Debugger.IsAttached)
        {
            return LogEventLevel.Debug;
        }

        var environment = Environment.GetEnvironmentVariable("DOTNET_ENVIRONMENT");
        return string.Equals(environment, "Development", StringComparison.OrdinalIgnoreCase)
            ? LogEventLevel.Debug
            : LogEventLevel.Information;
    }

    private static void CompactOperationalLog(string logPath, DateTimeOffset cutoff)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(logPath)!);
            if (!File.Exists(logPath))
            {
                return;
            }

            var retainedEntries = new List<string>();
            var currentEntry = new List<string>();
            var keepCurrent = false;
            foreach (var line in File.ReadLines(logPath))
            {
                if (TryParseEntryTimestamp(line, out var timestamp))
                {
                    if (currentEntry.Count > 0 && keepCurrent)
                    {
                        retainedEntries.AddRange(currentEntry);
                    }

                    currentEntry.Clear();
                    keepCurrent = timestamp >= cutoff;
                }

                currentEntry.Add(line);
            }

            if (currentEntry.Count > 0 && keepCurrent)
            {
                retainedEntries.AddRange(currentEntry);
            }

            File.WriteAllLines(logPath, retainedEntries);
        }
        catch
        {
            // ignored
        }
    }

    private static bool TryParseEntryTimestamp(string line, out DateTimeOffset timestamp)
    {
        timestamp = default;
        if (string.IsNullOrWhiteSpace(line) || line.Length < 3 || line[0] != '[')
        {
            return false;
        }

        var end = line.IndexOf(']');
        if (end <= 1)
        {
            return false;
        }

        var text = line.Substring(1, end - 1);
        return DateTimeOffset.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal, out timestamp);
    }
}
