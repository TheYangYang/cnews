using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using CNews.Application.Abstractions;
using CNews.Domain.Entities;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;

namespace CNews.Infrastructure.Auth;

public sealed class JwtOptions
{
    public string SigningKey { get; set; } = "dev-only-change-me-to-a-long-random-secret";
    public string Issuer { get; set; } = "cnews";
    public string Audience { get; set; } = "cnews-mobile";
    public int TtlMinutes { get; set; } = 60 * 24 * 7;
}

public sealed class JwtTokenService(IOptions<JwtOptions> options) : IJwtTokenService
{
    public (string Token, DateTimeOffset ExpiresAt) Issue(UserAccount user)
    {
        var opts = options.Value;
        var expires = DateTimeOffset.UtcNow.AddMinutes(opts.TtlMinutes);
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(opts.SigningKey));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);
        var token = new JwtSecurityToken(
            issuer: opts.Issuer,
            audience: opts.Audience,
            claims:
            [
                new Claim(JwtRegisteredClaimNames.Sub, user.UserId),
                new Claim(JwtRegisteredClaimNames.Email, user.Email),
                new Claim("name", user.DisplayName),
            ],
            expires: expires.UtcDateTime,
            signingCredentials: creds);
        return (new JwtSecurityTokenHandler().WriteToken(token), expires);
    }
}
