using System;
using System.Runtime.InteropServices;
using System.Text.Json;

namespace NexRemote.Services;

public interface IClipboardService
{
    object HandleRequest(JsonElement data);
}

public sealed class ClipboardService : IClipboardService
{
    private const uint CfUnicodeText = 13;
    private const uint GmemMoveable = 0x0002;

    public object HandleRequest(JsonElement data)
    {
        var action = GetString(data, "action").ToLowerInvariant();
        return action switch
        {
            "get" => new { type = "clipboard", action = "content", text = ReadText() ?? string.Empty },
            "set" => SetText(GetString(data, "text")),
            "clear" => Clear(),
            _ => new { type = "clipboard", action = "error", message = $"Unknown action: {action}" }
        };
    }

    private static object SetText(string value)
    {
        try
        {
            if (!OpenClipboard(IntPtr.Zero))
            {
                return Error("Clipboard is busy");
            }

            EmptyClipboard();
            var bytes = (value + '\0').ToCharArray();
            var size = bytes.Length * sizeof(char);
            var handle = GlobalAlloc(GmemMoveable, (UIntPtr)size);
            if (handle == IntPtr.Zero)
            {
                return Error("Failed to allocate clipboard memory");
            }

            var pointer = GlobalLock(handle);
            if (pointer == IntPtr.Zero)
            {
                GlobalFree(handle);
                return Error("Failed to lock clipboard memory");
            }

            try
            {
                Marshal.Copy(bytes, 0, pointer, bytes.Length);
            }
            finally
            {
                GlobalUnlock(handle);
            }

            SetClipboardData(CfUnicodeText, handle);
            return new { type = "clipboard", action = "updated", text = value };
        }
        catch (Exception ex)
        {
            return Error(ex.Message);
        }
        finally
        {
            CloseClipboard();
        }
    }

    private static object Clear()
    {
        try
        {
            if (!OpenClipboard(IntPtr.Zero))
            {
                return Error("Clipboard is busy");
            }

            EmptyClipboard();
            return new { type = "clipboard", action = "cleared" };
        }
        catch (Exception ex)
        {
            return Error(ex.Message);
        }
        finally
        {
            CloseClipboard();
        }
    }

    private static string? ReadText()
    {
        if (!OpenClipboard(IntPtr.Zero))
        {
            return null;
        }

        try
        {
            var handle = GetClipboardData(CfUnicodeText);
            if (handle == IntPtr.Zero)
            {
                return null;
            }

            var pointer = GlobalLock(handle);
            if (pointer == IntPtr.Zero)
            {
                return null;
            }

            try
            {
                return Marshal.PtrToStringUni(pointer);
            }
            finally
            {
                GlobalUnlock(handle);
            }
        }
        finally
        {
            CloseClipboard();
        }
    }

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

    private static object Error(string message) => new { type = "clipboard", action = "error", message };

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool OpenClipboard(IntPtr hWndNewOwner);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool CloseClipboard();

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool EmptyClipboard();

    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr GetClipboardData(uint uFormat);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr SetClipboardData(uint uFormat, IntPtr hMem);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr GlobalAlloc(uint uFlags, UIntPtr dwBytes);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr GlobalLock(IntPtr hMem);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GlobalUnlock(IntPtr hMem);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr GlobalFree(IntPtr hMem);
}
