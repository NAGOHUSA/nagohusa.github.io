# PulseRelay – Headless Backend

PulseRelay is a lightweight automation layer that uses the **DeepSeek API** to
populate `data/trends.json` every hour via a GitHub Action.  
Your iOS app simply fetches that static JSON file — no API latency on the device.

---

## Directory Structure

```
PULSERELAY/
├── scripts/
│   └── fetch_trends.py   # Calls DeepSeek and writes trends.json
└── data/
    └── trends.json       # Auto-generated; updated every hour

.github/workflows/
└── pulse_update.yml      # The scheduled GitHub Action
```

---

## How It Works

1. **Every hour** the `pulse_update.yml` workflow wakes up on GitHub's servers.  
2. It runs `fetch_trends.py`, which asks DeepSeek:  
   *"What is trending right now across Cinema, Sports, World Events, Streaming,
   Music, Space, Tech, 3D Printing, Privacy, Repair Economy, Outdoors, and
   Legal Tech?"*  
3. DeepSeek replies with a JSON array; the script validates and writes it to
   `PULSERELAY/data/trends.json`.  
4. The Action commits and pushes the file back to `main`.

---

## Adding the DeepSeek API Key to GitHub Secrets

1. Go to your repository on GitHub.  
2. Click **Settings** → **Secrets and variables** → **Actions**.  
3. Click **New repository secret**.  
4. Set:
   - **Name**: `DEEPSEEK_API_KEY`
   - **Value**: your DeepSeek API key (get one at <https://platform.deepseek.com>)  
5. Click **Add secret**.

The workflow reads this secret as the `DEEPSEEK_API_KEY` environment variable
at runtime — it is never stored in the repository.

---

## iOS Integration

Fetch the raw JSON URL directly in Swift:

```swift
// MARK: – PulseRelay iOS Integration

import Foundation

// Raw GitHub URL for the auto-updated trends file
private let trendsURL = URL(string:
    "https://raw.githubusercontent.com/NAGOHUSA/nagohusa.github.io/main/PULSERELAY/data/trends.json"
)!

// Swift model – mirrors the JSON schema exactly
struct PulseTrend: Identifiable, Decodable {
    let id = UUID()                 // synthesised locally; not in JSON
    let title: String
    let summary: String
    let sourceURL: String
    let timestamp: String           // ISO 8601 UTC, e.g. "2025-06-01T12:00:00Z"
    let niche: String
    let isHuman: Bool
    let velocityScore: Int

    private enum CodingKeys: String, CodingKey {
        case title, summary, sourceURL, timestamp, niche, isHuman, velocityScore
    }
}

// Fetching function (async/await)
func fetchGlobalTrends() async throws -> [PulseTrend] {
    let (data, _) = try await URLSession.shared.data(from: trendsURL)
    return try JSONDecoder().decode([PulseTrend].self, from: data)
}
```

> **Local trends tip:** Keep a separate function in your app that calls the
> DeepSeek API *directly* from the device using the user's GPS coordinates.
> This gives you global speed (cached JSON) **and** local accuracy (on-device
> call only for the "Local" card).

---

## JSON Schema Reference

Each object in `trends.json` conforms to:

| Field          | Type    | Description                                          |
|----------------|---------|------------------------------------------------------|
| `title`        | String  | Short headline of the trend                          |
| `summary`      | String  | 2-3 sentence explanation                             |
| `sourceURL`    | String  | URL of a representative source                       |
| `timestamp`    | String  | ISO 8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`)     |
| `niche`        | String  | One of the 12 configured niches                      |
| `isHuman`      | Boolean | `true` if primarily about human activity             |
| `velocityScore`| Integer | Growth speed score 1–100                             |

---

## Manual Run

You can trigger the workflow at any time without waiting for the hourly cron:

1. Go to **Actions** → **PulseRelay – Hourly Trends Update**.  
2. Click **Run workflow** → **Run workflow**.

---

## Notes

- The commit message `[skip ci]` prevents the push from re-triggering other
  workflows unnecessarily.  
- If `trends.json` has not changed since the last run (unlikely but possible),
  the Action skips the commit step gracefully.  
- Keep the repository **public** if you want to use the
  `raw.githubusercontent.com` URL from the iOS app without authentication.  
  For a private repo, generate a GitHub Personal Access Token (PAT) with
  `repo` scope and include it as a `Bearer` token in your Swift `URLRequest`.
