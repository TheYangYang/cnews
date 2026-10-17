namespace CNews.Domain.Entities;

public sealed class Storyline
{
    public required string ThreadId { get; init; }
    public required string Title { get; init; }
    public required string Status { get; init; }
    public required string Topic { get; init; }
    public required string Place { get; init; }
    public DateTimeOffset? OpenedAt { get; init; }
    public DateTimeOffset? ClosedAt { get; init; }
    public DateTimeOffset UpdatedAt { get; init; }
    public IReadOnlyList<StorylineUpdate> Updates { get; init; } = [];
}

public sealed class StorylineUpdate
{
    public required string StoryId { get; init; }
    public DateTimeOffset At { get; init; }
    public required string Outlet { get; init; }
    public required string Summary { get; init; }
    public string? Title { get; init; }
    public required string AudioStatus { get; init; }
    public string? AudioKey { get; init; }
    public string? ImageUrl { get; init; }
    public string? SourceUrl { get; init; }
}
