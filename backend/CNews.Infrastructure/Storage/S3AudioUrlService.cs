using Amazon.S3;
using Amazon.S3.Model;
using CNews.Application.Abstractions;
using Microsoft.Extensions.Options;

namespace CNews.Infrastructure.Storage;

public sealed class S3Options
{
    public string Bucket { get; set; } = "cnews-audio";
    public string Region { get; set; } = "ca-central-1";
    public string? Endpoint { get; set; } = "http://127.0.0.1:9000";
    public string? AccessKey { get; set; } = "cnewsminio";
    public string? SecretKey { get; set; } = "cnewsminio";
    public bool ForcePathStyle { get; set; } = true;
    public int UrlTtlSeconds { get; set; } = 900;
    /// <summary>Used for local/media keys like local/demo-brief.mp3.</summary>
    public string? PublicBaseUrl { get; set; } = "http://127.0.0.1:5080";
}

public sealed class S3AudioUrlService : IAudioUrlService, IDisposable
{
    private readonly S3Options _options;
    private readonly IAmazonS3 _client;

    public S3AudioUrlService(IOptions<S3Options> options)
    {
        _options = options.Value;
        var config = new AmazonS3Config
        {
            RegionEndpoint = Amazon.RegionEndpoint.GetBySystemName(_options.Region),
            ForcePathStyle = _options.ForcePathStyle,
        };
        if (!string.IsNullOrWhiteSpace(_options.Endpoint))
        {
            config.ServiceURL = _options.Endpoint;
            config.AuthenticationRegion = _options.Region;
        }

        _client = string.IsNullOrWhiteSpace(_options.AccessKey)
            ? new AmazonS3Client(config)
            : new AmazonS3Client(_options.AccessKey, _options.SecretKey, config);
    }

    public Task<(string Url, DateTimeOffset ExpiresAt)?> CreateSignedUrlAsync(string? audioKey, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(audioKey))
        {
            return Task.FromResult<(string, DateTimeOffset)?>(null);
        }

        var expires = DateTimeOffset.UtcNow.AddSeconds(_options.UrlTtlSeconds);

        // Absolute URL stored in Mongo (rare) — pass through.
        if (audioKey.StartsWith("http://", StringComparison.OrdinalIgnoreCase)
            || audioKey.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult<(string, DateTimeOffset)?>((audioKey, expires));
        }

        // Local static files under wwwroot/media (dev / seed without MinIO).
        if (audioKey.StartsWith("local/", StringComparison.OrdinalIgnoreCase))
        {
            var baseUrl = (_options.PublicBaseUrl ?? "http://127.0.0.1:5080").TrimEnd('/');
            var file = audioKey["local/".Length..].TrimStart('/');
            return Task.FromResult<(string, DateTimeOffset)?>(($"{baseUrl}/media/{file}", expires));
        }

        var request = new GetPreSignedUrlRequest
        {
            BucketName = _options.Bucket,
            Key = audioKey,
            Expires = expires.UtcDateTime,
            Verb = HttpVerb.GET,
        };
        var url = _client.GetPreSignedURL(request);
        return Task.FromResult<(string, DateTimeOffset)?>((url, expires));
    }

    public void Dispose() => _client.Dispose();
}
