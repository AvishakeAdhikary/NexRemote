using System;
using System.IO;
using System.Threading.Tasks;
using Microsoft.UI.Xaml.Media.Imaging;
using NexRemote.Helpers;
using QRCoder;

namespace NexRemote.Services;

public interface IQrCodeService
{
    Task<BitmapImage?> CreateAsync(string payload);
}

public sealed class QrCodeService : IQrCodeService
{
    public async Task<BitmapImage?> CreateAsync(string payload)
    {
        if (string.IsNullOrWhiteSpace(payload))
        {
            return null;
        }

        using var generator = new QRCodeGenerator();
        using var data = generator.CreateQrCode(payload, QRCodeGenerator.ECCLevel.M);
        var png = new PngByteQRCode(data).GetGraphic(18);
        var cacheDir = Path.Combine(PathHelper.GetAppDataRoot(), "cache");
        Directory.CreateDirectory(cacheDir);
        var filePath = Path.Combine(cacheDir, "quick-connect-qr.png");
        await File.WriteAllBytesAsync(filePath, png);
        return new BitmapImage(new Uri(filePath, UriKind.Absolute));
    }
}
