using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace NexRemote.Models;

public sealed class AppSettings
{
    public const string CurrentTermsOfServiceVersion = "2026-04-05";
    public const string CurrentTermsAndConditionsVersion = "2026-04-05";
    public const string CurrentPrivacyPolicyVersion = "2026-04-05";
    public const int CurrentSchemaVersion = 1;

    public int SchemaVersion { get; set; } = CurrentSchemaVersion;
    public string PcName { get; set; } = Environment.MachineName;
    public string DeviceId { get; set; } = Guid.NewGuid().ToString();
    public int ServerPort { get; set; } = 8765;
    public int ServerPortInsecure { get; set; } = 8766;
    public int DiscoveryPort { get; set; } = 37020;
    public bool EnableRemoteAccess { get; set; } = true;
    public int MaxClients { get; set; } = 5;
    public string LogLevel { get; set; } = "Information";
    public bool AutoStart { get; set; } = false;
    public bool MinimizeToTray { get; set; } = true;
    public bool RequireApproval { get; set; } = true;
    public bool TermsAccepted { get; set; } = false;
    public DateTimeOffset? TermsAcceptedAt { get; set; }
    public bool TermsOfServiceAccepted { get; set; } = false;
    public DateTimeOffset? TermsOfServiceAcceptedAt { get; set; }
    public string? TermsOfServiceVersionAccepted { get; set; }
    public bool TermsAndConditionsAccepted { get; set; } = false;
    public DateTimeOffset? TermsAndConditionsAcceptedAt { get; set; }
    public string? TermsAndConditionsVersionAccepted { get; set; }
    public bool PrivacyPolicyAccepted { get; set; } = false;
    public DateTimeOffset? PrivacyPolicyAcceptedAt { get; set; }
    public string? PrivacyPolicyVersionAccepted { get; set; }
    public bool FirewallConfigured { get; set; } = false;
    public string FirewallProfile { get; set; } = "private";
    public ThemePreference ThemePreference { get; set; } = ThemePreference.System;
    public bool ShowNotifications { get; set; } = true;
    public bool AuditLogging { get; set; } = true;
    public bool InputValidation { get; set; } = true;
    public bool RemoteControlConsentGranted { get; set; } = false;
    public bool BackgroundConsentGranted { get; set; } = false;
    public bool CameraAccessConsentGranted { get; set; } = false;
    public DateTimeOffset? PrivacyPolicyReviewedAt { get; set; }
    public string? CertificateThumbprint { get; set; }

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? ExtensionData { get; set; }

    public static AppSettings CreateDefault() => new();
}
