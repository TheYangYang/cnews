namespace CNews.Domain.Entities;

public sealed class Story
{
    public required string StoryId { get; init; }
    public string? ClusterId { get; init; }
    public string? ThreadId { get; init; }
    public required string Title { get; init; }
    public required string Summary { get; init; }
    public int SummaryWords { get; init; }
    public string? SummaryEngine { get; init; }
    public string? ImageUrl { get; init; }
    public double? ImageAspect { get; init; }
    public required string Outlet { get; init; }
    public required string Topic { get; init; }
    public required string Place { get; init; }
    public required string SourceUrl { get; init; }
    public DateTimeOffset PublishedAt { get; init; }
    public DateTimeOffset IngestedAt { get; init; }
    public required string AudioStatus { get; init; }
    public string? AudioKey { get; init; }
    public string? AudioContentType { get; init; }
    public int? AudioDurationMs { get; init; }
    public bool ListenReady { get; init; }
    public bool TextReady { get; init; }
}
