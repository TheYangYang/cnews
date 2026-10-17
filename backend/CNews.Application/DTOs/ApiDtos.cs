namespace CNews.Application.DTOs;

public sealed record StoryCardDto(
    string StoryId,
    string Title,
    string Summary,
    string SummaryPreview,
    string? ImageUrl,
    double? ImageAspect,
    string Outlet,
    string Topic,
    string Place,
    DateTimeOffset PublishedAt,
    string SourceUrl,
    string AudioStatus,
    string? AudioUrl,
    int? AudioDurationMs,
    string? ClusterId,
    string? ThreadId);

public sealed record FeedResponseDto(IReadOnlyList<StoryCardDto> Items, string? NextCursor, DateTimeOffset ServerTime);

public sealed record SearchResponseDto(
    IReadOnlyList<StoryCardDto> Stories,
    IReadOnlyList<StorylineSummaryDto> Storylines,
    DateTimeOffset ServerTime);

public sealed record DisplayAdDto(
    string AdId,
    string Advertiser,
    string Title,
    string ClickUrl,
    string? ImageUrl,
    double? ImageAspect);

public sealed record DisplayAdsResponseDto(IReadOnlyList<DisplayAdDto> Items);

public sealed record StoryDetailDto(StoryCardDto Story, string? CompareClusterId, string? ThreadId);

public sealed record AudioUrlDto(string AudioUrl, DateTimeOffset ExpiresAt);

public sealed record CoverageOutletDto(
    string StoryId,
    string Outlet,
    string Framing,
    string Summary,
    string AudioStatus,
    string? AudioUrl,
    string? ImageUrl,
    string? SourceUrl = null,
    string? PublishedAt = null);

public sealed record CoverageDetailDto(
    string ClusterId,
    string Title,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<CoverageOutletDto> Outlets);

public sealed record StorylineSummaryDto(
    string ThreadId,
    string Title,
    string Status,
    DateTimeOffset UpdatedAt,
    int UpdateCount,
    string Topic,
    string Place,
    string? CoverImageUrl,
    string? LatestOutlet,
    string? LatestStoryId);

public sealed record StorylineListDto(IReadOnlyList<StorylineSummaryDto> Items, string? NextCursor);

public sealed record StorylineUpdateDto(
    string StoryId,
    DateTimeOffset At,
    string Outlet,
    string Summary,
    string? Title,
    string AudioStatus,
    string? AudioUrl,
    string? ImageUrl,
    string? SourceUrl);

public sealed record StorylineDetailDto(
    string ThreadId,
    string Title,
    string Status,
    string Topic,
    string Place,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<StorylineUpdateDto> Updates);

public sealed record TopicDto(string Id, string Label);

public sealed record TopicsResponseDto(IReadOnlyList<TopicDto> Topics);

public sealed record UserDto(
    string UserId,
    string Email,
    string DisplayName,
    string? AvatarUrl,
    IReadOnlyList<string> Topics);

public sealed record AuthResponseDto(string AccessToken, DateTimeOffset ExpiresAt, UserDto User);

public sealed record GoogleAuthRequest(string IdToken);

public sealed record UpdateTopicsRequest(IReadOnlyList<string> Topics);

public sealed record ErrorBody(string Code, string Message);

public sealed record ErrorEnvelope(ErrorBody Error);
