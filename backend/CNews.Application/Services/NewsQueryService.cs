using CNews.Application.Abstractions;
using CNews.Application.DTOs;
using CNews.Domain.Entities;

namespace CNews.Application.Services;

public sealed class NewsQueryService(
    IStoryRepository stories,
    ICoverageRepository coverage,
    IStorylineRepository storylines,
    IAudioUrlService audioUrls)
{
    public async Task<FeedResponseDto> GetFeedAsync(
        string? topicsRaw,
        int limit,
        string? cursor,
        DateTimeOffset? newerThan,
        string mode,
        IReadOnlyList<string>? userTopics,
        CancellationToken ct)
    {
        limit = Math.Clamp(limit <= 0 ? 20 : limit, 1, 40);
        var topics = Catalog.ParseTopics(topicsRaw, userTopics ?? Catalog.DefaultTopics);
        var listenOnly = string.Equals(mode, "listen", StringComparison.OrdinalIgnoreCase);
        var (items, next) = await stories.GetFeedAsync(topics, limit, cursor, newerThan, listenOnly, ct);
        var cards = new List<StoryCardDto>(items.Count);
        foreach (var item in items)
        {
            cards.Add(await ToCardAsync(item, includeAudioUrl: false, ct));
        }

        return new FeedResponseDto(cards, next, DateTimeOffset.UtcNow);
    }

    public async Task<StoryDetailDto?> GetStoryAsync(string storyId, CancellationToken ct)
    {
        var story = await stories.GetByIdAsync(storyId, ct);
        if (story is null)
        {
            return null;
        }

        var card = await ToCardAsync(story, includeAudioUrl: true, ct);
        return new StoryDetailDto(card, story.ClusterId, story.ThreadId);
    }

    public async Task<AudioUrlDto?> GetAudioUrlAsync(string storyId, CancellationToken ct)
    {
        var story = await stories.GetByIdAsync(storyId, ct);
        if (story is null || story.AudioStatus != "ready" || string.IsNullOrWhiteSpace(story.AudioKey))
        {
            return null;
        }

        var signed = await audioUrls.CreateSignedUrlAsync(story.AudioKey, ct);
        return signed is null ? null : new AudioUrlDto(signed.Value.Url, signed.Value.ExpiresAt);
    }

    public async Task<CoverageDetailDto?> GetCoverageAsync(string clusterId, CancellationToken ct)
    {
        var cluster = await coverage.GetByIdAsync(clusterId, ct);
        if (cluster is null)
        {
            return null;
        }

        var outlets = new List<CoverageOutletDto>();
        foreach (var outlet in cluster.Outlets)
        {
            string? url = null;
            if (outlet.AudioStatus == "ready")
            {
                var signed = await audioUrls.CreateSignedUrlAsync(outlet.AudioKey, ct);
                url = signed?.Url;
            }

            outlets.Add(new CoverageOutletDto(
                outlet.StoryId,
                outlet.Outlet,
                outlet.Framing,
                outlet.Summary,
                outlet.AudioStatus,
                url,
                outlet.ImageUrl,
                outlet.SourceUrl,
                outlet.PublishedAt));
        }

        return new CoverageDetailDto(cluster.ClusterId, cluster.Title, cluster.UpdatedAt, outlets);
    }

    public async Task<StorylineListDto> ListStorylinesAsync(
        string status,
        string? topicsRaw,
        int limit,
        string? cursor,
        CancellationToken ct)
    {
        limit = Math.Clamp(limit <= 0 ? 20 : limit, 1, 40);
        IReadOnlyList<string>? topics = null;
        if (!string.IsNullOrWhiteSpace(topicsRaw))
        {
            topics = Catalog.ParseTopics(topicsRaw);
        }

        var (items, next) = await storylines.ListAsync(status, topics, limit, cursor, ct);
        var summaries = items.Select(t =>
        {
            var latest = t.Updates.OrderByDescending(u => u.At).FirstOrDefault();
            return new StorylineSummaryDto(
                t.ThreadId,
                t.Title,
                t.Status,
                t.UpdatedAt,
                t.Updates.Count,
                t.Topic,
                t.Place,
                latest?.ImageUrl,
                latest?.Outlet,
                latest?.StoryId);
        }).ToArray();
        return new StorylineListDto(summaries, next);
    }

    public async Task<StorylineDetailDto?> GetStorylineAsync(string threadId, CancellationToken ct)
    {
        var thread = await storylines.GetByIdAsync(threadId, ct);
        if (thread is null)
        {
            return null;
        }

        var updates = new List<StorylineUpdateDto>();
        foreach (var update in thread.Updates.OrderBy(u => u.At))
        {
            string? url = null;
            if (update.AudioStatus == "ready")
            {
                var signed = await audioUrls.CreateSignedUrlAsync(update.AudioKey, ct);
                url = signed?.Url;
            }

            updates.Add(new StorylineUpdateDto(
                update.StoryId,
                update.At,
                update.Outlet,
                update.Summary,
                update.Title,
                update.AudioStatus,
                url,
                update.ImageUrl,
                update.SourceUrl));
        }

        return new StorylineDetailDto(
            thread.ThreadId,
            thread.Title,
            thread.Status,
            thread.Topic,
            thread.Place,
            thread.UpdatedAt,
            updates);
    }

    private async Task<StoryCardDto> ToCardAsync(Story story, bool includeAudioUrl, CancellationToken ct)
    {
        string? audioUrl = null;
        if (includeAudioUrl && story.AudioStatus == "ready")
        {
            var signed = await audioUrls.CreateSignedUrlAsync(story.AudioKey, ct);
            audioUrl = signed?.Url;
        }

        return new StoryCardDto(
            story.StoryId,
            story.Title,
            story.Summary,
            Catalog.Preview(story.Summary),
            story.ImageUrl,
            story.ImageAspect,
            story.Outlet,
            story.Topic,
            story.Place,
            story.PublishedAt,
            story.SourceUrl,
            story.AudioStatus,
            audioUrl,
            story.AudioDurationMs,
            story.ClusterId,
            story.ThreadId);
    }
}
