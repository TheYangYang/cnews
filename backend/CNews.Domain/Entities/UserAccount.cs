namespace CNews.Domain.Entities;

public sealed class UserAccount
{
    public required string UserId { get; init; }
    public required string GoogleSub { get; init; }
    public required string Email { get; init; }
    public required string DisplayName { get; init; }
    public string? AvatarUrl { get; init; }
    public IReadOnlyList<string> Topics { get; init; } = ["Top", "Canada", "Local"];
    public bool PreferListenReady { get; init; }
}
