using System.Security.Claims;
using CNews.Application.DTOs;
using CNews.Application.Services;
using Microsoft.AspNetCore.Mvc;

namespace CNews.Api.Endpoints;

public static class V1Endpoints
{
    public static IEndpointRouteBuilder MapV1(this IEndpointRouteBuilder app)
    {
        var v1 = app.MapGroup("/v1");

        v1.MapGet("/health", () => Results.Ok(new { status = "ok" }));

        v1.MapGet("/ads/display", async (
            DisplayAdService ads,
            [FromQuery] string? slot,
            [FromQuery] int? limit,
            CancellationToken ct) =>
        {
            _ = slot;
            var result = await ads.ListAsync(limit ?? 6, ct);
            return Results.Ok(result);
        });

        v1.MapGet("/meta/topics", () =>
        {
            var topics = Catalog.Topics.Select(t => new TopicDto(t, t)).ToArray();
            return Results.Ok(new TopicsResponseDto(topics));
        });

        v1.MapGet("/home/feed", async (
            [FromServices] NewsQueryService news,
            [FromQuery] string? topics,
            [FromQuery] int? limit,
            [FromQuery] string? cursor,
            [FromQuery] string? newerThan,
            [FromQuery] string? mode,
            ClaimsPrincipal user,
            CancellationToken ct) =>
        {
            try
            {
                DateTimeOffset? newer = null;
                if (!string.IsNullOrWhiteSpace(newerThan) && DateTimeOffset.TryParse(newerThan, out var parsed))
                {
                    newer = parsed;
                }

                var result = await news.GetFeedAsync(topics, limit ?? 20, cursor, newer, mode ?? "any", null, ct);
                return Results.Ok(result);
            }
            catch (ArgumentException ex) when (ex.Message.StartsWith("invalid_topic"))
            {
                return Results.BadRequest(new ErrorEnvelope(new ErrorBody("invalid_topic", ex.Message)));
            }
        });

        v1.MapGet("/stories/{storyId}", async (string storyId, NewsQueryService news, CancellationToken ct) =>
        {
            var detail = await news.GetStoryAsync(storyId, ct);
            return detail is null
                ? Results.NotFound(new ErrorEnvelope(new ErrorBody("not_found", "Story not found")))
                : Results.Ok(detail);
        });

        v1.MapGet("/stories/{storyId}/audio-url", async (string storyId, NewsQueryService news, CancellationToken ct) =>
        {
            var audio = await news.GetAudioUrlAsync(storyId, ct);
            return audio is null
                ? Results.NotFound(new ErrorEnvelope(new ErrorBody("not_found", "Audio not ready")))
                : Results.Ok(audio);
        });

        v1.MapGet("/coverage/{clusterId}", async (string clusterId, NewsQueryService news, CancellationToken ct) =>
        {
            var coverage = await news.GetCoverageAsync(clusterId, ct);
            return coverage is null
                ? Results.NotFound(new ErrorEnvelope(new ErrorBody("not_found", "Coverage not found")))
                : Results.Ok(coverage);
        });

        v1.MapGet("/storylines", async (
            NewsQueryService news,
            [FromQuery] string? status,
            [FromQuery] string? topics,
            [FromQuery] int? limit,
            [FromQuery] string? cursor,
            CancellationToken ct) =>
        {
            try
            {
                var list = await news.ListStorylinesAsync(status ?? "open", topics, limit ?? 20, cursor, ct);
                return Results.Ok(list);
            }
            catch (ArgumentException ex) when (ex.Message.StartsWith("invalid_topic"))
            {
                return Results.BadRequest(new ErrorEnvelope(new ErrorBody("invalid_topic", ex.Message)));
            }
        });

        v1.MapGet("/storylines/{threadId}", async (string threadId, NewsQueryService news, CancellationToken ct) =>
        {
            var detail = await news.GetStorylineAsync(threadId, ct);
            return detail is null
                ? Results.NotFound(new ErrorEnvelope(new ErrorBody("not_found", "Storyline not found")))
                : Results.Ok(detail);
        });

        v1.MapPost("/auth/google", async (GoogleAuthRequest body, AuthService auth, CancellationToken ct) =>
        {
            try
            {
                var result = await auth.SignInWithGoogleAsync(body.IdToken, ct);
                return Results.Ok(result);
            }
            catch (UnauthorizedAccessException)
            {
                return Results.Json(
                    new ErrorEnvelope(new ErrorBody("unauthorized", "Invalid Google token")),
                    statusCode: StatusCodes.Status401Unauthorized);
            }
        });

        v1.MapGet("/me", async (ClaimsPrincipal principal, AuthService auth, CancellationToken ct) =>
        {
            var userId = principal.FindFirstValue(ClaimTypes.NameIdentifier)
                ?? principal.FindFirstValue("sub");
            if (string.IsNullOrWhiteSpace(userId))
            {
                return Results.Json(
                    new ErrorEnvelope(new ErrorBody("unauthorized", "Login required")),
                    statusCode: StatusCodes.Status401Unauthorized);
            }

            var me = await auth.GetMeAsync(userId, ct);
            return me is null
                ? Results.NotFound(new ErrorEnvelope(new ErrorBody("not_found", "User not found")))
                : Results.Ok(me);
        }).RequireAuthorization();

        v1.MapPut("/me/topics", async (
            UpdateTopicsRequest body,
            ClaimsPrincipal principal,
            AuthService auth,
            CancellationToken ct) =>
        {
            var userId = principal.FindFirstValue(ClaimTypes.NameIdentifier)
                ?? principal.FindFirstValue("sub");
            if (string.IsNullOrWhiteSpace(userId))
            {
                return Results.Json(
                    new ErrorEnvelope(new ErrorBody("unauthorized", "Login required")),
                    statusCode: StatusCodes.Status401Unauthorized);
            }

            try
            {
                var me = await auth.UpdateTopicsAsync(userId, body.Topics, ct);
                return Results.Ok(me);
            }
            catch (ArgumentException ex)
            {
                return Results.BadRequest(new ErrorEnvelope(new ErrorBody("invalid_topic", ex.Message)));
            }
        }).RequireAuthorization();

        return app;
    }
}
