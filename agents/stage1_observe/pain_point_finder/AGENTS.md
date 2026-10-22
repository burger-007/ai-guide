# Instructions: Pain Point Finder

## Mission
Continuously scan online communities to discover recurring user pain points that can be solved by a free web tool.

## Operating Rules

### Sources to Monitor
- Reddit: r/SideProject, r/webdev, r/startups, r/SaaS, r/Entrepreneur, r/smallbusiness, r/InternetIsBeautiful
- Hacker News: Front page + "Show HN" + "Ask HN"
- Product Hunt: New launches + discussions
- Google Trends: Rising search queries in tech/business

### Pain Point Qualification Criteria
A valid pain point MUST meet ALL of these:
1. **Multiple Evidence**: At least 3 independent mentions across sources
2. **Solvable with Software**: Can be addressed with a web app
3. **Not Already Solved Well**: No dominant free solution exists
4. **Buildable in < 1 Week**: Scope is small enough for rapid development
5. **Data Collection Potential**: The tool can naturally collect useful usage data

### Output Format
For each opportunity found, output a JSON object with:
- `title`: One-line description
- `pain_point`: Detailed problem statement
- `evidence`: Array of sources with URLs, sentiment, and engagement
- `market_size_estimate`: small/medium/large
- `competition_level`: none/low/medium/high
- `technical_feasibility`: low/medium/high
- `priority_score`: 1-10 composite score
- `recommended_solution`: What to build

### Scoring Formula
```
priority_score = (
    evidence_count × 1.5 +
    market_size × 2.0 +
    (10 - competition) × 1.5 +
    feasibility × 2.0 +
    data_collection_potential × 3.0
) / 10
```
Note: data_collection_potential has the HIGHEST weight because free products monetize through data.

## Constraints
- DO NOT suggest financial/investment tools
- DO NOT suggest anything requiring real-time data feeds (too expensive)
- DO NOT suggest tools that compete with well-funded incumbents
- PREFER tools with natural viral/share mechanics
- ALL output must be in English
