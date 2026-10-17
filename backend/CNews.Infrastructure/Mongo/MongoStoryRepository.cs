using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using CNews.Application.Abstractions;
using CNews.Domain.Entities;
using Microsoft.Extensions.Options;
using MongoDB.Bson;
using MongoDB.Driver;

namespace CNews.Infrastructure.Mongo;

public sealed class MongoOptions
{
    public string Uri { get; set; } = "mongodb://127.0.0.1:27017";
    public string Database { get; set; } = "cnews";
}

public sealed class MongoStoryRepository(IOptions<MongoOptions> options) : IStoryRepository
{
    private readonly IMongoCollection<BsonDocument> _stories =
        new MongoClient(options.Value.Uri).GetDatabase(options.Value.Database).GetCollection<BsonDocument>("stories");

    public async Task<(IReadOnlyList<Story> Items, string? NextCursor)> GetFeedAsync(
        IReadOnlyList<string> topics,
        int limit,
        string? cursor,
        DateTimeOffset? newerThan,
        bool listenOnly,
        CancellationToken ct)
    {
        var filter = Builders<BsonDocument>.Filter.And(
            Builders<BsonDocument>.Filter.Eq("textReady", true),
            Builders<BsonDocument>.Filter.In("topic", topics));

        if (listenOnly)
        {
            filter &= Builders<BsonDocument>.Filter.Eq("listenReady", true);
        }

        if (newerThan is not null)
        {
            filter &= Builders<BsonDocument>.Filter.Gt("publishedAt", newerThan.Value.UtcDateTime);
        }

        if (!string.IsNullOrWhiteSpace(cursor) && TryDecodeCursor(cursor, out var cursorTime, out var cursorId))
        {
            filter &= Builders<BsonDocument>.Filter.Or(
                Builders<BsonDocument>.Filter.Lt("publishedAt", cursorTime),
                Builders<BsonDocument>.Filter.And(
                    Builders<BsonDocument>.Filter.Eq("publishedAt", cursorTime),
                    Builders<BsonDocument>.Filter.Lt("storyId", cursorId)));
        }

        var docs = await _stories.Find(filter)
            .Sort(Builders<BsonDocument>.Sort.Descending("publishedAt").Descending("storyId"))
            .Limit(limit)
            .ToListAsync(ct);

        var items = docs.Select(MapStory).ToArray();
        string? next = null;
        if (items.Length == limit)
        {
            var last = items[^1];
            next = EncodeCursor(last.PublishedAt.UtcDateTime, last.StoryId);
        }

        return (items, next);
    }

    public async Task<Story?> GetByIdAsync(string storyId, CancellationToken ct)
    {
        var doc = await _stories.Find(Builders<BsonDocument>.Filter.Eq("storyId", storyId)).FirstOrDefaultAsync(ct);
        return doc is null ? null : MapStory(doc);
    }

    public async Task<IReadOnlyList<Story>> SearchAsync(string query, bool listenOnly, int limit, CancellationToken ct)
    {
        var take = Math.Clamp(limit, 1, 40);
        var regex = new BsonRegularExpression(Regex.Escape(query), "i");
        var text = Builders<BsonDocument>.Filter.Or(
            Builders<BsonDocument>.Filter.Regex("title", regex),
            Builders<BsonDocument>.Filter.Regex("summary", regex),
            Builders<BsonDocument>.Filter.Regex("outlet", regex),
            Builders<BsonDocument>.Filter.Regex("topic", regex),
            Builders<BsonDocument>.Filter.Regex("place", regex));

        var filter = Builders<BsonDocument>.Filter.And(
            Builders<BsonDocument>.Filter.Eq("textReady", true),
            text);

        if (listenOnly)
        {
            filter &= Builders<BsonDocument>.Filter.Eq("listenReady", true);
        }

        var docs = await _stories.Find(filter)
            .Sort(Builders<BsonDocument>.Sort.Descending("publishedAt").Descending("storyId"))
            .Limit(take)
            .ToListAsync(ct);

        return docs.Select(MapStory).ToArray();
    }

    internal static Story MapStory(BsonDocument doc) => new()
    {
        StoryId = doc.GetValue("storyId").AsString,
        ClusterId = doc.GetValue("clusterId", BsonNull.Value).IsBsonNull ? null : doc["clusterId"].AsString,
        ThreadId = doc.GetValue("threadId", BsonNull.Value).IsBsonNull ? null : doc["threadId"].AsString,
        Title = doc.GetValue("title", "").AsString,
        Summary = doc.GetValue("summary", "").AsString,
        SummaryWords = doc.GetValue("summaryWords", 0).ToInt32(),
        SummaryEngine = doc.GetValue("summaryEngine", BsonNull.Value).IsBsonNull ? null : doc["summaryEngine"].AsString,
        ImageUrl = doc.GetValue("imageUrl", BsonNull.Value).IsBsonNull ? null : doc["imageUrl"].AsString,
        ImageAspect = doc.GetValue("imageAspect", BsonNull.Value).IsBsonNull ? null : doc["imageAspect"].ToDouble(),
        Outlet = doc.GetValue("outlet", "").AsString,
        Topic = doc.GetValue("topic", "Top").AsString,
        Place = doc.GetValue("place", "Canada").AsString,
        SourceUrl = doc.GetValue("sourceUrl", "").AsString,
        PublishedAt = AsDto(doc.GetValue("publishedAt", BsonNull.Value)),
        IngestedAt = AsDto(doc.GetValue("ingestedAt", BsonNull.Value)),
        AudioStatus = doc.GetValue("audioStatus", "pending").AsString,
        AudioKey = doc.GetValue("audioKey", BsonNull.Value).IsBsonNull ? null : doc["audioKey"].AsString,
        AudioContentType = doc.GetValue("audioContentType", BsonNull.Value).IsBsonNull ? null : doc["audioContentType"].AsString,
        AudioDurationMs = doc.GetValue("audioDurationMs", BsonNull.Value).IsBsonNull ? null : doc["audioDurationMs"].ToInt32(),
        ListenReady = doc.GetValue("listenReady", false).ToBoolean(),
        TextReady = doc.GetValue("textReady", true).ToBoolean(),
    };

    private static DateTimeOffset AsDto(BsonValue value)
    {
        if (value.IsBsonNull)
        {
            return DateTimeOffset.UtcNow;
        }

        if (value.IsValidDateTime)
        {
            return new DateTimeOffset(value.ToUniversalTime());
        }

        if (value.IsString && DateTimeOffset.TryParse(value.AsString, out var parsed))
        {
            return parsed.ToUniversalTime();
        }

        return DateTimeOffset.UtcNow;
    }

    private static string EncodeCursor(DateTime publishedAt, string storyId)
    {
        var payload = JsonSerializer.Serialize(new { t = publishedAt.ToUniversalTime(), id = storyId });
        return Convert.ToBase64String(Encoding.UTF8.GetBytes(payload));
    }

    private static bool TryDecodeCursor(string cursor, out DateTime publishedAt, out string storyId)
    {
        publishedAt = default;
        storyId = "";
        try
        {
            var json = Encoding.UTF8.GetString(Convert.FromBase64String(cursor));
            using var doc = JsonDocument.Parse(json);
            publishedAt = doc.RootElement.GetProperty("t").GetDateTime().ToUniversalTime();
            storyId = doc.RootElement.GetProperty("id").GetString() ?? "";
            return !string.IsNullOrWhiteSpace(storyId);
        }
        catch
        {
            return false;
        }
    }
}
