using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace NexRemote.Services;

internal sealed class NativeInputService
{
    private const int InputKeyboard = 1;
    private const int InputMouse = 0;
    private const uint KeyeventfKeyup = 0x0002;
    private const uint KeyeventfUnicode = 0x0004;
    private const uint MouseeventfMove = 0x0001;
    private const uint MouseeventfAbsolute = 0x8000;
    private const uint MouseeventfLeftdown = 0x0002;
    private const uint MouseeventfLeftup = 0x0004;
    private const uint MouseeventfRightdown = 0x0008;
    private const uint MouseeventfRightup = 0x0010;
    private const uint MouseeventfMiddledown = 0x0020;
    private const uint MouseeventfMiddleup = 0x0040;
    private const uint MouseeventfXdown = 0x0080;
    private const uint MouseeventfXup = 0x0100;
    private const uint MouseeventfWheel = 0x0800;
    private const uint MouseeventfHwheel = 0x01000;
    private const uint MouseeventfVirtualdesk = 0x4000;
    private const int WheelDelta = 120;
    private const int SmXvirtualscreen = 76;
    private const int SmYvirtualscreen = 77;
    private const int SmCxvirtualscreen = 78;
    private const int SmCyvirtualscreen = 79;

    private static readonly IReadOnlyDictionary<string, ushort> VirtualKeys = new Dictionary<string, ushort>(StringComparer.OrdinalIgnoreCase)
    {
        ["enter"] = 0x0D,
        ["return"] = 0x0D,
        ["backspace"] = 0x08,
        ["tab"] = 0x09,
        ["space"] = 0x20,
        ["esc"] = 0x1B,
        ["escape"] = 0x1B,
        ["shift"] = 0x10,
        ["ctrl"] = 0x11,
        ["control"] = 0x11,
        ["alt"] = 0x12,
        ["cmd"] = 0x5B,
        ["win"] = 0x5B,
        ["caps_lock"] = 0x14,
        ["delete"] = 0x2E,
        ["end"] = 0x23,
        ["home"] = 0x24,
        ["page_up"] = 0x21,
        ["page_down"] = 0x22,
        ["left"] = 0x25,
        ["up"] = 0x26,
        ["right"] = 0x27,
        ["down"] = 0x28,
        ["f1"] = 0x70,
        ["f2"] = 0x71,
        ["f3"] = 0x72,
        ["f4"] = 0x73,
        ["f5"] = 0x74,
        ["f6"] = 0x75,
        ["f7"] = 0x76,
        ["f8"] = 0x77,
        ["f9"] = 0x78,
        ["f10"] = 0x79,
        ["f11"] = 0x7A,
        ["f12"] = 0x7B
    };

    public void SendKeyboard(JsonElement data)
    {
        var action = GetString(data, "action");
        switch (action.ToLowerInvariant())
        {
            case "type":
                TypeText(GetString(data, "text"));
                break;
            case "press":
                PressKey(GetString(data, "key"));
                break;
            case "release":
                ReleaseKey(GetString(data, "key"));
                break;
            case "hotkey":
                SendHotkey(ReadStringArray(data, "keys"));
                break;
        }
    }

    public void SendMouse(JsonElement data)
    {
        var action = GetString(data, "action");
        switch (action.ToLowerInvariant())
        {
            case "move":
                MoveAbsolute(ReadInt32(data, "x"), ReadInt32(data, "y"));
                break;
            case "move_relative":
                MoveRelative(ReadInt32(data, "dx"), ReadInt32(data, "dy"));
                break;
            case "click":
                Click(GetString(data, "button"), Math.Max(1, ReadInt32(data, "count", 1)));
                break;
            case "press":
                MouseDown(GetString(data, "button"));
                break;
            case "release":
                MouseUp(GetString(data, "button"));
                break;
            case "scroll":
                Scroll(ReadInt32(data, "dx"), ReadInt32(data, "dy"));
                break;
        }
    }

    public async Task ReplayMacroAsync(JsonElement steps, CancellationToken cancellationToken = default)
    {
        if (steps.ValueKind != JsonValueKind.Array)
        {
            return;
        }

        foreach (var step in steps.EnumerateArray())
        {
            cancellationToken.ThrowIfCancellationRequested();

            var action = GetString(step, "action");
            if (!string.IsNullOrWhiteSpace(action))
            {
                RunMacroAction(action);
            }

            var delay = ReadInt32(step, "delay", 0);
            if (delay > 0)
            {
                await Task.Delay(delay, cancellationToken).ConfigureAwait(false);
            }
        }
    }

