using System;
using System.ComponentModel;
using System.Runtime.InteropServices;

namespace NexRemote.Services;

internal static class NativeMethods
{
    public const uint WmNull = 0x0000;
    public const uint WmDestroy = 0x0002;
    public const uint WmContextMenu = 0x007B;
    public const uint WmLbuttonUp = 0x0202;
    public const uint WmLbuttonDblClk = 0x0203;
    public const uint WmRbuttonUp = 0x0205;
    public const uint WmApp = 0x8000;

    public const uint NimAdd = 0x00000000;
    public const uint NimModify = 0x00000001;
    public const uint NimDelete = 0x00000002;
    public const uint NimSetVersion = 0x00000004;

    public const uint NifMessage = 0x00000001;
    public const uint NifIcon = 0x00000002;
    public const uint NifTip = 0x00000004;
    public const uint NifInfo = 0x00000010;

    public const uint NiifInfo = 0x00000001;

    public const uint MfString = 0x0000;
    public const uint MfGrayed = 0x0001;
    public const uint MfDisabled = 0x0002;
    public const uint MfSeparator = 0x0800;

    public const uint TpmRightButton = 0x0002;
    public const uint TpmReturndcmd = 0x0100;

    public const uint NotifyIconVersion4 = 4;
    public const int TrayIconId = 1;

    public static readonly IntPtr StockApplicationIcon = LoadStockApplicationIcon();

    private const int ImageIcon = 1;
    private const uint LrLoadFromFile = 0x0010;
    private const uint LrDefaultSize = 0x0040;
    private const uint WsPopup = 0x80000000;
    private const uint WsExToolWindow = 0x00000080;
    private const string TrayWindowClassName = "NexRemoteTrayWindow";

    public delegate IntPtr WindowProc(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct NotifyIconData
    {
        public uint cbSize;
        public IntPtr hWnd;
        public uint uID;
        public uint uFlags;
        public uint uCallbackMessage;
        public IntPtr hIcon;

        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
        public string szTip;

        public uint dwState;
        public uint dwStateMask;

        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)]
        public string szInfo;

        public uint uTimeoutOrVersion;

        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)]
        public string szInfoTitle;

        public uint dwInfoFlags;
        public Guid guidItem;
        public IntPtr hBalloonIcon;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct Point
    {
        public int X;
        public int Y;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct WndClassEx
    {
        public uint cbSize;
        public uint style;
        public IntPtr lpfnWndProc;
        public int cbClsExtra;
        public int cbWndExtra;
        public IntPtr hInstance;
        public IntPtr hIcon;
        public IntPtr hCursor;
        public IntPtr hbrBackground;
        [MarshalAs(UnmanagedType.LPWStr)]
        public string? lpszMenuName;
        [MarshalAs(UnmanagedType.LPWStr)]
        public string lpszClassName;
        public IntPtr hIconSm;
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool Shell_NotifyIcon(uint dwMessage, ref NotifyIconData lpData);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern IntPtr CreatePopupMenu();

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool AppendMenu(IntPtr hMenu, uint uFlags, int uIDNewItem, string? lpNewItem);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool DestroyMenu(IntPtr hMenu);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool GetCursorPos(out Point lpPoint);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern uint TrackPopupMenuEx(IntPtr hMenu, uint uFlags, int x, int y, IntPtr hWnd, IntPtr lptpm);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr DefWindowProc(IntPtr hWnd, uint uMsg, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool DestroyWindow(IntPtr hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool DestroyIcon(IntPtr hIcon);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern ushort RegisterClassEx(ref WndClassEx lpwcx);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateWindowEx(
        uint dwExStyle,
        string lpClassName,
        string lpWindowName,
        uint dwStyle,
        int X,
        int Y,
        int nWidth,
        int nHeight,
        IntPtr hWndParent,
        IntPtr hMenu,
        IntPtr hInstance,
        IntPtr lpParam);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr GetModuleHandle(string? lpModuleName);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr LoadImage(IntPtr hInst, string lpszName, uint uType, int cxDesired, int cyDesired, uint fuLoad);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr LoadIcon(IntPtr hInstance, IntPtr lpIconName);

    [DllImport("user32.dll")]
    public static extern void PostQuitMessage(int nExitCode);

    public static IntPtr CreateTrayWindow(WindowProc wndProc)
    {
        var hInstance = GetModuleHandle(null);
        var className = TrayWindowClassName;

        var wndClass = new WndClassEx
        {
            cbSize = (uint)Marshal.SizeOf<WndClassEx>(),
            lpfnWndProc = Marshal.GetFunctionPointerForDelegate(wndProc),
            hInstance = hInstance,
            lpszClassName = className
        };

        if (RegisterClassEx(ref wndClass) == 0)
        {
            var error = Marshal.GetLastWin32Error();
            if (error != 1410)
            {
                throw new Win32Exception(error, "Unable to register tray window class.");
            }
        }

        return CreateWindowEx(
            WsExToolWindow,
            className,
            string.Empty,
            WsPopup,
            0,
            0,
            0,
            0,
            IntPtr.Zero,
            IntPtr.Zero,
            hInstance,
            IntPtr.Zero);
    }

    public static IntPtr LoadIconFromFile(string path)
    {
        return LoadImage(IntPtr.Zero, path, ImageIcon, 0, 0, LrLoadFromFile | LrDefaultSize);
    }

    private static IntPtr LoadStockApplicationIcon()
    {
        return LoadIcon(IntPtr.Zero, new IntPtr(32512));
    }
}
