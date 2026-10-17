using CNews.Domain.Entities;

namespace CNews.Application.Abstractions;

public interface IStoryRepository
{
    Task<(IReadOnlyList<Story> Items, string? NextCursor)> GetFeedAsync(
        IReadOnlyList<string> topics,
        int limit,
        string? cursor,
        DateTimeOffset? newerThan,
        bool listenOnly,
        CancellationToken ct);

    Task<Story?> GetByIdAsync(string storyId, CancellationToken ct);
}

public interface ICoverageRepository
{
    Task<CoverageCluster?> GetByIdAsync(string clusterId, CancellationToken ct);
}

public interface IStorylineRepository
{
    Task<(IReadOnlyList<Storyline> Items, string? NextCursor)> ListAsync(
        string status,
        IReadOnlyList<string>? topics,
        int limit,
        string? cursor,
        CancellationToken ct);

    Task<Storyline?> GetByIdAsync(string threadId, CancellationToken ct);
}

public interface IUserRepository
{
    Task<UserAccount> UpsertGoogleUserAsync(
        string googleSub,
        string email,
        string displayName,
        string? avatarUrl,
        CancellationToken ct);

    Task<UserAccount?> GetByIdAsync(string userId, CancellationToken ct);
    Task<UserAccount> UpdateTopicsAsync(string userId, IReadOnlyList<string> topics, CancellationToken ct);
}

public interface IDisplayAdRepository
{
    Task<IReadOnlyList<DisplayAd>> ListActiveAsync(string? slot, int limit, CancellationToken ct);
}

public interface IAudioUrlService
{
    Task<(string Url, DateTimeOffset ExpiresAt)?> CreateSignedUrlAsync(string? audioKey, CancellationToken ct);
}

public interface IGoogleTokenValidator
{
    Task<GoogleIdentity?> ValidateAsync(string idToken, CancellationToken ct);
}

public sealed record GoogleIdentity(string Subject, string Email, string Name, string? Picture);

public interface IJwtTokenService
{
    (string Token, DateTimeOffset ExpiresAt) Issue(UserAccount user);
}
