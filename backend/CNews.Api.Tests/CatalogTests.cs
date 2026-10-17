using CNews.Application.Services;

namespace CNews.Api.Tests;

public class CatalogTests
{
    [Fact]
    public void ParseTopics_defaults_when_empty()
    {
        var topics = Catalog.ParseTopics(null);
        Assert.Equal(Catalog.DefaultTopics, topics);
    }

    [Fact]
    public void ParseTopics_rejects_unknown()
    {
        var ex = Assert.Throws<ArgumentException>(() => Catalog.ParseTopics("Canada,Nope"));
        Assert.Contains("invalid_topic", ex.Message);
    }

    [Fact]
    public void Preview_adds_ellipsis()
    {
        var text = new string('a', 200);
        var preview = Catalog.Preview(text, 50);
        Assert.EndsWith("…", preview);
        Assert.True(preview.Length <= 50);
    }

    [Fact]
    public void SearchQuery_requires_two_characters()
    {
        Assert.Null(SearchQuery.Normalize(" "));
        Assert.Null(SearchQuery.Normalize("c"));
        Assert.Equal("CBC", SearchQuery.Normalize("  CBC  "));
    }
}
