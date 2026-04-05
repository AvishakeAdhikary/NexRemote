using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Threading;
using System.Threading.Tasks;
using NexRemote.Helpers;

namespace NexRemote.Services;

public interface ICertificateService
{
    string CertificatePath { get; }
    string PrivateKeyPath { get; }
    Task EnsureCertificateAsync(CancellationToken cancellationToken = default);
    Task<string?> GetThumbprintAsync(CancellationToken cancellationToken = default);
    Task<string?> GetFingerprintAsync(CancellationToken cancellationToken = default);
}

public sealed class CertificateService : ICertificateService
{
    private readonly IAppSettingsService _settingsService;

    public CertificateService(IAppSettingsService settingsService)
    {
        _settingsService = settingsService;
    }

    public string CertificatePath => Path.Combine(PathHelper.GetCertificatesDirectory(), "server.crt");
    public string PrivateKeyPath => Path.Combine(PathHelper.GetCertificatesDirectory(), "server.key");

    public async Task EnsureCertificateAsync(CancellationToken cancellationToken = default)
    {
        if (!File.Exists(CertificatePath) || !File.Exists(PrivateKeyPath))
        {
            await Task.Run(() =>
            {
                using var rsa = RSA.Create(2048);
                var subject = new X500DistinguishedName("CN=localhost, O=Neural Nexus Studios, L=Local, S=CA, C=US");
                var request = new CertificateRequest(subject, rsa, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
                request.CertificateExtensions.Add(new X509BasicConstraintsExtension(false, false, 0, false));
                request.CertificateExtensions.Add(new X509KeyUsageExtension(X509KeyUsageFlags.DigitalSignature | X509KeyUsageFlags.KeyEncipherment, false));
                request.CertificateExtensions.Add(new X509SubjectKeyIdentifierExtension(request.PublicKey, false));
                request.CertificateExtensions.Add(new X509EnhancedKeyUsageExtension(
                    new OidCollection
                    {
                        new("1.3.6.1.5.5.7.3.1")
                    }, false));

                var notBefore = DateTimeOffset.UtcNow.AddDays(-1);
                var notAfter = DateTimeOffset.UtcNow.AddYears(10);
                using var cert = request.CreateSelfSigned(notBefore, notAfter);

                Directory.CreateDirectory(Path.GetDirectoryName(CertificatePath)!);
                File.WriteAllText(CertificatePath, cert.ExportCertificatePem());
                File.WriteAllText(PrivateKeyPath, rsa.ExportPkcs8PrivateKeyPem());
            }, cancellationToken).ConfigureAwait(false);
        }

        var thumbprint = await GetThumbprintAsync(cancellationToken).ConfigureAwait(false);
        if (!string.IsNullOrWhiteSpace(thumbprint) &&
            !string.Equals(_settingsService.Current.CertificateThumbprint, thumbprint, StringComparison.OrdinalIgnoreCase))
        {
            _settingsService.Update(settings => settings.CertificateThumbprint = thumbprint);
            await _settingsService.SaveAsync(cancellationToken).ConfigureAwait(false);
        }
    }

    public async Task<string?> GetThumbprintAsync(CancellationToken cancellationToken = default)
    {
        if (!File.Exists(CertificatePath))
        {
            return null;
        }

        return await Task.Run(() =>
        {
            using var cert = X509Certificate2.CreateFromPemFile(CertificatePath, PrivateKeyPath);
            return cert.Thumbprint;
        }, cancellationToken).ConfigureAwait(false);
    }

    public async Task<string?> GetFingerprintAsync(CancellationToken cancellationToken = default)
    {
        if (!File.Exists(CertificatePath))
        {
            return null;
        }

        return await Task.Run(() =>
        {
            using var cert = X509Certificate2.CreateFromPemFile(CertificatePath, PrivateKeyPath);
            var hash = SHA256.HashData(cert.RawData);
            return string.Join(":", hash.Select(static b => b.ToString("X2")));
        }, cancellationToken).ConfigureAwait(false);
    }
}