    private static void RunMacroAction(string action)
    {
        if (action.StartsWith("keyboard:", StringComparison.OrdinalIgnoreCase))
        {
            var key = action["keyboard:".Length..];
            if (!string.IsNullOrWhiteSpace(key))
            {
                var input = new NativeInputService();
                input.PressKey(key);
                input.ReleaseKey(key);
            }

            return;
        }

        if (action.StartsWith("mouse:", StringComparison.OrdinalIgnoreCase))
        {
            var button = action["mouse:".Length..];
            var input = new NativeInputService();
            input.Click(button, 1);
        }
    }

    private void TypeText(string text)
    {
        if (string.IsNullOrEmpty(text))
        {
            return;
        }

        foreach (var ch in text)
        {
            SendUnicodeChar(ch, keyUp: false);
            SendUnicodeChar(ch, keyUp: true);
        }
    }

    private void PressKey(string key)
    {
        if (TryGetVirtualKey(key, out var vk))
        {
            SendVirtualKey(vk, keyUp: false);
            return;
        }

        if (!string.IsNullOrEmpty(key) && key.Length == 1)
        {
            SendUnicodeChar(key[0], keyUp: false);
        }
    }

    private void ReleaseKey(string key)
    {
        if (TryGetVirtualKey(key, out var vk))
        {
            SendVirtualKey(vk, keyUp: true);
            return;
        }

        if (!string.IsNullOrEmpty(key) && key.Length == 1)
        {
            SendUnicodeChar(key[0], keyUp: true);
        }
    }

    private void SendHotkey(IReadOnlyList<string> keys)
    {
        if (keys.Count == 0)
        {
            return;
        }

        var pressed = new List<ushort>(keys.Count);
        foreach (var key in keys)
        {
            if (TryGetVirtualKey(key, out var vk))
            {
                SendVirtualKey(vk, keyUp: false);
                pressed.Add(vk);
            }
            else if (!string.IsNullOrEmpty(key) && key.Length == 1)
            {
                SendUnicodeChar(key[0], keyUp: false);
            }
        }

        for (var i = pressed.Count - 1; i >= 0; i--)
        {
            SendVirtualKey(pressed[i], keyUp: true);
        }
    }

    private void MoveAbsolute(int x, int y)
    {
        var screenLeft = GetSystemMetrics(SmXvirtualscreen);
        var screenTop = GetSystemMetrics(SmYvirtualscreen);
        var screenWidth = Math.Max(1, GetSystemMetrics(SmCxvirtualscreen));
        var screenHeight = Math.Max(1, GetSystemMetrics(SmCyvirtualscreen));

        var normalizedX = (int)Math.Round((x - screenLeft) * 65535.0 / Math.Max(1, screenWidth - 1));
        var normalizedY = (int)Math.Round((y - screenTop) * 65535.0 / Math.Max(1, screenHeight - 1));

        SendMouseInput(MouseeventfMove | MouseeventfAbsolute | MouseeventfVirtualdesk, normalizedX, normalizedY, 0);
    }

    private void MoveRelative(int dx, int dy)
    {
        SendMouseInput(MouseeventfMove, dx, dy, 0);
    }

    private void Click(string buttonName, int count)
    {
        for (var i = 0; i < count; i++)
        {
            MouseDown(buttonName);
            MouseUp(buttonName);
        }
    }

    private void MouseDown(string buttonName)
    {
        var flags = GetMouseFlags(buttonName, out var mouseData);
        SendMouseInput(flags.down, 0, 0, mouseData);
    }

    private void MouseUp(string buttonName)
    {
        var flags = GetMouseFlags(buttonName, out var mouseData);
        SendMouseInput(flags.up, 0, 0, mouseData);
    }

    private void Scroll(int dx, int dy)
    {
        if (dy != 0)
        {
            SendMouseInput(MouseeventfWheel, 0, 0, dy * WheelDelta);
        }

        if (dx != 0)
        {
            SendMouseInput(MouseeventfHwheel, 0, 0, dx * WheelDelta);
        }
    }

