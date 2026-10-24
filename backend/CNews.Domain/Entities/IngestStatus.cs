namespace CNews.Domain.Entities;

/// <summary>Heartbeat the ingest box writes to Mongo (`ingest_status`) every minute.</summary>
public sealed class IngestStatus
{
    public required DateTimeOffset LastSeenAt { get; init; }
    public DateTimeOffset? LastBriefAt { get; init; }
    public int Backlog { get; init; }
    public string? Host { get; init; }
    public string? TtsStatus { get; init; }
}
