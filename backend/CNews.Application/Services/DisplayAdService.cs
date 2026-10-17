using CNews.Application.Abstractions;
using CNews.Application.DTOs;

namespace CNews.Application.Services;

public sealed class DisplayAdService(IDisplayAdRepository ads, IAudioUrlService mediaUrls)
{
    public async Task<DisplayAdsResponseDto> ListAsync(int limit, CancellationToken ct)
    {
        limit = Math.Clamp(limit <= 0 ? 6 : limit, 1, 12);
        var rows = await ads.ListActiveAsync(limit, ct);
        var items = new List<DisplayAdDto>(rows.Count);
        foreach (var ad in rows)
        {
            string? imageUrl = null;
            if (!string.IsNullOrWhiteSpace(ad.ImageKey))
            {
                var signed = await mediaUrls.CreateSignedUrlAsync(ad.ImageKey, ct);
                imageUrl = signed?.Url;
            }

            items.Add(new DisplayAdDto(
                ad.AdId,
                ad.Advertiser,
                ad.Title,
                ad.ClickUrl,
                imageUrl,
                ad.ImageAspect));
        }

        return new DisplayAdsResponseDto(items);
    }
}
