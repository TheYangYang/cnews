using CNews.Application.Abstractions;
using CNews.Domain.Entities;
using Microsoft.Extensions.Options;
using MongoDB.Bson;
using MongoDB.Driver;

namespace CNews.Infrastructure.Mongo;

public sealed class MongoIngestStatusRepository(IOptions<MongoOptions> options) : IIngestStatusRepository
{
    private readonly IMongoCollection<BsonDocument> _status =
        new MongoClient(options.Value.Uri).GetDatabase(options.Value.Database).GetCollection<BsonDocument>("ingest_status");

    public async Task<IngestStatus?> GetAsync(CancellationToken ct)
    {
        var doc = await _status.Find(Builders<BsonDocument>.Filter.Eq("_id", "ingest")).FirstOrDefaultAsync(ct);
        if (doc is null || !doc.Contains("lastSeenAt") || !doc["lastSeenAt"].IsValidDateTime)
        {
            return null;
        }

        return new IngestStatus
        {
            LastSeenAt = new DateTimeOffset(doc["lastSeenAt"].ToUniversalTime()),
            LastBriefAt = doc.Contains("lastBriefAt") && doc["lastBriefAt"].IsValidDateTime
                ? new DateTimeOffset(doc["lastBriefAt"].ToUniversalTime())
                : null,
            Backlog = doc.GetValue("backlog", 0).ToInt32(),
            Host = doc.GetValue("host", BsonNull.Value).IsBsonNull ? null : doc["host"].AsString,
            TtsStatus = doc.GetValue("ttsStatus", BsonNull.Value).IsBsonNull ? null : doc["ttsStatus"].AsString,
        };
    }
}
