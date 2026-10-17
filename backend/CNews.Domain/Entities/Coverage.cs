namespace CNews.Domain.Entities;

public sealed class CoverageCluster
{
    public required string ClusterId { get; init; }
    public required string Title { get; init; }
    public IReadOnlyList<string> Topics { get; init; } = [];
    public DateTimeOffset UpdatedAt { get; init; }
    public IReadOnlyList<CoverageOutlet> Outlets { get; init; } = [];
}

public sealed class CoverageOutlet
{
    public required string StoryId { get; init; }
    public required string Outlet { get; init; }
    public required string Framing { get; init; }
    public required string Summary { get; init; }
    public required string AudioStatus { get; init; }
    public string? AudioKey { get; init; }
    public string? ImageUrl { get; init; }
    public string? SourceUrl { get; init; }
    public string? PublishedAt { get; init; }
}
