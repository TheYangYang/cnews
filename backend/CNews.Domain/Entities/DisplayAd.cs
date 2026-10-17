namespace CNews.Domain.Entities;

public sealed class DisplayAd
{
    public required string AdId { get; init; }
    public required string Advertiser { get; init; }
    public required string Title { get; init; }
    public required string ClickUrl { get; init; }
    public string? ImageKey { get; init; }
    public double? ImageAspect { get; init; }
    public bool Active { get; init; } = true;
}
