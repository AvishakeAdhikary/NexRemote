using System;
using System.IO;
using System.Threading.Tasks;

namespace NexRemote.Services;

public enum LegalDocumentKind
{
    TermsOfService,
    TermsAndConditions,
    PrivacyPolicy
}

public interface ILegalDocumentService
{
    Task<string> LoadTermsOfServiceAsync();
    Task<string> LoadTermsAndConditionsAsync();
    Task<string> LoadPrivacyPolicyAsync();
}

public sealed class LegalDocumentService : ILegalDocumentService
{
    public Task<string> LoadTermsOfServiceAsync() => LoadAsync("TERMS_OF_SERVICE.md");

    public Task<string> LoadTermsAndConditionsAsync() => LoadAsync("TERMS_AND_CONDITIONS.md");

    public Task<string> LoadPrivacyPolicyAsync() => LoadAsync("PRIVACY_POLICY.md");

    private static async Task<string> LoadAsync(string fileName)
    {
        var path = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "Assets", "Legal", fileName));
        if (!File.Exists(path))
        {
            return $"{fileName} not found.";
        }

        return await File.ReadAllTextAsync(path).ConfigureAwait(false);
    }
}
