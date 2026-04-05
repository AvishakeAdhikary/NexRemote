using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;

namespace NexRemote.Services;

internal sealed class ScreenCaptureService
{
    public sealed record ScreenDisplayInfo(int Index, string Name, int Width, int Height, bool IsPrimary, Rectangle Bounds);

    public IReadOnlyList<ScreenDisplayInfo> GetMonitors()
    {
        var result = new List<ScreenDisplayInfo>();
        EnumDisplayMonitors(IntPtr.Zero, IntPtr.Zero, (monitor, _, _, lParam) =>
        {
            var index = result.Count;
            var info = new MonitorInfoEx { Size = (uint)Marshal.SizeOf<MonitorInfoEx>() };
            if (GetMonitorInfo(monitor, ref info))
            {
                var bounds = Rectangle.FromLTRB(info.Monitor.Left, info.Monitor.Top, info.Monitor.Right, info.Monitor.Bottom);
                var name = string.IsNullOrWhiteSpace(info.DeviceName) ? $"Display {index + 1}" : info.DeviceName;
                result.Add(new ScreenDisplayInfo(index, name, bounds.Width, bounds.Height, info.Flags == 1, bounds));
            }

            return true;
        }, IntPtr.Zero);

        if (result.Count == 0)
        {
            result.Add(new ScreenDisplayInfo(0, "Primary Display", 1920, 1080, true, new Rectangle(0, 0, 1920, 1080)));
        }

        return result;
    }

    public byte[] CaptureFrame(ScreenDisplayInfo monitor, string resolution, int quality)
    {
        var bounds = monitor.Bounds;
        var targetSize = GetTargetSize(bounds.Size, resolution);
        using var sourceBitmap = new Bitmap(bounds.Width, bounds.Height, PixelFormat.Format24bppRgb);
        using (var graphics = Graphics.FromImage(sourceBitmap))
        {
            graphics.CopyFromScreen(bounds.Left, bounds.Top, 0, 0, bounds.Size, CopyPixelOperation.SourceCopy);
            if (targetSize != bounds.Size)
            {
                using var resized = new Bitmap(targetSize.Width, targetSize.Height, PixelFormat.Format24bppRgb);
                using var resizedGraphics = Graphics.FromImage(resized);
                resizedGraphics.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                resizedGraphics.DrawImage(sourceBitmap, 0, 0, targetSize.Width, targetSize.Height);
                return EncodeJpeg(resized, quality);
            }
        }

        return EncodeJpeg(sourceBitmap, quality);
    }

    private static Size GetTargetSize(Size source, string resolution)
    {
        if (string.IsNullOrWhiteSpace(resolution) || resolution.Equals("native", StringComparison.OrdinalIgnoreCase))
        {
            return source;
        }

        if (resolution.Equals("half", StringComparison.OrdinalIgnoreCase))
        {
            return new Size(Math.Max(1, source.Width / 2), Math.Max(1, source.Height / 2));
        }

        if (resolution.Equals("720p", StringComparison.OrdinalIgnoreCase))
        {
            return FitWithin(source, 1280, 720);
        }

        if (resolution.Equals("1080p", StringComparison.OrdinalIgnoreCase))
        {
            return FitWithin(source, 1920, 1080);
        }

        if (TryParseResolution(resolution, out var width, out var height))
        {
            return FitWithin(source, width, height);
        }

        return source;
    }

    private static bool TryParseResolution(string resolution, out int width, out int height)
    {
        width = 0;
        height = 0;

        var separator = resolution.IndexOf('x', StringComparison.OrdinalIgnoreCase);
        if (separator <= 0 || separator >= resolution.Length - 1)
        {
            return false;
        }

        return int.TryParse(resolution[..separator], out width) &&
               int.TryParse(resolution[(separator + 1)..], out height) &&
               width > 0 &&
               height > 0;
    }

    private static Size FitWithin(Size source, int maxWidth, int maxHeight)
    {
        if (source.Width <= 0 || source.Height <= 0)
        {
            return new Size(maxWidth, maxHeight);
        }

        var widthScale = maxWidth / (double)source.Width;
        var heightScale = maxHeight / (double)source.Height;
        var scale = Math.Min(1.0, Math.Min(widthScale, heightScale));

        return new Size(
            Math.Max(1, (int)Math.Round(source.Width * scale)),
            Math.Max(1, (int)Math.Round(source.Height * scale)));
    }

    private static byte[] EncodeJpeg(Bitmap bitmap, int quality)
    {
        using var stream = new MemoryStream();
        var encoder = ImageCodecInfo.GetImageEncoders().FirstOrDefault(codec => codec.FormatID == ImageFormat.Jpeg.Guid);
        if (encoder is null)
        {
            bitmap.Save(stream, ImageFormat.Jpeg);
            return stream.ToArray();
        }

        using var parameters = new EncoderParameters(1);
        parameters.Param[0] = new EncoderParameter(Encoder.Quality, Math.Clamp(quality, 1, 100));
        bitmap.Save(stream, encoder, parameters);
        return stream.ToArray();
    }

    [DllImport("user32.dll")]
    private static extern bool EnumDisplayMonitors(IntPtr hdc, IntPtr lprcClip, MonitorEnumProc lpfnEnum, IntPtr dwData);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern bool GetMonitorInfo(IntPtr hMonitor, ref MonitorInfoEx lpmi);

    private delegate bool MonitorEnumProc(IntPtr hMonitor, IntPtr hdc, IntPtr lprcMonitor, IntPtr dwData);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct MonitorInfoEx
    {
        public uint Size;
        public Rect Monitor;
        public Rect Work;
        public uint Flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
        public string DeviceName;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct Rect
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
}
