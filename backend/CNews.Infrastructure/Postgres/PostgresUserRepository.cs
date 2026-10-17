using CNews.Application.Abstractions;
using CNews.Domain.Entities;
using Microsoft.Extensions.Options;
using Npgsql;

namespace CNews.Infrastructure.Postgres;

public sealed class PostgresOptions
{
    public string ConnectionString { get; set; } =
        "Host=127.0.0.1;Port=5432;Database=cnews;Username=cnews;Password=cnews";
}

public sealed class PostgresUserRepository(IOptions<PostgresOptions> options) : IUserRepository
{
    public async Task<UserAccount> UpsertGoogleUserAsync(
        string googleSub,
        string email,
        string displayName,
        string? avatarUrl,
        CancellationToken ct)
    {
        await using var conn = new NpgsqlConnection(options.Value.ConnectionString);
        await conn.OpenAsync(ct);

        await using (var find = new NpgsqlCommand(
            "SELECT user_id FROM users WHERE google_sub = @sub LIMIT 1", conn))
        {
            find.Parameters.AddWithValue("sub", googleSub);
            var existing = await find.ExecuteScalarAsync(ct) as string;
            if (existing is null)
            {
                var userId = $"user_{Guid.NewGuid():N}";
                await using var insert = new NpgsqlCommand(
                    """
                    INSERT INTO users (user_id, google_sub, email, display_name, avatar_url)
                    VALUES (@id, @sub, @email, @name, @avatar);
                    INSERT INTO user_preferences (user_id, topics)
                    VALUES (@id, ARRAY['Top','Canada','Local']);
                    """, conn);
                insert.Parameters.AddWithValue("id", userId);
                insert.Parameters.AddWithValue("sub", googleSub);
                insert.Parameters.AddWithValue("email", email);
                insert.Parameters.AddWithValue("name", displayName);
                insert.Parameters.AddWithValue("avatar", (object?)avatarUrl ?? DBNull.Value);
                await insert.ExecuteNonQueryAsync(ct);
                return (await GetByIdAsync(userId, ct))!;
            }

            await using var update = new NpgsqlCommand(
                """
                UPDATE users
                SET email = @email,
                    display_name = @name,
                    avatar_url = @avatar,
                    updated_at = NOW(),
                    last_login_at = NOW()
                WHERE google_sub = @sub
                """, conn);
            update.Parameters.AddWithValue("email", email);
            update.Parameters.AddWithValue("name", displayName);
            update.Parameters.AddWithValue("avatar", (object?)avatarUrl ?? DBNull.Value);
            update.Parameters.AddWithValue("sub", googleSub);
            await update.ExecuteNonQueryAsync(ct);
            return (await GetByIdAsync(existing, ct))!;
        }
    }

    public async Task<UserAccount?> GetByIdAsync(string userId, CancellationToken ct)
    {
        await using var conn = new NpgsqlConnection(options.Value.ConnectionString);
        await conn.OpenAsync(ct);
        await using var cmd = new NpgsqlCommand(
            """
            SELECT u.user_id, u.google_sub, u.email, u.display_name, u.avatar_url,
                   COALESCE(p.topics, ARRAY['Top','Canada','Local']) AS topics,
                   COALESCE(p.prefer_listen_ready, FALSE) AS prefer_listen_ready
            FROM users u
            LEFT JOIN user_preferences p ON p.user_id = u.user_id
            WHERE u.user_id = @id
            LIMIT 1
            """, conn);
        cmd.Parameters.AddWithValue("id", userId);
        await using var reader = await cmd.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct))
        {
            return null;
        }

        var topics = reader["topics"] as string[] ?? ["Top", "Canada", "Local"];
        return new UserAccount
        {
            UserId = reader.GetString(0),
            GoogleSub = reader.GetString(1),
            Email = reader.GetString(2),
            DisplayName = reader.GetString(3),
            AvatarUrl = reader.IsDBNull(4) ? null : reader.GetString(4),
            Topics = topics,
            PreferListenReady = reader.GetBoolean(6),
        };
    }

    public async Task<UserAccount> UpdateTopicsAsync(string userId, IReadOnlyList<string> topics, CancellationToken ct)
    {
        await using var conn = new NpgsqlConnection(options.Value.ConnectionString);
        await conn.OpenAsync(ct);
        await using var cmd = new NpgsqlCommand(
            """
            INSERT INTO user_preferences (user_id, topics, updated_at)
            VALUES (@id, @topics, NOW())
            ON CONFLICT (user_id) DO UPDATE
            SET topics = EXCLUDED.topics, updated_at = NOW()
            """, conn);
        cmd.Parameters.AddWithValue("id", userId);
        cmd.Parameters.AddWithValue("topics", topics.ToArray());
        await cmd.ExecuteNonQueryAsync(ct);
        return (await GetByIdAsync(userId, ct))!;
    }
}
