using CNews.Application.Abstractions;
using CNews.Application.DTOs;

namespace CNews.Application.Services;

public sealed class AuthService(
    IGoogleTokenValidator google,
    IUserRepository users,
    IJwtTokenService jwt)
{
    public async Task<AuthResponseDto> SignInWithGoogleAsync(string idToken, CancellationToken ct)
    {
        var identity = await google.ValidateAsync(idToken, ct)
            ?? throw new UnauthorizedAccessException("invalid_google_token");

        var user = await users.UpsertGoogleUserAsync(
            identity.Subject,
            identity.Email,
            identity.Name,
            identity.Picture,
            ct);

        var (token, expires) = jwt.Issue(user);
        return new AuthResponseDto(token, expires, ToDto(user));
    }

    public async Task<UserDto?> GetMeAsync(string userId, CancellationToken ct)
    {
        var user = await users.GetByIdAsync(userId, ct);
        return user is null ? null : ToDto(user);
    }

    public async Task<UserDto> UpdateTopicsAsync(string userId, IReadOnlyList<string> topics, CancellationToken ct)
    {
        var normalized = Catalog.ParseTopics(string.Join(',', topics));
        if (normalized.Count == 0)
        {
            throw new ArgumentException("invalid_topic:empty");
        }

        var user = await users.UpdateTopicsAsync(userId, normalized, ct);
        return ToDto(user);
    }

    private static UserDto ToDto(Domain.Entities.UserAccount user) =>
        new(user.UserId, user.Email, user.DisplayName, user.AvatarUrl, user.Topics);
}
