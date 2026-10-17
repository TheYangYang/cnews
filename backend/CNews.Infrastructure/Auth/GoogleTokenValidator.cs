using CNews.Application.Abstractions;
using Google.Apis.Auth;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace CNews.Infrastructure.Auth;

public sealed class GoogleAuthOptions
{
    /// <summary>Comma-separated OAuth client IDs (iOS/Android/Expo/Web).</summary>
    public string ClientIds { get; set; } = "";
    public bool AllowDevBypass { get; set; } = true;
}

public sealed class GoogleTokenValidator(
    IOptions<GoogleAuthOptions> options,
    ILogger<GoogleTokenValidator> logger) : IGoogleTokenValidator
{
    public async Task<GoogleIdentity?> ValidateAsync(string idToken, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(idToken))
        {
            return null;
        }

        // Local/dev convenience: "dev:<email>" when AllowDevBypass is on.
        if (options.Value.AllowDevBypass && idToken.StartsWith("dev:", StringComparison.OrdinalIgnoreCase))
        {
            var email = idToken[4..].Trim();
            if (string.IsNullOrWhiteSpace(email))
            {
                email = "dev@cnews.local";
            }

            return new GoogleIdentity($"dev-{email}", email, email.Split('@')[0], null);
        }

        try
        {
            var audiences = options.Value.ClientIds
                .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            var settings = new GoogleJsonWebSignature.ValidationSettings();
            if (audiences.Length > 0)
            {
                settings.Audience = audiences;
            }

            var payload = await GoogleJsonWebSignature.ValidateAsync(idToken, settings);
            return new GoogleIdentity(
                payload.Subject,
                payload.Email ?? $"{payload.Subject}@users.noreply.google.com",
                payload.Name ?? payload.Email ?? "Reader",
                payload.Picture);
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Google token validation failed");
            return null;
        }
    }
}
