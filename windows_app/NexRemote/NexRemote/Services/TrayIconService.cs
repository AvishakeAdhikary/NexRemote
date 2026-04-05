using System;
using System.IO;
using System.Runtime.InteropServices;

namespace NexRemote.Services;

public interface ITrayIconService : IDisposable
{
    event EventHandler? ShowRequested;
    event EventHandler? ToggleServerRequested;
    event EventHandler? ExitRequested;

    void Initialize();
    void UpdateServerState(bool isRunning, string statusText);
    void ShowMessage(string title, string message);
}

public sealed class TrayIconService : ITrayIconService
{
    private const int ShowCommandId = 1001;
    private const int ToggleServerCommandId = 1002;
    private const int ExitCommandId = 1003;
    private const uint CallbackMessage = NativeMethods.WmApp + 1;

    private readonly NativeMethods.WindowProc _windowProc;
    private readonly object _sync = new();
    private IntPtr _windowHandle;
    private IntPtr _iconHandle;
    private bool _initialized;
    private bool _disposed;
    private bool _serverRunning;
    private string _statusText = "Server stopped";

    public event EventHandler? ShowRequested;
    public event EventHandler? ToggleServerRequested;
    public event EventHandler? ExitRequested;

    public TrayIconService()
    {
        _windowProc = WindowProcedure;
    }

    public void Initialize()
    {
        lock (_sync)
        {
            if (_initialized)
            {
                return;
            }

            _windowHandle = NativeMethods.CreateTrayWindow(_windowProc);
            if (_windowHandle == IntPtr.Zero)
            {
                throw new InvalidOperationException("Unable to create tray host window.");
            }

            _iconHandle = LoadTrayIcon();

            var data = CreateNotifyIconData(NativeMethods.NifMessage | NativeMethods.NifIcon | NativeMethods.NifTip);
            if (!NativeMethods.Shell_NotifyIcon(NativeMethods.NimAdd, ref data))
            {
                throw new InvalidOperationException("Unable to create tray icon.");
            }

            data.uTimeoutOrVersion = NativeMethods.NotifyIconVersion4;
            NativeMethods.Shell_NotifyIcon(NativeMethods.NimSetVersion, ref data);
            _initialized = true;
        }
    }

    public void UpdateServerState(bool isRunning, string statusText)
    {
        lock (_sync)
        {
            _serverRunning = isRunning;
            _statusText = string.IsNullOrWhiteSpace(statusText) ? "Server stopped" : statusText;
            if (!_initialized)
            {
                return;
            }

            var data = CreateNotifyIconData(NativeMethods.NifTip | NativeMethods.NifIcon);
            NativeMethods.Shell_NotifyIcon(NativeMethods.NimModify, ref data);
        }
    }

    public void ShowMessage(string title, string message)
    {
        lock (_sync)
        {
            if (!_initialized)
            {
                return;
            }

            var data = CreateNotifyIconData(NativeMethods.NifInfo);
            data.szInfoTitle = title ?? "NexRemote";
            data.szInfo = message ?? string.Empty;
            data.dwInfoFlags = NativeMethods.NiifInfo;
            NativeMethods.Shell_NotifyIcon(NativeMethods.NimModify, ref data);
        }
    }

    public void Dispose()
    {
        lock (_sync)
        {
            if (!_initialized || _disposed)
            {
                return;
            }

            _disposed = true;
            var data = CreateNotifyIconData(0);
            NativeMethods.Shell_NotifyIcon(NativeMethods.NimDelete, ref data);

            if (_windowHandle != IntPtr.Zero)
            {
                NativeMethods.DestroyWindow(_windowHandle);
                _windowHandle = IntPtr.Zero;
            }

            if (_iconHandle != IntPtr.Zero && _iconHandle != NativeMethods.StockApplicationIcon)
            {
                NativeMethods.DestroyIcon(_iconHandle);
                _iconHandle = IntPtr.Zero;
            }

            _initialized = false;
        }
    }

    private IntPtr WindowProcedure(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam)
    {
        if (msg == CallbackMessage)
        {
            var notification = unchecked((uint)(lParam.ToInt64() & 0xFFFF));
            switch (notification)
            {
                case NativeMethods.WmLbuttonUp:
                case NativeMethods.WmLbuttonDblClk:
                    ShowRequested?.Invoke(this, EventArgs.Empty);
                    return IntPtr.Zero;
                case NativeMethods.WmRbuttonUp:
                case NativeMethods.WmContextMenu:
                    ShowContextMenu(hWnd);
                    return IntPtr.Zero;
            }
        }

        return NativeMethods.DefWindowProc(hWnd, msg, wParam, lParam);
    }

    private void ShowContextMenu(IntPtr hWnd)
    {
        if (!NativeMethods.GetCursorPos(out var point))
        {
            return;
        }

        var menu = NativeMethods.CreatePopupMenu();
        if (menu == IntPtr.Zero)
        {
            return;
        }

        try
        {
            NativeMethods.AppendMenu(menu, NativeMethods.MfString, ShowCommandId, "Show");
            NativeMethods.AppendMenu(menu, NativeMethods.MfString, ToggleServerCommandId, _serverRunning ? "Stop Server" : "Start Server");
            NativeMethods.AppendMenu(menu, NativeMethods.MfSeparator, 0, null);
            NativeMethods.AppendMenu(menu, NativeMethods.MfString | NativeMethods.MfDisabled, 0, $"Status: {_statusText}");
            NativeMethods.AppendMenu(menu, NativeMethods.MfSeparator, 0, null);
            NativeMethods.AppendMenu(menu, NativeMethods.MfString, ExitCommandId, "Quit");

            NativeMethods.SetForegroundWindow(hWnd);
            var command = NativeMethods.TrackPopupMenuEx(
                menu,
                NativeMethods.TpmRightButton | NativeMethods.TpmReturndcmd,
                point.X,
                point.Y,
                hWnd,
                IntPtr.Zero);
            NativeMethods.PostMessage(hWnd, NativeMethods.WmNull, IntPtr.Zero, IntPtr.Zero);

            switch (command)
            {
                case ShowCommandId:
                    ShowRequested?.Invoke(this, EventArgs.Empty);
                    break;
                case ToggleServerCommandId:
                    ToggleServerRequested?.Invoke(this, EventArgs.Empty);
                    break;
                case ExitCommandId:
                    ExitRequested?.Invoke(this, EventArgs.Empty);
                    break;
            }
        }
        finally
        {
            NativeMethods.DestroyMenu(menu);
        }
    }

    private NativeMethods.NotifyIconData CreateNotifyIconData(uint flags)
    {
        return new NativeMethods.NotifyIconData
        {
            cbSize = (uint)Marshal.SizeOf<NativeMethods.NotifyIconData>(),
            hWnd = _windowHandle,
            uID = NativeMethods.TrayIconId,
            uFlags = flags,
            uCallbackMessage = CallbackMessage,
            hIcon = _iconHandle != IntPtr.Zero ? _iconHandle : NativeMethods.StockApplicationIcon,
            szTip = $"NexRemote{Environment.NewLine}{(_serverRunning ? "Server running" : "Server stopped")}",
            szInfo = string.Empty,
            szInfoTitle = string.Empty
        };
    }

    private static IntPtr LoadTrayIcon()
    {
        var icoPath = Path.Combine(AppContext.BaseDirectory, "Assets", "Brand", "logo.ico");
        if (File.Exists(icoPath))
        {
            var icon = NativeMethods.LoadIconFromFile(icoPath);
            if (icon != IntPtr.Zero)
            {
                return icon;
            }
        }

        return NativeMethods.StockApplicationIcon;
    }
}