    private static (uint down, uint up) GetMouseFlags(string buttonName, out int mouseData)
    {
        mouseData = 0;
        switch (buttonName.ToLowerInvariant())
        {
            case "right":
                return (MouseeventfRightdown, MouseeventfRightup);
            case "middle":
                return (MouseeventfMiddledown, MouseeventfMiddleup);
            case "x1":
                mouseData = 1;
                return (MouseeventfXdown, MouseeventfXup);
            case "x2":
                mouseData = 2;
                return (MouseeventfXdown, MouseeventfXup);
            default:
                return (MouseeventfLeftdown, MouseeventfLeftup);
        }
    }

    private void SendVirtualKey(ushort vk, bool keyUp)
    {
        var input = new INPUT
        {
            type = InputKeyboard,
            U = new InputUnion
            {
                ki = new KEYBDINPUT
                {
                    wVk = vk,
                    wScan = 0,
                    dwFlags = keyUp ? KeyeventfKeyup : 0,
                    time = 0,
                    dwExtraInfo = IntPtr.Zero
                }
            }
        };

        SendInput(1, new[] { input }, Marshal.SizeOf<INPUT>());
    }

    private void SendUnicodeChar(char character, bool keyUp)
    {
        var input = new INPUT
        {
            type = InputKeyboard,
            U = new InputUnion
            {
                ki = new KEYBDINPUT
                {
                    wVk = 0,
                    wScan = character,
                    dwFlags = KeyeventfUnicode | (keyUp ? KeyeventfKeyup : 0),
                    time = 0,
                    dwExtraInfo = IntPtr.Zero
                }
            }
        };

        SendInput(1, new[] { input }, Marshal.SizeOf<INPUT>());
    }

    private static void SendMouseInput(uint flags, int dx, int dy, int mouseData)
    {
        var input = new INPUT
        {
            type = InputMouse,
            U = new InputUnion
            {
                mi = new MOUSEINPUT
                {
                    dx = dx,
                    dy = dy,
                    mouseData = mouseData,
                    dwFlags = flags,
                    time = 0,
                    dwExtraInfo = IntPtr.Zero
                }
            }
        };

        SendInput(1, new[] { input }, Marshal.SizeOf<INPUT>());
    }

    private static bool TryGetVirtualKey(string? key, out ushort vk)
    {
        if (!string.IsNullOrWhiteSpace(key) && VirtualKeys.TryGetValue(key, out vk))
        {
            return true;
        }

        vk = 0;
        return false;
    }

    private static string GetString(JsonElement element, string propertyName, string fallback = "")
        => element.ValueKind == JsonValueKind.Object &&
           element.TryGetProperty(propertyName, out var prop) &&
           prop.ValueKind == JsonValueKind.String
            ? prop.GetString() ?? fallback
            : fallback;

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

    private static IReadOnlyList<string> ReadStringArray(JsonElement element, string propertyName)
    {
        if (element.ValueKind != JsonValueKind.Object ||
            !element.TryGetProperty(propertyName, out var array) ||
            array.ValueKind != JsonValueKind.Array)
        {
            return Array.Empty<string>();
        }

        var result = new List<string>();
        foreach (var item in array.EnumerateArray())
        {
            if (item.ValueKind == JsonValueKind.String)
            {
                result.Add(item.GetString() ?? string.Empty);
            }
        }

        return result;
    }

    [DllImport("user32.dll")]
    private static extern int SendInput(int nInputs, INPUT[] pInputs, int cbSize);

    [DllImport("user32.dll")]
    private static extern int GetSystemMetrics(int nIndex);

    [StructLayout(LayoutKind.Sequential)]
    private struct INPUT
    {
        public int type;
        public InputUnion U;
    }

    [StructLayout(LayoutKind.Explicit)]
    private struct InputUnion
    {
        [FieldOffset(0)]
        public MOUSEINPUT mi;

        [FieldOffset(0)]
        public KEYBDINPUT ki;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct MOUSEINPUT
    {
        public int dx;
        public int dy;
        public int mouseData;
        public uint dwFlags;
        public uint time;
        public IntPtr dwExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct KEYBDINPUT
    {
        public ushort wVk;
        public ushort wScan;
        public uint dwFlags;
        public uint time;
        public IntPtr dwExtraInfo;
    }
}
