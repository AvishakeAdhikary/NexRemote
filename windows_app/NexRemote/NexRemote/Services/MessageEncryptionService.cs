using System;
using System.Security.Cryptography;
using System.Text;

namespace NexRemote.Services;

public interface IMessageEncryptionService
{
    string EncryptToBase64(string payload);
    byte[] EncryptToBase64Bytes(string payload);
    string DecryptFromBase64(string payload);
    string DecryptFromBase64Bytes(byte[] payload);
}

public sealed class MessageEncryptionService : IMessageEncryptionService
{
    private static readonly byte[] ZeroIv = new byte[16];
    private static readonly byte[] KeyBytes = CreateKeyBytes("nexremote_encryption_key_32chars");

    public string EncryptToBase64(string payload) => Encoding.UTF8.GetString(EncryptToBase64Bytes(payload));

    public byte[] EncryptToBase64Bytes(string payload)
    {
        var plainBytes = Encoding.UTF8.GetBytes(payload);
        using var aes = Aes.Create();
        aes.Key = KeyBytes;
        aes.IV = ZeroIv;
        aes.Mode = CipherMode.CBC;
        aes.Padding = PaddingMode.PKCS7;

        using var encryptor = aes.CreateEncryptor();
        var encrypted = encryptor.TransformFinalBlock(plainBytes, 0, plainBytes.Length);
        return Encoding.UTF8.GetBytes(Convert.ToBase64String(encrypted));
    }

    public string DecryptFromBase64(string payload)
    {
        var decoded = DecryptInternal(Convert.FromBase64String(payload));
        return Encoding.UTF8.GetString(decoded);
    }

    public string DecryptFromBase64Bytes(byte[] payload)
    {
        if (payload.Length == 0)
        {
            return string.Empty;
        }

        var text = Encoding.UTF8.GetString(payload).Trim();
        var decoded = IsBase64Text(payload)
            ? Convert.FromBase64String(text)
            : payload;

        return Encoding.UTF8.GetString(DecryptInternal(decoded));
    }

    private static byte[] DecryptInternal(byte[] encryptedBytes)
    {
        using var aes = Aes.Create();
        aes.Key = KeyBytes;
        aes.IV = ZeroIv;
        aes.Mode = CipherMode.CBC;
        aes.Padding = PaddingMode.PKCS7;

        using var decryptor = aes.CreateDecryptor();
        return decryptor.TransformFinalBlock(encryptedBytes, 0, encryptedBytes.Length);
    }

    private static byte[] CreateKeyBytes(string key)
    {
        var bytes = Encoding.UTF8.GetBytes(key);
        var result = new byte[32];
        Array.Copy(bytes, result, Math.Min(bytes.Length, result.Length));
        return result;
    }

    private static bool IsBase64Text(byte[] payload)
    {
        try
        {
            var text = Encoding.UTF8.GetString(payload).Trim();
            if (text.Length == 0 || text.Length % 4 != 0)
            {
                return false;
            }

            Convert.FromBase64String(text);
            return true;
        }
        catch
        {
            return false;
        }
    }
}
